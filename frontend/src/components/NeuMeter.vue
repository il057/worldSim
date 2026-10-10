<template>
  <div class="neu-meter">
    <div class="meter-header">
      <div class="header-left">
        <Icon v-if="icon" :icon="icon" class="meter-icon" :style="{ color }" />
        <span class="meter-label">{{ label }}</span>
      </div>
      <div class="header-right">
        <span
          v-if="delta !== undefined && delta !== 0"
          class="meter-delta-badge"
          :class="delta > 0 ? 'delta-positive' : 'delta-negative'"
        >
          <Icon :icon="delta > 0 ? 'material-symbols:arrow-drop-up' : 'material-symbols:arrow-drop-down'" class="delta-arrow" />
          {{ delta > 0 ? `+${delta}` : delta }}
        </span>
        <span class="meter-value" :style="{ color }">{{ value }}{{ suffix }}</span>
        <span v-if="subText" class="meter-sub">{{ subText }}</span>
      </div>
    </div>
    <div class="meter-track neu-inset-sm">
      <div
        class="meter-fill"
        :style="{
          width: `${clampedValue}%`,
          backgroundColor: color,
        }"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Icon } from '@iconify/vue'

const props = withDefaults(
  defineProps<{
    label: string
    value: number
    color?: string
    icon?: string
    suffix?: string
    subText?: string
    delta?: number
  }>(),
  {
    color: 'var(--neu-accent)',
    icon: '',
    suffix: '%',
    subText: '',
    delta: undefined,
  }
)

const clampedValue = computed(() => Math.max(0, Math.min(100, props.value)))
</script>

<style scoped>
.neu-meter {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  width: 100%;
}

.meter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.85rem;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  color: var(--neu-text-secondary);
  font-weight: 500;
}

.meter-icon {
  font-size: 1.15rem;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.meter-value {
  font-weight: 700;
  font-size: 0.95rem;
}

.meter-delta-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.1rem;
  font-size: 0.725rem;
  font-weight: 700;
  padding: 0.1rem 0.45rem;
  border-radius: 9999px;
  font-family: monospace;
  line-height: 1.2;
  background: var(--neu-surface);
  box-shadow: 2px 2px 5px var(--neu-dark), -2px -2px 5px var(--neu-light);
  animation: delta-pop 0.3s ease-out;
}

.delta-arrow {
  font-size: 0.9rem;
  margin-right: -0.15rem;
  margin-left: -0.15rem;
}

.delta-positive {
  color: var(--neu-success);
  box-shadow: 2px 2px 5px var(--neu-dark), -2px -2px 5px var(--neu-light), inset 0 0 3px rgba(56, 161, 105, 0.2);
}

.delta-negative {
  color: var(--neu-danger);
  box-shadow: 2px 2px 5px var(--neu-dark), -2px -2px 5px var(--neu-light), inset 0 0 3px rgba(229, 62, 62, 0.2);
}

@keyframes delta-pop {
  0% { transform: scale(0.85); opacity: 0; }
  100% { transform: scale(1); opacity: 1; }
}

.meter-sub {
  font-size: 0.75rem;
  color: var(--neu-text-muted);
}

.meter-track {
  height: 10px;
  width: 100%;
  overflow: hidden;
  padding: 2px;
  position: relative;
}

.meter-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 0 8px rgba(0, 0, 0, 0.1);
}
</style>
