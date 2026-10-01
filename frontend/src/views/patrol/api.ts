/** 绿地巡查接口封装：列表、看板、明细、动作执行。 */
import { request } from '@/api/client'

import type { PatrolEntry, PatrolFilters, PatrolStat } from './model'

const ENDPOINT = '/api/patrol'

interface PagePayload {
  items: PatrolEntry[]
  total: number
}

export interface ActionResponse {
  ok: boolean
  message: string
  entry: PatrolEntry | null
}

function toQuery(filters: PatrolFilters): string {
  const params = new URLSearchParams()
  if (filters.keyword.trim()) params.set('keyword', filters.keyword.trim())
  if (filters.area.trim()) params.set('area', filters.area.trim())
  if (filters.patrol_date.trim()) params.set('patrol_date', filters.patrol_date.trim())
  if (filters.inspector.trim()) params.set('inspector', filters.inspector.trim())
  if (filters.status.trim()) params.set('status', filters.status.trim())
  return params.toString()
}

export async function fetchPatrolList(filters: PatrolFilters): Promise<PagePayload> {
  const query = toQuery(filters)
  const response = await request(`${ENDPOINT}?${query}`)
  if (!response.ok) throw new Error('巡查记录列表读取失败')
  return (await response.json()) as PagePayload
}

export async function fetchPatrolStats(): Promise<PatrolStat[]> {
  const response = await request(`${ENDPOINT}/stats`)
  if (!response.ok) throw new Error('巡查看板读取失败')
  const payload = (await response.json()) as { cards: PatrolStat[] }
  return payload.cards ?? []
}

export async function fetchPatrolEntry(id: number): Promise<PatrolEntry> {
  const response = await request(`${ENDPOINT}/${id}`)
  if (!response.ok) throw new Error('巡查单明细读取失败')
  return (await response.json()) as PatrolEntry
}

/** 后端把业务错误收敛在 body.ok 上（冲突时 HTTP 409），这里统一转成可读 message。 */
export async function runPatrolAction(id: number, values: Record<string, string>): Promise<ActionResponse> {
  const response = await request(`${ENDPOINT}/${id}/actions`, {
    method: 'POST',
    body: JSON.stringify({ values }),
  })
  const payload = (await response.json().catch(() => null)) as ActionResponse | null
  if (!response.ok || !payload) {
    throw new Error(payload?.message || '绿地巡查动作未生效，请稍后重试')
  }
  return payload
}

export async function createPatrolEntry(values: Record<string, string>): Promise<ActionResponse> {
  const response = await request(ENDPOINT, {
    method: 'POST',
    body: JSON.stringify({ values }),
  })
  const payload = (await response.json().catch(() => null)) as ActionResponse | null
  if (!response.ok || !payload) {
    throw new Error(payload?.message || '巡查记录登记失败')
  }
  return payload
}
