<template>
  <section class="page" data-module="patrol">
    <header class="page-head">
      <div>
        <h2>绿地巡查管理</h2>
        <p class="page-desc">巡查单按 待巡查 → 巡查中 → 已巡查 → 待复查（复查确认回到已巡查）流转，路线面板与详情页读到的是同一份进度。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记巡查记录</button>
        <button class="btn" type="button" @click="exportRows">导出绿地巡查清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in store.stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label class="filter-item">
        <span>巡查编号</span>
        <input v-model="store.filters.keyword" placeholder="按巡查编号检索" />
      </label>
      <label class="filter-item">
        <span>巡查区域</span>
        <input v-model="store.filters.area" placeholder="按巡查区域检索" />
      </label>
      <label class="filter-item">
        <span>巡查日期</span>
        <input v-model="store.filters.patrol_date" placeholder="如 2026-10-01" />
      </label>
      <label class="filter-item">
        <span>巡查人员</span>
        <input v-model="store.filters.inspector" placeholder="按巡查人员检索" />
      </label>
      <label class="filter-item">
        <span>巡查状态</span>
        <select v-model="store.filters.status">
          <option value="">全部状态</option>
          <option v-for="status in STATUS_STEPS" :key="status" :value="status">{{ status }}</option>
        </select>
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <div class="patrol-layout">
      <!-- 巡查路线面板：按巡查路线分组，展开后用与详情页同一个进度条组件 -->
      <aside class="route-panel">
        <h3 class="panel-title">巡查路线（{{ routeGroups.length }}）</h3>
        <p class="panel-empty" v-if="!routeGroups.length">当前筛选下暂无巡查路线</p>
        <div v-for="group in routeGroups" :key="group.route" class="route-group">
          <button
            type="button"
            class="route-head"
            :class="{ active: openRoute === group.route }"
            @click="toggleRoute(group.route)"
          >
            <span class="route-name">{{ group.route }}</span>
            <span class="route-count">{{ group.entries.length }} 单</span>
          </button>
          <div v-if="openRoute === group.route" class="route-body">
            <RouterLink
              v-for="entry in group.entries"
              :key="entry.id"
              :to="`/patrol/${entry.id}`"
              class="route-entry"
              :class="{ selected: store.selectedId === entry.id }"
            >
              <span class="entry-no">{{ entry.巡查编号 }} · {{ entry.巡查人员 }}</span>
              <PatrolProgress :status="entry.status" />
            </RouterLink>
          </div>
        </div>
      </aside>

      <table class="data-table patrol-table">
        <thead>
          <tr>
            <th v-for="column in columns" :key="column">{{ column }}</th>
            <th>当前进度</th>
            <th>可执行动作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in store.rows" :key="row.id">
            <td v-for="column in columns" :key="column">{{ row[column] || '—' }}</td>
            <td>
              <RouterLink class="status-link" :to="`/patrol/${row.id}`">{{ row.status }}</RouterLink>
            </td>
            <td class="row-actions">
              <button
                v-for="action in availableActions(row.status)"
                :key="action"
                class="link"
                type="button"
                @click="openAction(action, row)"
              >
                {{ action }}
              </button>
              <RouterLink class="link" :to="`/patrol/${row.id}`">详情</RouterLink>
            </td>
          </tr>
          <tr v-if="!store.rows.length">
            <td :colspan="columns.length + 2" class="empty-state">暂无绿地巡查数据，可先登记巡查记录</td>
          </tr>
        </tbody>
      </table>
    </div>

    <footer class="page-foot">
      <span>共 {{ store.total }} 条绿地巡查记录</span>
      <span v-if="notice" class="info-text">{{ notice }}</span>
      <span v-else-if="store.error" class="error-text">{{ store.error }}</span>
    </footer>

    <PatrolActionDialog
      ref="dialogRef"
      :open="dialog.open"
      :action="dialog.action"
      :entry="dialog.entry"
      @cancel="closeDialog"
      @submit="submitDialog"
    />

    <div v-if="registerOpen" class="modal-mask" @click.self="registerOpen = false">
      <div class="modal-card">
        <h3 class="modal-title">登记巡查记录</h3>
        <label class="modal-field">
          <span>巡查编号 <em>*</em></span>
          <input v-model="registerForm.巡查编号" placeholder="如 PATR-0005" />
        </label>
        <label class="modal-field">
          <span>巡查区域 <em>*</em></span>
          <input v-model="registerForm.巡查区域" />
        </label>
        <label class="modal-field">
          <span>巡查日期 <em>*</em></span>
          <input v-model="registerForm.巡查日期" type="date" />
        </label>
        <label class="modal-field">
          <span>巡查人员 <em>*</em></span>
          <input v-model="registerForm.巡查人员" />
        </label>
        <label class="modal-field">
          <span>巡查路线</span>
          <input v-model="registerForm.巡查路线" placeholder="可先登记，提交巡查前补齐" />
        </label>
        <p v-if="registerError" class="error-text">{{ registerError }}</p>
        <div class="modal-actions">
          <button class="btn ghost" type="button" @click="registerOpen = false">取消</button>
          <button class="btn primary" type="button" @click="submitRegister">登记</button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import PatrolActionDialog from './PatrolActionDialog.vue'
