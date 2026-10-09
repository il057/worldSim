<template>
  <div class="toast-container" aria-live="polite">
    <TransitionGroup name="toast-anim" tag="div" class="toast-list">
      <div
        v-for="item in toasts"
        :key="item.id"
        :class="['toast-card', `is-${item.type}`, 'neu-flat']"
      >
        <!-- 状态指示图标 -->
        <div class="toast-icon-wrap" :class="`icon-wrap-${item.type}`">
          <Icon :icon="getIconName(item.type)" class="toast-icon" />
        </div>

        <!-- 文本内容 -->
        <div class="toast-body">
          <div class="toast-title-row">
            <h4 class="toast-title">{{ item.title }}</h4>
            <span v-if="item.errorCode" class="error-code-badge neu-inset-sm">
              {{ item.errorCode }}
            </span>
          </div>
          <p class="toast-desc">{{ item.description }}</p>

          <!-- 交互操作按钮 (如有重试或前往设置) -->
          <div v-if="item.actionLabel && item.onAction" class="toast-action-bar">
            <button class="toast-action-btn neu-flat-sm" @click="handleAction(item)">
              <Icon :icon="getActionIcon(item.actionLabel)" class="action-btn-icon" />
              <span>{{ item.actionLabel }}</span>
            </button>
          </div>
        </div>

        <!-- 关闭按钮 -->
        <button class="toast-close-btn" title="关闭通知" @click="dismiss(item.id)">
          <Icon icon="material-symbols:close" class="close-icon" />
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup lang="ts">
import { Icon } from '@iconify/vue'
import { useToast, type ToastItem, type ToastType } from '../composables/useToast'

const { toasts, dismiss } = useToast()

const getIconName = (type: ToastType): string => {
  switch (type) {
    case 'error':
      return 'material-symbols:error'
    case 'warning':
      return 'material-symbols:warning'
    case 'success':
      return 'material-symbols:check-circle'
    case 'info':
    default:
      return 'material-symbols:info'
  }
}

const getActionIcon = (label: string): string => {
  if (label.includes('设置') || label.includes('API')) {
    return 'material-symbols:settings'
  }
  if (label.includes('重试')) {
    return 'material-symbols:refresh'
  }
  return 'material-symbols:arrow-forward'
}

const handleAction = (item: ToastItem) => {
  if (item.onAction) {
    item.onAction()
  }
  dismiss(item.id)
}
</script>

<style scoped>
.toast-container {
  position: fixed;
  top: 1.5rem;
  right: 1.5rem;
  z-index: 9999;
  max-width: 420px;
  width: calc(100vw - 3rem);
  pointer-events: none;
}

.toast-list {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.toast-card {
  pointer-events: auto;
  display: flex;
  align-items: flex-start;
  gap: 0.85rem;
  padding: 1rem 1.15rem;
  border-radius: 14px;
  background: var(--neu-surface);
  box-shadow: 8px 8px 18px var(--neu-dark), -8px -8px 18px var(--neu-light);
  border: 1px solid rgba(255, 255, 255, 0.4);
  position: relative;
  transition: all 0.25s ease;
}

.toast-icon-wrap {
  flex-shrink: 0;
  width: 2.25rem;
  height: 2.25rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-flat-sm);
}

.toast-icon {
  font-size: 1.25rem;
}

.icon-wrap-error {
  color: var(--neu-danger);
  background: #fff0f0;
}

.icon-wrap-warning {
  color: var(--neu-warning);
  background: #fffbf0;
}

.icon-wrap-success {
  color: var(--neu-success);
  background: #f0fff4;
}

.icon-wrap-info {
  color: var(--neu-accent);
  background: #f0f4ff;
}

.toast-body {
  flex: 1;
  min-width: 0;
}

.toast-title-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-bottom: 0.25rem;
}

.toast-title {
  margin: 0;
  font-size: 0.925rem;
  font-weight: 600;
  color: var(--neu-text-primary);
}

.error-code-badge {
  font-size: 0.7rem;
  font-family: monospace;
  padding: 0.1rem 0.4rem;
  border-radius: 4px;
  color: var(--neu-danger);
  font-weight: 600;
}

.toast-desc {
  margin: 0;
  font-size: 0.825rem;
  color: var(--neu-text-secondary);
  line-height: 1.5;
}

.toast-action-bar {
  margin-top: 0.6rem;
}

.toast-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.3rem 0.75rem;
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--neu-accent);
  background: var(--neu-surface);
  border: none;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.toast-action-btn:hover {
  color: var(--neu-accent-hover);
  box-shadow: var(--shadow-hover);
  transform: translateY(-1px);
}

.action-btn-icon {
  font-size: 0.95rem;
}

.toast-close-btn {
  flex-shrink: 0;
  background: none;
  border: none;
  color: var(--neu-text-muted);
  cursor: pointer;
  padding: 0.25rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: color 0.2s ease;
}

.toast-close-btn:hover {
  color: var(--neu-text-primary);
}

.close-icon {
  font-size: 1.1rem;
}

/* 动效 */
.toast-anim-enter-active,
.toast-anim-leave-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}

.toast-anim-enter-from {
  opacity: 0;
  transform: translateX(30px) scale(0.95);
}

.toast-anim-leave-to {
  opacity: 0;
  transform: translateY(-15px) scale(0.95);
}
</style>
