<template>
  <div
    class="avatar-badge"
    :class="{ 'is-character': isCharacter, 'size-sm': size === 'sm', 'size-md': size === 'md' }"
    :title="name"
  >
    <img
      v-if="!hasError && resolvedAvatarUrl"
      :src="resolvedAvatarUrl"
      :alt="name"
      class="avatar-img"
      @error="hasError = true"
    />
    <span v-else class="avatar-initial" :style="fallbackStyle">{{ initial }}</span>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const props = withDefaults(
  defineProps<{
    name: string
    avatarUrl?: string
    isCharacter?: boolean
    size?: 'sm' | 'md'
  }>(),
  {
    avatarUrl: '',
    isCharacter: false,
    size: 'md',
  }
)

const hasError = ref(false)

const cleanName = computed(() => {
  return (props.name || '').trim().replace(/^来自\s+/, '')
})

const initial = computed(() => {
  return cleanName.value ? cleanName.value.slice(0, 1) : '友'
})

import { useTheme } from '../../composables/useTheme'

const { getDicebearAvatarUrl } = useTheme()

// 优先采用显式传入头像；缺省时采用贴合全局主题色与深浅背景的 DiceBear Slice 风格接口
const resolvedAvatarUrl = computed(() => {
  if (props.avatarUrl) return props.avatarUrl
  if (!cleanName.value) return ''
  return getDicebearAvatarUrl(cleanName.value)
})

// 离线/网络加载失败时的自适应渐变保底
const fallbackStyle = computed(() => {
  let hash = 0
  for (let i = 0; i < cleanName.value.length; i++) {
    hash = cleanName.value.charCodeAt(i) + ((hash << 5) - hash)
  }
  const hue = Math.abs(hash) % 360
  return {
    background: `linear-gradient(135deg, hsl(${hue}, 38%, 56%), hsl(${(hue + 40) % 360}, 42%, 46%))`,
  }
})
</script>

<style scoped>
.avatar-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  color: #ffffff;
  font-weight: 700;
  font-size: 0.825rem;
  flex-shrink: 0;
  overflow: hidden;
  background: var(--neu-surface, #e6e9ef);
  box-shadow: 2px 2px 5px var(--neu-dark, #c4c9d4), -2px -2px 5px var(--neu-light, #ffffff);
  user-select: none;
}

.avatar-badge.size-sm {
  width: 28px;
  height: 28px;
  font-size: 0.725rem;
  border-radius: 8px;
}

.avatar-badge.is-character {
  box-shadow: 0 0 6px rgba(var(--neu-accent-rgb, 94, 114, 228), 0.35), 2px 2px 5px var(--neu-dark, #c4c9d4);
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-initial {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  text-transform: uppercase;
  color: #ffffff;
  font-weight: 700;
}
</style>
