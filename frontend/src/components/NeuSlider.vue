<template>
  <div class="neu-slider-container">
    <div class="slider-header">
      <label class="slider-label">
        <Icon v-if="icon" :icon="icon" class="label-icon" />
        <span>{{ label }}</span>
      </label>
      <!-- 精确数值输入框 (SillyTavern 风格) -->
      <div class="value-input-wrap">
        <input
          type="number"
          :value="localValue"
          :min="min"
          :max="max"
          :step="step"
          class="neu-value-input neu-inset-sm"
          @input="handleInputNumber"
        />
        <span v-if="unit" class="unit-text">{{ unit }}</span>
      </div>
    </div>

    <!-- 新拟态滑轨与滑块 -->
    <div class="slider-control-row">
      <input
        type="range"
        :value="localValue"
        :min="min"
        :max="max"
        :step="step"
        class="neu-range-slider"
        @input="handleInputRange"
      />
    </div>

    <p v-if="hint" class="slider-hint">{{ hint }}</p>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Icon } from '@iconify/vue'

const props = withDefaults(
  defineProps<{
    modelValue: number
    min?: number
    max?: number
    step?: number
    label: string
    unit?: string
    icon?: string
    hint?: string
  }>(),
  {
    min: 0,
    max: 100,
    step: 1,
    unit: '',
  }
)

const emit = defineEmits<{
  (e: 'update:modelValue', value: number): void
}>()

const localValue = computed(() => props.modelValue)

const handleInputRange = (e: Event) => {
  const target = e.target as HTMLInputElement
  const val = parseFloat(target.value)
  if (!isNaN(val)) {
    emit('update:modelValue', val)
  }
}

const handleInputNumber = (e: Event) => {
  const target = e.target as HTMLInputElement
  let val = parseFloat(target.value)
  if (isNaN(val)) return
  if (props.min !== undefined && val < props.min) val = props.min
  if (props.max !== undefined && val > props.max) val = props.max
  emit('update:modelValue', val)
}
</script>

<style scoped>
.neu-slider-container {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.slider-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.slider-label {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--neu-text-primary);
}

.label-icon {
  font-size: 1rem;
  color: var(--neu-accent);
}

.value-input-wrap {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}

.neu-value-input {
  width: 5.5rem;
  padding: 0.25rem 0.5rem;
  border: none;
  outline: none;
  border-radius: 8px;
  background: var(--neu-surface);
  color: var(--neu-text-primary);
  font-family: monospace;
  font-size: 0.85rem;
  font-weight: 600;
  text-align: right;
  transition: all 0.2s ease;
}

.neu-value-input:focus {
  box-shadow: inset 3px 3px 6px var(--neu-dark), inset -3px -3px 6px var(--neu-light);
  color: var(--neu-accent);
}

.unit-text {
  font-size: 0.75rem;
  color: var(--neu-text-secondary);
}

.slider-control-row {
  display: flex;
  align-items: center;
  width: 100%;
}

/* 范围滑动条新拟态定制 */
.neu-range-slider {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 8px;
  border-radius: 999px;
  background: var(--neu-surface);
  box-shadow: inset 2px 2px 5px var(--neu-dark), inset -2px -2px 5px var(--neu-light);
  outline: none;
  cursor: pointer;
  transition: background 0.2s;
}

.neu-range-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--neu-surface);
  box-shadow: 2px 2px 5px var(--neu-dark), -2px -2px 5px var(--neu-light);
  cursor: pointer;
  border: 2px solid var(--neu-accent);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.neu-range-slider::-webkit-slider-thumb:hover {
  transform: scale(1.15);
  box-shadow: 3px 3px 7px var(--neu-dark), -3px -3px 7px var(--neu-light);
}

.neu-range-slider::-webkit-slider-thumb:active {
  transform: scale(1.05);
  background: var(--neu-accent);
}

.neu-range-slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--neu-surface);
  box-shadow: 2px 2px 5px var(--neu-dark), -2px -2px 5px var(--neu-light);
  cursor: pointer;
  border: 2px solid var(--neu-accent);
}

.slider-hint {
  margin: 0;
  font-size: 0.725rem;
  color: var(--neu-text-muted);
}
</style>
