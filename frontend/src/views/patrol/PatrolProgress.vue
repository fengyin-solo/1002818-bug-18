<template>
  <!-- 巡查进度条：路线面板与详情页都用它渲染，进度口径只有一份 -->
  <ol class="patrol-progress" :data-current="current">
    <li
      v-for="(step, index) in steps"
      :key="step"
      class="progress-node"
      :class="{ done: index < current, active: index === current }"
    >
      <span class="node-dot">{{ index < current ? '✓' : index + 1 }}</span>
      <span class="node-label">{{ step }}</span>
    </li>
  </ol>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import { STATUS_STEPS, stepIndex } from './model'

const props = defineProps<{ status: string }>()

const steps = STATUS_STEPS
const current = computed(() => stepIndex(props.status))
</script>

<style scoped>
.patrol-progress {
  display: flex;
  align-items: center;
  gap: 0;
  list-style: none;
  margin: 0;
  padding: 0;
}
.progress-node {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  position: relative;
  color: var(--muted);
  font-size: 12px;
}
.progress-node:not(:last-child)::after {
  content: '';
  flex: 1;
  height: 2px;
  background: var(--border);
  margin: 0 8px;
}
.progress-node.done::after {
  background: #16a34a;
}
.node-dot {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #e2e8f0;
  color: #64748b;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  flex: none;
}
.progress-node.done .node-dot {
  background: #16a34a;
  color: #fff;
}
.progress-node.active {
  color: #0f5132;
  font-weight: 600;
}
.progress-node.active .node-dot {
  background: var(--brand);
  color: #fff;
}
</style>
