"""绿地巡查业务规则：状态流转、字段校验与筛选口径都收在这里。

状态机：
    待巡查 ──开始巡查──▶ 巡查中 ──提交巡查──▶ 已巡查 ──发起复查──▶ 待复查 ──复查确认──▶ 已巡查

其中「交接」不改变状态，只把当前处置人记进处置人轨迹，任何在办状态都能交接。
提交与复查都带幂等令牌：同一张巡查单重复提交只认第一次。
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from app.store import store

MODULE = "patrol"
REQUIRED_FIELDS = ["巡查编号", "巡查区域", "巡查日期", "巡查人员"]
# 状态序列：待巡查 → 巡查中 → 已巡查 → 待复查（复查确认回到已巡查）
STATUS_PENDING = "待巡查"
STATUS_INSPECTING = "巡查中"
STATUS_DONE = "已巡查"
STATUS_RECHECK = "待复查"
STATUS_ORDER = [STATUS_PENDING, STATUS_INSPECTING, STATUS_DONE, STATUS_RECHECK]

ACTION_START = "开始巡查"
ACTION_SUBMIT = "提交巡查"
ACTION_RECHECK = "发起复查"
ACTION_CONFIRM = "复查确认"
ACTION_HANDOVER = "交接"
ACTION_RULES = {
    ACTION_START: STATUS_INSPECTING,
    ACTION_SUBMIT: STATUS_DONE,
    ACTION_RECHECK: STATUS_RECHECK,
    ACTION_CONFIRM: STATUS_DONE,
}
NEGATIVE_ACTIONS = []

# 处置措施里夹带的路线写法：「按原路线:A」「路线=A」「巡查路线：A」等，统一改写成「路线：巡查路线」
# 短写法前面若是「原」或「查」（按原路线/巡查路线的尾巴），交给前面的长写法去匹配
_ROUTE_REF = re.compile(r"(?:按原路线|巡查路线|(?<![原查])路线)\s*[:：=＝]\s*([^，,；;。\s]+)")
ROUTE_FIELD = "巡查路线"
MEASURE_FIELD = "处置措施"
PROBLEM_FIELD = "发现问题"
HANDLER_FIELD = "巡查人员"
RESULT_FIELD = "复查结果"
TOKEN_FIELD = "提交令牌"
TOKEN_LOG_FIELD = "令牌记录"

# 每个动作允许的前置状态；交接不在表里，单独放行所有在办状态
ALLOWED_FROM: dict[str, set[str]] = {
    ACTION_START: {STATUS_PENDING},
    ACTION_SUBMIT: {STATUS_INSPECTING},
    ACTION_RECHECK: {STATUS_DONE},
    ACTION_CONFIRM: {STATUS_RECHECK},
}
# 复查/提交时必须带上的内容字段
ACTION_REQUIRED_CONTENT = {
    ACTION_SUBMIT: [PROBLEM_FIELD, MEASURE_FIELD],
    ACTION_CONFIRM: [RESULT_FIELD],
}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _add_event(entry: dict[str, Any], title: str, detail: str, operator: str) -> None:
    events = entry.setdefault("进展轨迹", [])
    assert isinstance(events, list)
    events.append({"时间": _now(), "动作": title, "说明": detail, "操作人": operator})


def _sync_flags(entry: dict[str, Any]) -> None:
    """pending/abnormal 看板口径统一从 status 推导，避免明细与看板各算各的。"""
    status = str(entry.get("status") or STATUS_PENDING)
    entry["pending"] = status != STATUS_DONE
    entry["abnormal"] = status == STATUS_RECHECK
    entry["巡查状态"] = status


def _normalize_measure(measure: str, route: str) -> str:
    """处置措施里写的路线与巡查路线字段相互牵连时，以巡查路线字段为准。"""
    def _replace(match: re.Match[str]) -> str:
        return f"路线：{route}"

    return _ROUTE_REF.sub(_replace, measure)


def _token_seen(entry: dict[str, Any], action: str, token: str) -> bool:
    log = entry.get(TOKEN_LOG_FIELD)
    return isinstance(log, dict) and log.get(action) == token


def _remember_token(entry: dict[str, Any], action: str, token: str) -> None:
    if not token:
        return
    log = entry.setdefault(TOKEN_LOG_FIELD, {})
    assert isinstance(log, dict)
    log[action] = token


class PatrolService:
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        area: str | None = None,
        patrol_date: str | None = None,
        inspector: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows(MODULE)
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("巡查编号", ""))]
        if area:
            rows = [row for row in rows if area in str(row.get("巡查区域", ""))]
        if patrol_date:
            rows = [row for row in rows if patrol_date in str(row.get("巡查日期", ""))]
        if inspector:
            rows = [row for row in rows if inspector in str(row.get(HANDLER_FIELD, ""))]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        total = len(rows)
        start = max(page - 1, 0) * size
        return rows[start:start + size], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        return store.find(MODULE, entry_id)

    def stats(self) -> list[dict[str, Any]]:
        """看板三张小卡片，全部由明细实时重算。"""
        rows = store.rows(MODULE)
        return [
            {"label": "待巡查区域", "value": sum(1 for row in rows if row.get("status") == STATUS_PENDING)},
            {"label": "已巡查记录", "value": sum(1 for row in rows if row.get("status") == STATUS_DONE)},
            {"label": "待复查记录",
             "value": sum(1 for row in rows if row.get("status") == STATUS_RECHECK)},
        ]

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        rows = store.rows(MODULE)
        entry: dict[str, Any] = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        for field in REQUIRED_FIELDS:
            entry[field] = str(values.get(field)).strip()
        entry[ROUTE_FIELD] = str(values.get(ROUTE_FIELD) or "").strip()
        entry[PROBLEM_FIELD] = ""
        entry[MEASURE_FIELD] = ""
        entry[RESULT_FIELD] = ""
        entry["处置人轨迹"] = [{"处置人": entry[HANDLER_FIELD], "接手时间": _now()}]
        entry["进展轨迹"] = [{
            "时间": _now(),
            "动作": "登记",
            "说明": "巡查单已登记，等待开始巡查",
            "操作人": entry[HANDLER_FIELD],
        }]
        entry["status"] = STATUS_PENDING
        _sync_flags(entry)
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
        if action not in ACTION_RULES and action != ACTION_HANDOVER:
            return None, f"动作「{action}」不属于绿地巡查可执行范围"

        status = str(entry.get("status") or "")
        operator = str(values.get("operator") or entry.get(HANDLER_FIELD) or "值班管理员").strip()

        if action == ACTION_HANDOVER:
            return self._handover(entry, values, operator)

        # 同一张巡查单重复提交只认第一次：令牌一致直接回放首次结果，
        # 这条判断要放在状态守卫之前——复查回到已巡查后，旧令牌重试仍算同一次提交。
        token = str(values.get(TOKEN_FIELD) or "").strip()
        if token and action in (ACTION_SUBMIT, ACTION_CONFIRM) and _token_seen(entry, action, token):
            return entry, "该结果已提交过，重复提交只认第一次"

        if status not in ALLOWED_FROM[action]:
            return None, f"当前为{status}，不能执行「{action}」"

        target = ACTION_RULES[action]

        if action == ACTION_SUBMIT:
            return self._submit(entry, values, operator, target, token)
        if action == ACTION_CONFIRM:
            return self._confirm(entry, values, operator, target, token)
        if action == ACTION_START:
            _add_event(entry, ACTION_START, f"沿路线「{entry.get(ROUTE_FIELD) or '未填写'}」开始巡查", operator)
        elif action == ACTION_RECHECK:
            reason = str(values.get(PROBLEM_FIELD) or "").strip()
            detail = f"因{reason}发起复查" if reason else "已发起复查，等待复查确认"
            _add_event(entry, ACTION_RECHECK, detail, operator)

        entry["status"] = target
        _sync_flags(entry)
        return entry, f"巡查记录已{action}"

    def _submit(
        self,
        entry: dict[str, Any],
        values: dict[str, Any],
        operator: str,
        target: str,
        token: str,
    ) -> tuple[dict[str, Any], str]:
        missing = [
            field for field in ACTION_REQUIRED_CONTENT[ACTION_SUBMIT]
            if not str(values.get(field) or "").strip()
        ]
        route = str(values.get(ROUTE_FIELD) or entry.get(ROUTE_FIELD) or "").strip()
        if not route:
            missing.append(ROUTE_FIELD)
        if missing:
            return None, f"提交失败，巡查路线与巡查结果不能为空：{'、'.join(dict.fromkeys(missing))}"

        problem = str(values.get(PROBLEM_FIELD) or "").strip()
        measure = str(values.get(MEASURE_FIELD) or "").strip()
        measure = _normalize_measure(measure, route)

        entry[ROUTE_FIELD] = route
        entry[PROBLEM_FIELD] = problem
        entry[MEASURE_FIELD] = measure
        _remember_token(entry, ACTION_SUBMIT, token)
        entry["status"] = target
        _sync_flags(entry)
        _add_event(entry, ACTION_SUBMIT, f"巡查完成：{problem}；处置措施：{measure}", operator)
        return entry, "巡查记录已提交"

    def _confirm(
        self,
        entry: dict[str, Any],
        values: dict[str, Any],
        operator: str,
        target: str,
        token: str,
    ) -> tuple[dict[str, Any], str]:
        result = str(values.get(RESULT_FIELD) or "").strip()
        if not result:
            return None, "复查失败，复查结果不能为空"

        entry[RESULT_FIELD] = result
        _remember_token(entry, ACTION_CONFIRM, token)
        entry["status"] = target
        _sync_flags(entry)
        _add_event(entry, ACTION_CONFIRM, f"复查确认：{result}", operator)
        return entry, "复查确认完成，回到已巡查"

    def _handover(
        self,
        entry: dict[str, Any],
        values: dict[str, Any],
        operator: str,
    ) -> tuple[dict[str, Any] | None, str]:
        status = str(entry.get("status") or STATUS_PENDING)
        if status == STATUS_DONE:
            return None, "已巡查的工单无需交接"
        successor = str(values.get("下一处置人") or values.get("handler") or "").strip()
        if not successor:
            return None, "交接失败，下一处置人不能为空"

        track = entry.setdefault("处置人轨迹", [])
        assert isinstance(track, list)
        previous = str(entry.get(HANDLER_FIELD) or "")
        if successor == previous:
            return None, "下一处置人与当前处置人相同，无需交接"

        track.append({
            "处置人": successor,
            "接手时间": _now(),
            "上一处置人": previous,
            "交接时状态": status,
        })
        entry[HANDLER_FIELD] = successor
        _add_event(entry, ACTION_HANDOVER, f"{previous} 移交给 {successor}", operator)
        # 交接不改状态，但看板标志位仍以当前状态为准
        _sync_flags(entry)
        return entry, f"已交接给{successor}，上一处置人{previous}可追溯"
