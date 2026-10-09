<template>
  <div :class="['neu-card', variantClass, { 'neu-hover-card': hover }]" :style="{ padding }">
    <slot />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    variant?: 'flat' | 'inset' | 'flat-sm' | 'inset-sm'
    padding?: string
    hover?: boolean
  }>(),
  {
    variant: 'flat',
    padding: '1.25rem',
    hover: false,
  }
)

const variantClass = computed(() => {
  switch (props.variant) {
    case 'inset':
      return 'neu-inset'
    case 'flat-sm':
      return 'neu-flat-sm'
    case 'inset-sm':
      return 'neu-inset-sm'
    default:
      return 'neu-flat'
  }
})
</script>

<style scoped>
.neu-card {
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.neu-hover-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-hover);
}
</style>
