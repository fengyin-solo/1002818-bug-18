<template>
  <div v-if="open" class="modal-mask" @click.self="cancel">
    <div class="modal-card">
      <h3 class="modal-title">{{ action }} · {{ entry?.巡查编号 }}</h3>
      <p class="modal-sub">当前进度：{{ entry?.status }}</p>

      <label v-if="needRoute" class="modal-field">
        <span>巡查路线 <em>*</em></span>
        <input v-model="form.route" placeholder="巡查路线空着不许提交" />
      </label>
      <label v-if="needProblem" class="modal-field">
        <span>发现问题 <em>*</em></span>
        <textarea v-model="form.problem" rows="2" placeholder="记录本次巡查发现的问题"></textarea>
      </label>
      <label v-if="needMeasure" class="modal-field">
        <span>处置措施 <em>*</em></span>
        <textarea v-model="form.measure" rows="2" placeholder="措施里若写了路线，会以巡查路线字段为准"></textarea>
      </label>
      <label v-if="needReason" class="modal-field">
        <span>复查原因</span>
        <textarea v-model="form.reason" rows="2" placeholder="可说明发起复查的原因（选填）"></textarea>
      </label>
      <label v-if="needResult" class="modal-field">
        <span>复查结果 <em>*</em></span>
        <textarea v-model="form.result" rows="2" placeholder="复查确认后巡查单回到已巡查"></textarea>
      </label>
      <label v-if="needHandover" class="modal-field">
        <span>下一处置人 <em>*</em></span>
        <input v-model="form.successor" placeholder="交接后仍可追溯上一处置人" />
      </label>

      <p v-if="hint" class="modal-hint">{{ hint }}</p>
      <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>

      <div class="modal-actions">
        <button class="btn ghost" type="button" :disabled="submitting" @click="cancel">取消</button>
        <button class="btn primary" type="button" :disabled="submitting" @click="confirm">
          {{ submitting ? '提交中…' : '确认' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'

import {
  ACTION_CONFIRM,
  ACTION_HANDOVER,
  ACTION_RECHECK,
  ACTION_SUBMIT,
  type PatrolEntry,
} from './model'

const props = defineProps<{
  open: boolean
  action: string
  entry: PatrolEntry | null
}>()
const emit = defineEmits<{
  (e: 'cancel'): void
  (e: 'submit', values: Record<string, string>): void
}>()

const form = reactive({ route: '', problem: '', measure: '', reason: '', result: '', successor: '' })
const errorMessage = ref('')
const submitting = ref(false)

const needRoute = computed(() => props.action === ACTION_SUBMIT)
const needProblem = computed(() => props.action === ACTION_SUBMIT)
const needMeasure = computed(() => props.action === ACTION_SUBMIT)
const needReason = computed(() => props.action === ACTION_RECHECK)
const needResult = computed(() => props.action === ACTION_CONFIRM)
const needHandover = computed(() => props.action === ACTION_HANDOVER)

const hints: Record<string, string> = {
  [ACTION_SUBMIT]: '提交后状态变为已巡查；重复提交同一巡查单只认第一次。',
  [ACTION_RECHECK]: '发起复查后进入待复查，需复查确认才回到已巡查。',
  [ACTION_CONFIRM]: '复查确认后回到已巡查，结果会记入进展轨迹。',
  [ACTION_HANDOVER]: '交接不改状态，只更新当前处置人并保留完整处置人轨迹。',
}
const hint = computed(() => hints[props.action] ?? '')

watch(
  () => [props.open, props.entry?.id],
  () => {
    form.route = props.entry?.巡查路线 ?? ''
    form.problem = props.entry?.发现问题 ?? ''
    form.measure = props.entry?.处置措施 ?? ''
    form.reason = ''
    form.result = ''
    form.successor = ''
    errorMessage.value = ''
    submitting.value = false
  },
)

function makeToken(): string {
  return `${props.entry?.id}-${props.action}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

function confirm() {
  errorMessage.value = ''
  if (!props.entry) return
  if (needRoute.value && !form.route.trim()) {
    errorMessage.value = '巡查路线空着不许提交'
    return
  }
  if (needProblem.value && !form.problem.trim()) {
    errorMessage.value = '发现问题不能为空'
    return
  }
  if (needMeasure.value && !form.measure.trim()) {
    errorMessage.value = '处置措施不能为空'
    return
  }
  if (needResult.value && !form.result.trim()) {
    errorMessage.value = '复查结果不能为空'
    return
  }
  if (needHandover.value && !form.successor.trim()) {
    errorMessage.value = '下一处置人不能为空'
    return
  }

  const values: Record<string, string> = { action: props.action }
  if (needRoute.value) {
    values['巡查路线'] = form.route.trim()
    values['发现问题'] = form.problem.trim()
    values['处置措施'] = form.measure.trim()
    values['提交令牌'] = makeToken()
  }
  if (needReason.value) values['发现问题'] = form.reason.trim()
  if (needResult.value) {
    values['复查结果'] = form.result.trim()
    values['提交令牌'] = makeToken()
  }
  if (needHandover.value) values['下一处置人'] = form.successor.trim()

  submitting.value = true
  emit('submit', values)
}

function cancel() {
  emit('cancel')
}

defineExpose({
  fail(message: string) {
    submitting.value = false
    errorMessage.value = message
  },
})
</script>

<style scoped>
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
  width: 460px;
  max-width: calc(100vw - 32px);
  background: #fff;
  border-radius: 10px;
  padding: 18px 20px;
  box-shadow: 0 18px 48px rgba(15, 23, 42, 0.25);
}
.modal-title { margin: 0; font-size: 16px; }
.modal-sub { margin: 4px 0 12px; color: var(--muted); font-size: 12px; }
.modal-field { display: block; margin-bottom: 10px; }
.modal-field span { display: block; font-size: 12px; color: var(--muted); margin-bottom: 4px; }
.modal-field em { color: #b42318; font-style: normal; }
.modal-field input,
.modal-field textarea {
  width: 100%;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 6px 8px;
  font: inherit;
  font-size: 13px;
}
.modal-field textarea { resize: vertical; }
.modal-hint { font-size: 12px; color: #92400e; background: #fef3c7; border-radius: 6px; padding: 6px 8px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 12px; }
</style>
