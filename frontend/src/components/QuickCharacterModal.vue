<template>
  <div v-if="isOpen" class="modal-backdrop" @click.self="$emit('close')">
    <NeuCard class="modal-card" variant="flat">
      <div class="modal-header">
        <div class="header-title">
          <Icon icon="material-symbols:auto-awesome" class="title-icon" />
          <h3>AI 极简衍生创建角色</h3>
        </div>
        <button class="close-btn" @click="$emit('close')">
          <Icon icon="material-symbols:close" />
        </button>
      </div>

      <p class="modal-subtitle">
        仅需提供基础设定，AI 将自动补全角色的生活作息、深层执念与初始处境。
      </p>

      <form class="modal-form" @submit.prevent="handleSubmit">
        <div class="form-group">
          <label>
            <Icon icon="material-symbols:person" class="label-icon" />
            角色姓名
          </label>
          <input
            v-model="form.name"
            class="neu-input neu-inset-sm"
            placeholder="例如: 艾尔莎·克莱恩"
            required
          />
        </div>

        <div class="form-group">
          <label>
            <Icon icon="material-symbols:badge" class="label-icon" />
            社会身份 / 职业
          </label>
          <input
            v-model="form.role"
            class="neu-input neu-inset-sm"
            placeholder="例如: 废弃动力核心勘探员"
            required
          />
        </div>

        <div class="form-group">
          <label>
            <Icon icon="material-symbols:psychology" class="label-icon" />
            性格底色与处事风格
          </label>
          <input
            v-model="form.archetype"
            class="neu-input neu-inset-sm"
            placeholder="例如: 寡言警惕、对废旧金属有强烈直觉、重视诺言"
            required
          />
        </div>

        <div class="form-group">
          <label>
            <Icon icon="material-symbols:crisis-alert" class="label-icon" />
            开局处境与遭遇
          </label>
          <textarea
            v-model="form.initial_situation"
            class="neu-textarea neu-inset-sm"
            rows="3"
            placeholder="例如: 躲在暴雨下的旧仓库阁楼，随身干粮耗尽，门外有游荡者的手电筒光芒扫过..."
            required
          />
        </div>

        <div class="modal-actions">
          <NeuButton
            type="button"
            icon="material-symbols:cancel"
            label="取消"
            @click="$emit('close')"
          />
          <NeuButton
            type="submit"
            icon="material-symbols:auto-awesome"
            label="一键创建角色"
            variant="accent"
            :loading="isSubmitting"
          />
        </div>
      </form>
    </NeuCard>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { Icon } from '@iconify/vue'
import NeuCard from './NeuCard.vue'
import NeuButton from './NeuButton.vue'
import { apiClient } from '../api/client'

const props = defineProps<{
  isOpen: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'created', characterId: string): void
}>()

const isSubmitting = ref(false)

const form = reactive({
  name: '',
  role: '',
  archetype: '',
  initial_situation: '',
})

const handleSubmit = async () => {
  if (isSubmitting.value) return
  isSubmitting.value = true
  try {
    const res = await apiClient.generateQuickCharacter(form)
    emit('created', res.data.character_id)
    emit('close')
  } catch (err: any) {
    alert(`创建失败: ${err.message}`)
  } finally {
    isSubmitting.value = false
  }
}
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(45, 55, 72, 0.45);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.modal-card {
  width: 100%;
  max-width: 520px;
  background: #f0f3f8;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.title-icon {
  font-size: 1.35rem;
  color: var(--neu-accent);
}

.header-title h3 {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--neu-text-primary);
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.25rem;
  color: var(--neu-text-secondary);
  cursor: pointer;
}

.modal-subtitle {
  font-size: 0.8rem;
  color: var(--neu-text-secondary);
  margin-bottom: 1.25rem;
  line-height: 1.45;
}

.modal-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.form-group label {
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

.neu-input, .neu-textarea {
  width: 100%;
  padding: 0.65rem 0.85rem;
  border: none;
  outline: none;
  font-family: inherit;
  font-size: 0.85rem;
  color: var(--neu-text-primary);
  background: var(--neu-surface);
}

.neu-input:focus, .neu-textarea:focus {
  box-shadow: inset 3px 3px 6px var(--neu-dark), inset -3px -3px 6px var(--neu-light), 0 0 0 1px var(--neu-accent);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 0.75rem;
}
</style>
