<template>
  <section class="page" data-module="patrol">
    <header class="page-head">
      <div>
        <h2>绿地巡查管理</h2>
        <p class="page-desc">维护巡查记录，围绕巡查编号、巡查区域、巡查日期、巡查人员做登记、筛选与状态流转。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记巡查记录</button>
        <button class="btn" type="button" @click="exportRows">导出绿地巡查清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label v-for="field in filterFields" :key="field" class="filter-item">
        <span>{{ field }}</span>
        <input v-model="filters[field]" :placeholder="`按${field}检索`" />
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)">
          <td v-for="column in columns" :key="column">{{ row[column] ?? '—' }}</td>
          <td class="row-actions">
            <template v-if="actionsFor(row).length">
              <button
                v-for="action in actionsFor(row)"
                :key="action"
                class="link"
                type="button"
                @click="runAction(action, row)"
              >
                {{ action }}
              </button>
            </template>
            <span v-else>—</span>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 1" class="empty-state">暂无绿地巡查数据，可先登记巡查记录</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条绿地巡查记录</span>
      <span v-if="noticeMessage" class="notice-text">{{ noticeMessage }}</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { request } from '@/api/client'

type Row = Record<string, string | number | null>
type StatItem = { label: string; value: number }

const ENDPOINT = '/api/patrol'
const columns = ["巡查编号", "巡查区域", "巡查日期", "巡查人员", "巡查路线", "发现问题", "处置措施", "上一处置人", "巡查状态"]
const statuses = ["待巡查", "巡查中", "已巡查", "待复查"]
// 状态机：待巡查→巡查中→已巡查；已巡查可发起复查进入待复查，复查确认后回到已巡查
const ACTIONS_BY_STATUS: Record<string, string[]> = {
  '待巡查': ['开始巡查'],
  '巡查中': ['提交巡查'],
  '已巡查': ['发起复查'],
  '待复查': ['复查确认'],
}
// 看板卡片与明细状态的对应关系，数值每次按明细重算
const STAT_SOURCE: Record<string, string> = {
  '待巡查区域': '待巡查',
  '已巡查记录': '已巡查',
  '待复查记录': '待复查',
}

const rows = ref<Row[]>([])
const total = ref(0)
const stats = ref<StatItem[]>([
  { label: '待巡查区域', value: 0 },
  { label: '已巡查记录', value: 0 },
  { label: '待复查记录', value: 0 },
])
const errorMessage = ref('')
const noticeMessage = ref('')
const filters = ref<Record<string, string>>({})
const filterFields = columns.slice(0, 3)

function actionsFor(row: Row): string[] {
  const status = String(row.status ?? row['巡查状态'] ?? '')
  return ACTIONS_BY_STATUS[status] ?? []
}

function resetFilters() {
  filters.value = {}
  void reload()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

function openCreate() {
  errorMessage.value = '巡查记录登记入口尚未接入审批流'
}

async function runAction(action: string, row: Row) {
  errorMessage.value = ''
  noticeMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ values: { action } }),
    })
    const payload = await response.json().catch(() => null)
    if (!response.ok || !payload?.ok) {
      throw new Error(payload?.message ?? '绿地巡查动作未生效，请稍后重试')
    }
    noticeMessage.value = String(payload.message ?? '')
    await Promise.all([reload(), reloadStats()])
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '绿地巡查操作失败'
  }
}

async function reload() {
  errorMessage.value = ''
  const query = new URLSearchParams(filters.value as Record<string, string>).toString()
  try {
    const response = await request(`${ENDPOINT}?${query}`)
    if (!response.ok) {
      throw new Error('巡查记录列表读取失败')
    }
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '绿地巡查列表读取失败'
  }
}

async function reloadStats() {
  try {
    const response = await request(`${ENDPOINT}/stats`)
    if (!response.ok) {
      throw new Error('巡查看板统计读取失败')
    }
    const payload = await response.json()
    const counts = (payload?.stats ?? {}) as Record<string, number>
    stats.value = stats.value.map((item) => ({
      ...item,
      value: Number(counts[STAT_SOURCE[item.label]] ?? 0),
    }))
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '巡查看板统计读取失败'
  }
}

onMounted(() => {
  void reload()
  void reloadStats()
})
</script>
