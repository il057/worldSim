<template>
  <div class="neu-meter">
    <div class="meter-header">
      <div class="header-left">
        <Icon v-if="icon" :icon="icon" class="meter-icon" :style="{ color }" />
        <span class="meter-label">{{ label }}</span>
      </div>
      <div class="header-right">
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
  }>(),
  {
    color: 'var(--neu-accent)',
    icon: '',
    suffix: '%',
    subText: '',
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
