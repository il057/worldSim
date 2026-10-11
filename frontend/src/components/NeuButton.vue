<template>
  <button
    :class="[
      'neu-btn',
      variantClass,
      { 'is-active': active, 'is-disabled': disabled || loading }
    ]"
    :disabled="disabled || loading"
    @click="$emit('click')"
  >
    <Icon
      v-if="loading"
      icon="material-symbols:progress-activity"
      class="btn-icon spin"
    />
    <Icon
      v-else-if="icon"
      :icon="icon"
      class="btn-icon"
    />
    <span v-if="label" class="btn-label">{{ label }}</span>
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Icon } from '@iconify/vue'

const props = withDefaults(
  defineProps<{
    icon?: string
    label?: string
    variant?: 'normal' | 'primary' | 'danger' | 'accent'
    active?: boolean
    disabled?: boolean
    loading?: boolean
  }>(),
  {
    icon: '',
    label: '',
    variant: 'normal',
    active: false,
    disabled: false,
    loading: false,
  }
)

defineEmits<{
  (e: 'click'): void
}>()

const variantClass = computed(() => {
  switch (props.variant) {
    case 'primary':
      return 'neu-btn-primary'
    case 'accent':
      return 'neu-btn-accent'
    case 'danger':
      return 'neu-btn-danger'
    default:
      return 'neu-btn-normal'
  }
})
</script>

<style scoped>
.neu-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.65rem 1.15rem;
  border: none;
  border-radius: 12px;
  background: var(--neu-surface);
  color: var(--neu-text-primary);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  box-shadow: var(--shadow-flat-sm);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  user-select: none;
  outline: none;
}

.neu-btn:hover:not(.is-disabled) {
  box-shadow: var(--shadow-hover);
  transform: translateY(-1px);
}

.neu-btn:active:not(.is-disabled),
.neu-btn.is-active {
  box-shadow: var(--shadow-active);
  transform: translateY(1px);
}

.neu-btn-primary {
  color: var(--neu-accent);
  font-weight: 600;
}

.neu-btn-accent {
  background: var(--neu-accent);
  color: #ffffff;
  box-shadow: 4px 4px 10px rgba(var(--neu-accent-rgb, 94, 114, 228), 0.35), -4px -4px 10px var(--neu-light);
}
.neu-btn-accent:hover:not(.is-disabled) {
  background: var(--neu-accent-hover);
}
.neu-btn-accent:active:not(.is-disabled) {
  background: var(--neu-accent);
  box-shadow: inset 2px 2px 5px rgba(0, 0, 0, 0.3);
}

.neu-btn-danger {
  color: var(--neu-danger);
}

.neu-btn.is-disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none !important;
  box-shadow: var(--shadow-flat-sm) !important;
}

.btn-icon {
  font-size: 1.25rem;
  flex-shrink: 0;
}

.spin {
  animation: neu-spin 1s linear infinite;
}

@keyframes neu-spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