import PatrolProgress from './PatrolProgress.vue'
import { ACTIONS_BY_STATUS, STATUS_STEPS, type PatrolEntry, type PatrolStatus } from './model'
import { usePatrolStore } from './store'

const ENDPOINT = '/api/patrol'
const columns: (keyof PatrolEntry)[] = ['巡查编号', '巡查区域', '巡查日期', '巡查人员', '巡查路线', '发现问题', '处置措施']

const store = usePatrolStore()
const dialogRef = ref<InstanceType<typeof PatrolActionDialog> | null>(null)
const dialog = reactive({ open: false, action: '', entry: null as PatrolEntry | null })
const notice = ref('')
const registerOpen = ref(false)
const registerError = ref('')
const registerForm = reactive({
  巡查编号: '',
  巡查区域: '',
  巡查日期: '',
  巡查人员: '',
  巡查路线: '',
})

const routeGroups = computed(() => {
  const groups = new Map<string, PatrolEntry[]>()
  for (const entry of store.rows) {
    const route = entry.巡查路线 || '未分配路线'
    const list = groups.get(route) ?? []
    list.push(entry)
    groups.set(route, list)
  }
  return Array.from(groups, ([route, entries]) => ({ route, entries }))
})
const openRoute = ref<string | null>(null)

function toggleRoute(route: string) {
  openRoute.value = openRoute.value === route ? null : route
}

function availableActions(status: string): string[] {
  return ACTIONS_BY_STATUS[status as PatrolStatus] ?? []
}

function openAction(action: string, entry: PatrolEntry) {
  dialog.open = true
  dialog.action = action
  dialog.entry = entry
}

function closeDialog() {
  dialog.open = false
  dialog.entry = null
}

async function submitDialog(values: Record<string, string>) {
  if (!dialog.entry) return
  try {
    const result = await store.act(dialog.entry.id, values)
    notice.value = result.message
    closeDialog()
  } catch (error) {
    dialogRef.value?.fail(error instanceof Error ? error.message : '绿地巡查操作失败')
  }
}

function openCreate() {
  registerError.value = ''
  Object.assign(registerForm, { 巡查编号: '', 巡查区域: '', 巡查日期: '', 巡查人员: '', 巡查路线: '' })
  registerOpen.value = true
}

async function submitRegister() {
  registerError.value = ''
  try {
    const result = await store.register({ ...registerForm })
    registerOpen.value = false
    notice.value = result.message
  } catch (error) {
    registerError.value = error instanceof Error ? error.message : '巡查记录登记失败'
  }
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

function resetFilters() {
  store.filters.keyword = ''
  store.filters.area = ''
  store.filters.patrol_date = ''
  store.filters.inspector = ''
  store.filters.status = ''
  void reload()
}

async function reload() {
  await store.refreshAll()
}

onMounted(reload)
</script>

<style scoped>
.patrol-layout { display: flex; gap: 12px; align-items: flex-start; }
.route-panel {
  width: 300px;
  flex: none;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px;
  max-height: 70vh;
  overflow-y: auto;
}
.panel-title { margin: 0 0 8px; font-size: 14px; }
.panel-empty { color: var(--muted); font-size: 12px; }
.route-group { margin-bottom: 6px; }
.route-head {
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border: 1px solid var(--border);
  background: #f8fafc;
  border-radius: 6px;
  padding: 6px 8px;
  cursor: pointer;
  font-size: 13px;
}
.route-head.active { border-color: var(--brand); color: var(--brand); }
.route-count { color: var(--muted); font-size: 12px; }
.route-body { padding: 6px 4px 2px 8px; display: flex; flex-direction: column; gap: 8px; }
.route-entry {
  display: block;
  border-left: 3px solid var(--border);
  padding: 4px 8px;
  text-decoration: none;
  color: inherit;
  border-radius: 0 6px 6px 0;
}
.route-entry.selected { background: #eff6ff; border-left-color: var(--brand); }
.entry-no { display: block; font-size: 12px; margin-bottom: 6px; }
.patrol-table { flex: 1; }
.status-link { color: var(--brand); text-decoration: none; font-weight: 600; }
.filter-item select {
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 5px 8px;
  font: inherit;
}
.info-text { color: #166534; }
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 20;
}
.modal-card {
  width: 440px;
  max-width: calc(100vw - 32px);
  background: #fff;
  border-radius: 10px;
  padding: 18px 20px;
}
.modal-title { margin: 0 0 12px; font-size: 16px; }
.modal-field { display: block; margin-bottom: 10px; }
.modal-field span { display: block; font-size: 12px; color: var(--muted); margin-bottom: 4px; }
.modal-field em { color: #b42318; font-style: normal; }
.modal-field input {
  width: 100%;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 6px 8px;
  font: inherit;
  font-size: 13px;
}
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 12px; }
</style>
