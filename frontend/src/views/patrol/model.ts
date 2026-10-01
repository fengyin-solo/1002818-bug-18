/** 绿地巡查领域类型与常量：状态序列、各状态可用动作都在这里统一维护。 */

export const STATUS_PENDING = '待巡查'
export const STATUS_INSPECTING = '巡查中'
export const STATUS_DONE = '已巡查'
export const STATUS_RECHECK = '待复查'

/** 路线面板与详情页共用同一份进度序列，保证两处读到的进度一致。 */
export const STATUS_STEPS = [
  STATUS_PENDING,
  STATUS_INSPECTING,
  STATUS_DONE,
  STATUS_RECHECK,
] as const

export type PatrolStatus = (typeof STATUS_STEPS)[number]

export const ACTION_START = '开始巡查'
export const ACTION_SUBMIT = '提交巡查'
export const ACTION_RECHECK = '发起复查'
export const ACTION_CONFIRM = '复查确认'
export const ACTION_HANDOVER = '交接'

/** 各状态下允许出现的动作；不满足前置状态的按钮不渲染。 */
export const ACTIONS_BY_STATUS: Record<PatrolStatus, string[]> = {
  [STATUS_PENDING]: [ACTION_START, ACTION_HANDOVER],
  [STATUS_INSPECTING]: [ACTION_SUBMIT, ACTION_HANDOVER],
  [STATUS_DONE]: [ACTION_RECHECK],
  [STATUS_RECHECK]: [ACTION_CONFIRM, ACTION_HANDOVER],
}

export interface PatrolEvent {
  时间: string
  动作: string
  说明: string
  操作人: string
}

export interface HandlerNode {
  处置人: string
  接手时间: string
  上一处置人?: string
  交接时状态?: string
}

export interface PatrolEntry {
  id: number
  status: PatrolStatus
  pending: boolean
  abnormal: boolean
  巡查编号: string
  巡查区域: string
  巡查日期: string
  巡查人员: string
  巡查路线: string
  发现问题: string
  处置措施: string
  复查结果: string
  令牌记录?: Record<string, string>
  处置人轨迹: HandlerNode[]
  进展轨迹: PatrolEvent[]
  巡查状态: string
}

export interface PatrolStat {
  label: string
  value: number
}

export interface PatrolFilters {
  keyword: string
  area: string
  patrol_date: string
  inspector: string
  status: string
}

export function emptyFilters(): PatrolFilters {
  return { keyword: '', area: '', patrol_date: '', inspector: '', status: '' }
}

/** 0-3：待巡查/巡查中/已巡查/待复查；复查确认后回到已巡查（2），与状态序列保持同一口径。 */
export function stepIndex(status: string): number {
  const idx = STATUS_STEPS.indexOf(status as PatrolStatus)
  return idx < 0 ? 0 : idx
}
