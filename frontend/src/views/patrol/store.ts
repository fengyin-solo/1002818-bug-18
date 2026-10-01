/** 绿地巡查共享数据：列表页的路线面板与详情页都从这里取数、看同一份进度。 */
import { defineStore } from 'pinia'

import {
  createPatrolEntry,
  fetchPatrolEntry,
  fetchPatrolList,
  fetchPatrolStats,
  runPatrolAction,
} from './api'
import { emptyFilters, type PatrolEntry, type PatrolFilters, type PatrolStat } from './model'

interface PatrolState {
  rows: PatrolEntry[]
  total: number
  stats: PatrolStat[]
  filters: PatrolFilters
  selectedId: number | null
  detail: PatrolEntry | null
  loading: boolean
  error: string
}

export const usePatrolStore = defineStore('patrol', {
  state: (): PatrolState => ({
    rows: [],
    total: 0,
    stats: [],
    filters: emptyFilters(),
    selectedId: null,
    detail: null,
    loading: false,
    error: '',
  }),
  getters: {
    selected(state): PatrolEntry | null {
      if (state.selectedId === null) return null
      return state.rows.find((row) => row.id === state.selectedId) ?? state.detail
    },
  },
  actions: {
    setSelected(id: number | null) {
      this.selectedId = id
      this.detail = null
    },
    async loadList() {
      this.loading = true
      this.error = ''
      try {
        const page = await fetchPatrolList(this.filters)
        this.rows = page.items
        this.total = page.total
        // 详情若落在当前过滤结果里，直接复用列表行，保证两处进度永远一致
        if (this.selectedId !== null && !this.rows.some((row) => row.id === this.selectedId)) {
          this.detail = null
        }
      } catch (error) {
        this.error = error instanceof Error ? error.message : '绿地巡查列表读取失败'
      } finally {
        this.loading = false
      }
    },
    async loadStats() {
      try {
        this.stats = await fetchPatrolStats()
      } catch {
        // 看板失败不阻塞列表
      }
    },
    async loadDetail(id: number) {
      this.selectedId = id
      this.loading = true
      this.error = ''
      try {
        this.detail = await fetchPatrolEntry(id)
      } catch (error) {
        this.error = error instanceof Error ? error.message : '巡查单明细读取失败'
      } finally {
        this.loading = false
      }
    },
    /** 动作成功后统一刷新：明细驱动看板重算，列表行同步更新。 */
    async act(id: number, values: Record<string, string>) {
      const result = await runPatrolAction(id, values)
      await Promise.all([this.loadList(), this.loadStats()])
      if (this.selectedId === id && result.entry) {
        this.detail = result.entry
      }
      return result
    },
    async refreshAll() {
      await Promise.all([this.loadList(), this.loadStats()])
    },
    async register(values: Record<string, string>) {
      const result = await createPatrolEntry(values)
      await this.refreshAll()
      return result
    },
  },
})
