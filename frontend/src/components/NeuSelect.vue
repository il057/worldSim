<template>
  <div class="neu-select-wrapper" ref="wrapperRef">
    <!-- 下拉选择触发框 -->
    <button
      type="button"
      :class="['neu-select-trigger', 'neu-inset-sm', { 'is-open': isOpen, 'is-disabled': disabled }]"
      :disabled="disabled"
      @click="toggleOpen"
    >
      <div class="trigger-content">
        <Icon v-if="displayIcon" :icon="displayIcon" class="trigger-icon" />
        <span v-if="displayLabel" class="trigger-label">{{ displayLabel }}</span>
        <span v-else class="trigger-placeholder">{{ placeholder }}</span>
      </div>

      <div class="trigger-actions">
        <Icon
          icon="material-symbols:expand-more"
          class="chevron-icon"
          :class="{ 'rotate-180': isOpen }"
        />
      </div>
    </button>

    <!-- 下拉浮动面板 -->
    <Transition name="dropdown-anim">
      <div v-if="isOpen" class="dropdown-menu neu-card neu-flat">
        <!-- 搜索输入框 (当 searchable 为 true 时展示) -->
        <div v-if="searchable" class="dropdown-search neu-inset-sm">
          <Icon icon="material-symbols:search" class="search-icon" />
          <input
            ref="searchInputRef"
            v-model="searchQuery"
            class="search-input"
            :placeholder="searchPlaceholder || '搜索选项...'"
            @click.stop
          />
          <button
            v-if="searchQuery"
            type="button"
            class="search-clear-btn"
            @click.stop="searchQuery = ''"
          >
            <Icon icon="material-symbols:close" />
          </button>
        </div>

        <!-- 选项列表 -->
        <div class="options-list">
          <div
            v-for="opt in filteredOptions"
            :key="String(opt.value)"
            :class="['option-item', { 'is-selected': isSelected(opt.value) }]"
            @click="handleSelect(opt)"
          >
            <div class="option-left">
              <Icon v-if="opt.icon" :icon="opt.icon" class="option-icon" />
              <div class="option-texts">
                <span class="option-label">{{ opt.label }}</span>
                <span v-if="opt.description" class="option-desc">{{ opt.description }}</span>
              </div>
            </div>

            <div class="option-right">
              <span v-if="opt.badge" class="option-badge neu-flat-sm">{{ opt.badge }}</span>
              <Icon
                v-if="isSelected(opt.value)"
                icon="material-symbols:check"
                class="check-icon"
              />
            </div>
          </div>

          <!-- 空搜索结果展示 -->
          <div v-if="filteredOptions.length === 0" class="empty-options">
            <Icon icon="material-symbols:search-off" class="empty-icon" />
            <span>未找到匹配的选项</span>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { Icon } from '@iconify/vue'

export interface SelectOption {
  label: string
  value: any
  icon?: string
  badge?: string
  description?: string
}

const props = withDefaults(
  defineProps<{
    modelValue: any
    options: Array<string | SelectOption>
    placeholder?: string
    searchPlaceholder?: string
    disabled?: boolean
    searchable?: boolean
    icon?: string
  }>(),
  {
    placeholder: '请选择...',
    searchPlaceholder: '快速搜索...',
    disabled: false,
    searchable: false,
    icon: '',
  }
)

const emit = defineEmits<{
  (e: 'update:modelValue', value: any): void
  (e: 'change', value: any): void
}>()

const isOpen = ref(false)
const searchQuery = ref('')
const wrapperRef = ref<HTMLElement | null>(null)
const searchInputRef = ref<HTMLInputElement | null>(null)

// 统一规范化 options 为 SelectOption[]
const normalizedOptions = computed<SelectOption[]>(() => {
  return props.options.map((opt) => {
    if (typeof opt === 'string') {
      return { label: opt, value: opt }
    }
    return opt
  })
})

// 根据搜索关键词过滤选项
const filteredOptions = computed(() => {
  if (!searchQuery.value.trim()) return normalizedOptions.value
  const q = searchQuery.value.toLowerCase().trim()
  return normalizedOptions.value.filter(
    (opt) =>
      opt.label.toLowerCase().includes(q) ||
      (opt.description && opt.description.toLowerCase().includes(q)) ||
      (opt.badge && opt.badge.toLowerCase().includes(q))
  )
})

// 当前选中项对应的 Option
const selectedOption = computed(() => {
  return normalizedOptions.value.find((opt) => opt.value === props.modelValue)
})

// 触发框显示的文本
const displayLabel = computed(() => {
  if (selectedOption.value) return selectedOption.value.label
  if (props.modelValue) return String(props.modelValue)
  return ''
})

// 触发框图标
const displayIcon = computed(() => {
  if (selectedOption.value?.icon) return selectedOption.value.icon
  return props.icon
})

const isSelected = (val: any) => {
  return props.modelValue === val
}

