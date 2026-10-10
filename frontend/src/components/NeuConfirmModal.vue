<template>
  <Transition name="confirm-fade">
    <div
      v-if="confirmState.isOpen"
      class="confirm-backdrop"
      @click.self="handleCancel"
      @keydown.esc="handleCancel"
      tabindex="-1"
    >
      <NeuCard class="confirm-card" variant="flat">
        <div class="confirm-body">
          <div :class="['confirm-icon-wrap', `is-${confirmState.variant || 'danger'}`]">
            <Icon :icon="confirmState.icon || 'material-symbols:warning'" class="confirm-icon" />
          </div>

          <div class="confirm-content">
            <h3 class="confirm-title">{{ confirmState.title || '操作确认' }}</h3>
            <p class="confirm-message">{{ confirmState.message }}</p>
          </div>
        </div>

        <div class="confirm-actions">
          <NeuButton
            icon="material-symbols:cancel"
            :label="confirmState.cancelText || '取消'"
            variant="normal"
            @click="handleCancel"
          />
          <NeuButton
            :icon="confirmState.variant === 'danger' ? 'material-symbols:delete-forever' : 'material-symbols:check'"
            :label="confirmState.confirmText || '确定'"
            :variant="confirmState.variant === 'danger' ? 'danger' : 'accent'"
            @click="handleConfirm"
          />
        </div>
      </NeuCard>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { Icon } from '@iconify/vue'
import NeuCard from './NeuCard.vue'
import NeuButton from './NeuButton.vue'
import { useConfirm } from '../composables/useConfirm'

const { confirmState, handleConfirm, handleCancel } = useConfirm()

const handleKeydown = (e: KeyboardEvent) => {
  if (confirmState.value.isOpen && e.key === 'Escape') {
    handleCancel()
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
.confirm-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(30, 41, 59, 0.48);
  backdrop-filter: blur(5px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  padding: 1.25rem;
  outline: none;
}

.confirm-card {
  width: 100%;
  max-width: 460px;
  background: #f0f3f8;
  border-radius: 18px;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  box-shadow: 10px 10px 25px rgba(166, 175, 195, 0.7), -10px -10px 25px rgba(255, 255, 255, 0.9);
}

.confirm-body {
  display: flex;
  align-items: flex-start;
  gap: 1rem;
}

.confirm-icon-wrap {
  width: 2.75rem;
  height: 2.75rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: var(--shadow-flat-sm);
}

.confirm-icon {
  font-size: 1.5rem;
}

.confirm-icon-wrap.is-danger {
  color: var(--neu-danger);
  background: #fff0f0;
}

.confirm-icon-wrap.is-warning {
  color: var(--neu-warning);
  background: #fffaf0;
}

.confirm-icon-wrap.is-primary {
  color: var(--neu-accent);
  background: #f0f4ff;
}

.confirm-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.confirm-title {
  font-size: 1rem;
  font-weight: 700;
  color: var(--neu-text-primary);
  margin: 0;
}

.confirm-message {
  font-size: 0.825rem;
  color: var(--neu-text-secondary);
  line-height: 1.55;
  margin: 0;
  white-space: pre-line;
}

.confirm-actions {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 0.75rem;
  padding-top: 0.5rem;
  border-top: 1px dashed rgba(166, 175, 195, 0.35);
}

/* 渐变与缩放动效 */
.confirm-fade-enter-active,
.confirm-fade-leave-active {
  transition: opacity 0.2s ease;
}

.confirm-fade-enter-from,
.confirm-fade-leave-to {
  opacity: 0;
}

.confirm-fade-enter-active .confirm-card {
  transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.confirm-fade-enter-from .confirm-card {
  transform: scale(0.95) translateY(6px);
}
</style>
