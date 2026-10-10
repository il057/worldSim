<template>
  <div v-if="isOpen" class="modal-backdrop" @click.self="$emit('close')">
    <NeuCard class="modal-card" variant="flat">
      <!-- 模态顶栏：与其它弹窗（世界书、系统配置、AI创建角色）完全对齐的统一规范 -->
      <div class="modal-header">
        <div class="header-title">
          <Icon icon="material-symbols:crisis-alert" class="title-icon" />
          <h3>触发突发事件</h3>
        </div>
        <button class="close-btn" @click="$emit('close')" title="关闭窗口">
          <Icon icon="material-symbols:close" />
        </button>
      </div>

      <!-- 导引说明文本 -->
      <p class="panel-desc">
        结合角色当前时空境遇与核心执念构思危机与变数，打破稳态为推演注入戏剧动力。支持由 AI 自主决定衍生，或由你主动指定具体事件。
      </p>

      <!-- 当前时空境遇浮雕卡 -->
      <div class="context-banner neu-inset-sm" v-if="currentState">
        <div class="context-item">
          <Icon icon="material-symbols:person" class="ctx-icon" />
          <span class="ctx-label">主角:</span>
          <span class="ctx-val">{{ currentCharacterName }}</span>
        </div>
        <div class="context-item">
          <Icon icon="material-symbols:schedule" class="ctx-icon" />
          <span class="ctx-label">时间:</span>
          <span class="ctx-val">{{ currentState.virtual_time }}</span>
        </div>
        <div class="context-item">
          <Icon icon="material-symbols:location-on" class="ctx-icon" />
          <span class="ctx-label">地点:</span>
          <span class="ctx-val">{{ currentState.location }}</span>
        </div>
      </div>

      <!-- 自定义事件输入区域 -->
      <div class="form-group">
        <div class="field-header">
          <label>
            <Icon icon="material-symbols:edit-note" class="label-icon" />
            自定义突发事件 (可选)
          </label>
          <span class="field-hint">留空即由 AI 结合情境自主决定</span>
        </div>
        <textarea
          v-model="customIncidentText"
          class="neu-textarea neu-inset-sm"
          rows="3"
          placeholder="例如：教导主任突然推门检查自习室 / 储物柜里发现了一封未署名的求助信 / 广播通知全员到操场集合..."
          @keydown.ctrl.enter="handleConfirm"
        ></textarea>
      </div>

      <!-- 底部动作按钮组：对齐系统统一 modal-actions -->
      <div class="modal-actions">
        <NeuButton
          icon="material-symbols:close"
          label="取消"
          @click="$emit('close')"
        />
        <NeuButton
          v-if="!customIncidentText.trim()"
          icon="material-symbols:smart-toy"
          label="由 AI 决定衍生"
          variant="accent"
          @click="handleAIDecide"
        />
        <NeuButton
          v-else
          icon="material-symbols:bolt"
          label="注入该事件"
          variant="accent"
          @click="handleConfirm"
        />
      </div>
    </NeuCard>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Icon } from '@iconify/vue'
import NeuCard from './NeuCard.vue'
import NeuButton from './NeuButton.vue'
import { useWorldStore } from '../stores/world'

const props = defineProps<{
  isOpen: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'confirm', incidentDescription?: string): void
}>()

const worldStore = useWorldStore()
const customIncidentText = ref('')

const currentState = computed(() => worldStore.currentState)
const currentCharacterName = computed(() => {
  if (worldStore.currentDetail?.name) {
    return `${worldStore.currentDetail.name} (${worldStore.currentDetail.title || '活动中'})`
  }
  return '当前角色'
})

const handleConfirm = () => {
  const desc = customIncidentText.value.trim() || undefined
  emit('confirm', desc)
  customIncidentText.value = ''
}

const handleAIDecide = () => {
  emit('confirm', undefined)
  customIncidentText.value = ''
}
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(30, 41, 59, 0.45);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.modal-card {
  width: 100%;
  max-width: 580px;
  background: var(--neu-surface);
  max-height: 90vh;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.title-icon {
  font-size: 1.35rem;
  color: var(--neu-accent);
}

.header-title h3 {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--neu-text-primary);
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.25rem;
  color: var(--neu-text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  padding: 0.25rem;
  transition: color 0.2s;
}

.close-btn:hover {
  color: var(--neu-text-primary);
}

.panel-desc {
  margin: 0;
  font-size: 0.8rem;
  color: var(--neu-text-secondary);
  line-height: 1.45;
}

.context-banner {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem 1.25rem;
  padding: 0.65rem 0.9rem;
  border-radius: 10px;
  font-size: 0.825rem;
}

.context-item {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.ctx-icon {
  font-size: 0.95rem;
  color: var(--neu-accent);
}

.ctx-label {
  color: var(--neu-text-secondary);
}

.ctx-val {
  color: var(--neu-text-primary);
  font-weight: 600;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.field-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.field-header label {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.825rem;
  font-weight: 600;
  color: var(--neu-text-primary);
}

.label-icon {
  font-size: 1rem;
  color: var(--neu-accent);
}

.field-hint {
  font-size: 0.75rem;
  color: var(--neu-text-secondary);
}

.neu-textarea {
  width: 100%;
  border: none;
  background: transparent;
  outline: none;
  box-sizing: border-box;
  font-size: 0.825rem;
  color: var(--neu-text-primary);
  padding: 0.65rem 0.8rem;
  border-radius: 10px;
  resize: vertical;
  min-height: 80px;
  font-family: inherit;
  line-height: 1.5;
}

.neu-textarea:focus {
  box-shadow: inset 3px 3px 6px var(--neu-dark), inset -3px -3px 6px var(--neu-light), 0 0 0 1px var(--neu-accent);
}

.neu-textarea::placeholder {
  color: var(--neu-text-secondary);
  opacity: 0.7;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 0.25rem;
}
</style>
