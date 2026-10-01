"""绿地巡查业务规则：状态流转、字段校验与筛选口径都收在这里。"""
from __future__ import annotations

from typing import Any

from app.store import store

MODULE = "patrol"
REQUIRED_FIELDS = ["巡查编号", "巡查区域", "巡查日期"]
OPTIONAL_FIELDS = ["巡查人员", "巡查路线", "发现问题", "处置措施"]
STATUS_ORDER = ["待巡查", "巡查中", "已巡查", "待复查"]
# 状态机：动作 -> (要求的当前状态, 目标状态)。主线为 待巡查→巡查中→已巡查，
# 已巡查可发起复查进入待复查，待复查只能经复查确认回到已巡查。
TRANSITIONS = {
    "开始巡查": ("待巡查", "巡查中"),
    "提交巡查": ("巡查中", "已巡查"),
    "发起复查": ("已巡查", "待复查"),
    "复查确认": ("待复查", "已巡查"),
}
# 动作随带 values 里允许写回明细的字段
EDITABLE_FIELDS = ["巡查人员", "巡查路线", "发现问题", "处置措施", "复查结果"]
DONE_STATUS = "已巡查"
NEGATIVE_ACTIONS = []


class PatrolService:
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows(MODULE)
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("巡查编号", ""))]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        total = len(rows)
        start = max(page - 1, 0) * size
        return rows[start:start + size], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        return store.find(MODULE, entry_id)

    def stats(self) -> dict[str, int]:
        """巡查看板计数：每次按明细逐条重算，不留存中间结果。"""
        rows = store.rows(MODULE)
        return {status: sum(1 for row in rows if row.get("status") == status) for status in STATUS_ORDER}

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        rows = store.rows(MODULE)
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry.update({field: values.get(field) for field in REQUIRED_FIELDS})
        for field in OPTIONAL_FIELDS:
            if values.get(field) is not None:
                entry[field] = values[field]
        entry["status"] = STATUS_ORDER[0]
        entry["巡查状态"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = False
        entry["上一处置人"] = None
        entry["处置人履历"] = []
        rows.append(entry)
        return entry, []

    def run_action(
        self,
        entry_id: int,
        action: str,
        values: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any] | None, str]:
        values = values or {}
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"巡查记录 {entry_id} 不存在或已归档"
        if action not in TRANSITIONS:
            return None, f"动作「{action}」不属于绿地巡查可执行范围"
        source, target = TRANSITIONS[action]
        current = str(entry.get("status") or "")
        if action == "提交巡查" and current in (DONE_STATUS, "待复查"):
            # 重复提交同一巡查单只认第一次：不回写字段、不动状态
            return entry, "该巡查单已提交过，重复提交以第一次为准"
        if current != source:
            return None, f"「{action}」要求记录处于「{source}」，当前为「{current}」"
        # 提交前先合并路线：随带路线优先，空路线不覆盖已有路线
        incoming_route = str(values.get("巡查路线") or "").strip()
        merged_route = incoming_route or str(entry.get("巡查路线") or "").strip()
        if action == "提交巡查" and not merged_route:
            return None, "巡查路线为空，不能提交巡查：请先补录巡查路线"
        self._apply_updates(entry, values)
        entry["status"] = target
        entry["巡查状态"] = target
        entry["pending"] = target != DONE_STATUS
        entry["abnormal"] = action in NEGATIVE_ACTIONS
        return entry, f"巡查记录已{action}"

    def _apply_updates(self, entry: dict[str, Any], values: dict[str, Any]) -> None:
        """把动作随带的明细字段写回记录。

        处置措施与巡查路线相互牵连时以巡查路线为准：路线最后落库、
        空路线不覆盖已有路线，其他字段不允许顶替路线生效。
        """
        for field in ("发现问题", "处置措施", "复查结果"):
            if field in values and values[field] is not None:
                entry[field] = values[field]
        self._apply_handover(entry, values)
        route = str(values.get("巡查路线") or "").strip()
        if route:
            entry["巡查路线"] = route

    def _apply_handover(self, entry: dict[str, Any], values: dict[str, Any]) -> None:
        """巡查人员变更视为交接：留住上一位处置人，履历可一直往前追。"""
        if "巡查人员" not in values:
            return
        new_handler = str(values.get("巡查人员") or "").strip()
        old_handler = str(entry.get("巡查人员") or "").strip()
        if not new_handler or new_handler == old_handler:
            return
        history = entry.setdefault("处置人履历", [])
        if old_handler:
            history.append(old_handler)
        entry["上一处置人"] = old_handler or None
        entry["巡查人员"] = new_handler