const toggleOpen = () => {
  if (props.disabled) return
  isOpen.value = !isOpen.value
  if (isOpen.value && props.searchable) {
    searchQuery.value = ''
    nextTick(() => {
      searchInputRef.value?.focus()
    })
  }
}

const handleSelect = (opt: SelectOption) => {
  emit('update:modelValue', opt.value)
  emit('change', opt.value)
  isOpen.value = false
}

// 点击外部自动收起下拉框
const handleClickOutside = (e: MouseEvent) => {
  if (wrapperRef.value && !wrapperRef.value.contains(e.target as Node)) {
    isOpen.value = false
  }
}

// Escape 键关闭
const handleKeydown = (e: KeyboardEvent) => {
  if (isOpen.value && e.key === 'Escape') {
    isOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  window.removeEventListener('keydown', handleKeydown)
})

watch(() => props.disabled, (disabled) => {
  if (disabled) isOpen.value = false
})
</script>

<style scoped>
.neu-select-wrapper {
  position: relative;
  width: 100%;
}

.neu-select-trigger {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.65rem;
  padding: 0.6rem 0.85rem;
  border: none;
  background: var(--neu-surface);
  border-radius: 10px;
  cursor: pointer;
  font-family: inherit;
  font-size: 0.825rem;
  color: var(--neu-text-primary);
  text-align: left;
  outline: none;
  transition: all 0.2s ease;
  user-select: none;
}

.neu-select-trigger.is-open {
  border-color: var(--neu-accent);
}

.neu-select-trigger.is-disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.trigger-content {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  min-width: 0;
  flex: 1;
}

.trigger-icon {
  font-size: 1.15rem;
  color: var(--neu-accent);
  flex-shrink: 0;
}

.trigger-label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: 500;
}

.trigger-placeholder {
  color: var(--neu-text-muted);
}

.trigger-actions {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.chevron-icon {
  font-size: 1.25rem;
  color: var(--neu-text-secondary);
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.rotate-180 {
  transform: rotate(180deg);
}

/* 下拉菜单浮层 */
.dropdown-menu {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  width: 100%;
  background: var(--neu-surface);
  border-radius: 12px;
  box-shadow: 6px 8px 20px var(--neu-dark), -6px -8px 20px var(--neu-light);
  z-index: 1050;
  padding: 0.45rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  box-sizing: border-box;
}

.dropdown-search {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.4rem 0.65rem;
  border-radius: 8px;
  background: var(--neu-surface);
}

.search-icon {
  font-size: 1rem;
  color: var(--neu-text-secondary);
}

.search-input {
  flex: 1;
  border: none;
  background: transparent;
  outline: none;
  font-size: 0.775rem;
  color: var(--neu-text-primary);
  font-family: inherit;
}

.search-clear-btn {
  background: none;
  border: none;
  color: var(--neu-text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  font-size: 0.95rem;
  padding: 0;
}

.options-list {
  max-height: 220px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  padding-right: 0.2rem;
  scrollbar-width: thin;
  scrollbar-color: rgba(196, 201, 212, 0.55) transparent;
}

.options-list::-webkit-scrollbar {
  width: 5px;
}

.options-list::-webkit-scrollbar-track {
  background: transparent;
}

.options-list::-webkit-scrollbar-thumb {
  background: rgba(196, 201, 212, 0.55);
  border-radius: 999px;
}

.option-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.5rem 0.65rem;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.8rem;
  color: var(--neu-text-primary);
  transition: all 0.15s ease;
  user-select: none;
}

.option-item:hover {
  background: rgba(var(--neu-accent-rgb, 94, 114, 228), 0.08);
  color: var(--neu-accent);
}

.option-item.is-selected {
  background: var(--neu-surface);
  box-shadow: var(--shadow-flat-sm);
  color: var(--neu-accent);
  font-weight: 600;
}

.option-left {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  min-width: 0;
  flex: 1;
}

.option-icon {
  font-size: 1rem;
  color: var(--neu-accent);
  flex-shrink: 0;
}

.option-texts {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  min-width: 0;
}

.option-label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.option-desc {
  font-size: 0.7rem;
  color: var(--neu-text-secondary);
}

.option-right {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  flex-shrink: 0;
}

.option-badge {
  font-size: 0.675rem;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  color: var(--neu-accent);
  font-weight: 600;
}

.check-icon {
  font-size: 1.1rem;
  color: var(--neu-accent);
}

.empty-options {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.35rem;
  padding: 1.25rem 0.5rem;
  color: var(--neu-text-muted);
  font-size: 0.775rem;
}

.empty-icon {
  font-size: 1.6rem;
}

/* 动效 */
.dropdown-anim-enter-active,
.dropdown-anim-leave-active {
  transition: opacity 0.18s ease, transform 0.18s cubic-bezier(0.16, 1, 0.3, 1);
}

.dropdown-anim-enter-from,
.dropdown-anim-leave-to {
  opacity: 0;
  transform: translateY(-6px) scale(0.98);
}
</style>
