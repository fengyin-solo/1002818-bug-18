<template>
  <section class="page patrol-detail">
    <header class="page-head">
      <div>
        <h2>巡查单详情 · {{ entry?.巡查编号 ?? '—' }}</h2>
        <p class="page-desc">与路线面板共用同一份明细数据，进度、处置人轨迹、复查结果保持一致。</p>
      </div>
      <div class="page-actions">
        <RouterLink class="btn" to="/patrol">返回巡查列表</RouterLink>
      </div>
    </header>

    <p v-if="store.loading" class="state-text">明细加载中…</p>
    <p v-else-if="!entry" class="error-text">{{ store.error || '巡查单不存在或已归档' }}</p>

    <template v-else>
      <div class="detail-card">
        <div class="detail-head">
          <span class="status-badge" :data-status="entry.status">{{ entry.status }}</span>
          <span class="head-meta">{{ entry.巡查区域 }} · {{ entry.巡查日期 }}</span>
        </div>
        <!-- 与路线面板同一个进度条组件、同一个 status 字段 -->
        <PatrolProgress :status="entry.status" />
      </div>

      <div class="detail-grid">
        <article class="detail-card">
          <h3>巡查信息</h3>
          <dl class="info-list">
            <div><dt>巡查编号</dt><dd>{{ entry.巡查编号 }}</dd></div>
            <div><dt>巡查区域</dt><dd>{{ entry.巡查区域 }}</dd></div>
            <div><dt>巡查日期</dt><dd>{{ entry.巡查日期 }}</dd></div>
            <div><dt>当前处置人</dt><dd>{{ entry.巡查人员 }}</dd></div>
            <div><dt>巡查路线</dt><dd>{{ entry.巡查路线 || '—（提交时必须补齐）' }}</dd></div>
            <div><dt>发现问题</dt><dd>{{ entry.发现问题 || '—' }}</dd></div>
            <div><dt>处置措施</dt><dd>{{ entry.处置措施 || '—' }}</dd></div>
            <div><dt>复查结果</dt><dd>{{ entry.复查结果 || '—' }}</dd></div>
          </dl>
          <div class="action-row">
            <button
              v-for="action in availableActions(entry.status)"
              :key="action"
              class="btn"
              :class="{ primary: action !== '交接' }"
              type="button"
              @click="openAction(action)"
            >
              {{ action }}
            </button>
          </div>
        </article>

        <article class="detail-card">
          <h3>处置人轨迹</h3>
          <p class="card-tip">交接只换人不改状态，上一处置人始终可追溯。</p>
          <ol class="timeline">
            <li v-for="(node, index) in entry.处置人轨迹" :key="index" class="timeline-item">
              <div class="timeline-main">
                <strong>{{ node.处置人 }}</strong>
                <span v-if="node.上一处置人" class="timeline-sub">由 {{ node.上一处置人 }} 交接</span>
              </div>
              <div class="timeline-meta">{{ node.接手时间 }}<span v-if="node.交接时状态"> · {{ node.交接时状态 }}</span></div>
            </li>
          </ol>
        </article>

        <article class="detail-card detail-wide">
          <h3>进展轨迹</h3>
          <ol class="timeline">
            <li v-for="(event, index) in entry.进展轨迹" :key="index" class="timeline-item">
              <div class="timeline-main">
                <strong>{{ event.动作 }}</strong>
                <span class="timeline-sub">{{ event.说明 }}</span>
              </div>
              <div class="timeline-meta">{{ event.时间 }} · {{ event.操作人 }}</div>
            </li>
          </ol>
        </article>
      </div>

      <footer class="page-foot">
        <span v-if="notice" class="info-text">{{ notice }}</span>
        <span v-else-if="store.error" class="error-text">{{ store.error }}</span>
      </footer>

      <PatrolActionDialog
        ref="dialogRef"
        :open="dialog.open"
        :action="dialog.action"
        :entry="entry"
        @cancel="closeDialog"
        @submit="submitDialog"
      />
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import PatrolActionDialog from './PatrolActionDialog.vue'
import PatrolProgress from './PatrolProgress.vue'
import { ACTIONS_BY_STATUS, type PatrolEntry, type PatrolStatus } from './model'
import { usePatrolStore } from './store'

const route = useRoute()
const store = usePatrolStore()
const dialogRef = ref<InstanceType<typeof PatrolActionDialog> | null>(null)
const dialog = reactive({ open: false, action: '' })
const notice = ref('')

const entryId = computed(() => Number(route.params.id))
const entry = computed<PatrolEntry | null>(() => {
  if (store.selectedId === entryId.value) {
    return store.selected ?? store.detail
  }
  return store.detail
})

function availableActions(status: string): string[] {
  return ACTIONS_BY_STATUS[status as PatrolStatus] ?? []
}

function openAction(action: string) {
  dialog.open = true
  dialog.action = action
}

function closeDialog() {
  dialog.open = false
}

async function submitDialog(values: Record<string, string>) {
  try {
    const result = await store.act(entryId.value, values)
    notice.value = result.message
    closeDialog()
  } catch (error) {
    dialogRef.value?.fail(error instanceof Error ? error.message : '绿地巡查操作失败')
  }
}

watch(
  entryId,
  async (id) => {
    await store.loadDetail(id)
  },
  { immediate: true },
)
</script>

<style scoped>
.state-text { color: var(--muted); }
.detail-card {
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 14px 16px;
}
.detail-head { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
.status-badge {
  border-radius: 999px;
  padding: 2px 10px;
  font-size: 12px;
  background: #e2e8f0;
  color: #334155;
}
.status-badge[data-status='待复查'] { background: #fef3c7; color: #92400e; }
.status-badge[data-status='巡查中'] { background: #dbeafe; color: #1e40af; }
.status-badge[data-status='已巡查'] { background: #dcfce7; color: #166534; }
.head-meta { color: var(--muted); font-size: 13px; }
.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 12px;
}
.detail-wide { grid-column: 1 / -1; }
.detail-card h3 { margin: 0 0 10px; font-size: 14px; }
.card-tip { margin: -4px 0 10px; color: var(--muted); font-size: 12px; }
.info-list { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 16px; margin: 0; }
.info-list div { display: flex; flex-direction: column; }
.info-list dt { color: var(--muted); font-size: 12px; }
.info-list dd { margin: 2px 0 0; font-size: 13px; }
.action-row { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }
.timeline { list-style: none; margin: 0; padding: 0; }
.timeline-item {
  border-left: 3px solid var(--border);
  padding: 0 0 12px 12px;
  margin-left: 4px;
}
.timeline-item:last-child { padding-bottom: 0; }
.timeline-main { display: flex; gap: 8px; align-items: baseline; flex-wrap: wrap; }
.timeline-sub { color: #334155; font-size: 13px; }
.timeline-meta { color: var(--muted); font-size: 12px; margin-top: 2px; }
.info-text { color: #166534; }
</style>
