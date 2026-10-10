<template>
  <div v-if="isOpen" class="modal-backdrop" @click.self="$emit('close')">
    <NeuCard class="modal-card" variant="flat">
      <div class="modal-header">
        <div class="header-title">
          <Icon icon="material-symbols:auto-awesome" class="title-icon" />
          <h3>AI 角色构思与世界衍生</h3>
        </div>
        <button class="close-btn" @click="$emit('close')">
          <Icon icon="material-symbols:close" />
        </button>
      </div>

      <p class="modal-subtitle">
        提供基础灵感或全部留空，AI 将为您智能衍生立体主角画像、具有张力的人际关系网与初始世界书。
        <span class="optional-tip">所有字段均为可选。</span>
      </p>

      <form class="modal-form" @submit.prevent="handleSubmit">
        <div class="form-grid-row">
          <div class="form-group">
            <label>
              <Icon icon="material-symbols:person" class="label-icon" />
              角色姓名
            </label>
            <input
              v-model="form.name"
              class="neu-input neu-inset-sm"
              placeholder="留空由 AI 自动命名，或输入如: 艾尔莎"
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
              placeholder="例如: 炼金学徒 / 浮空艇巡航员"
            />
          </div>
        </div>

        <div class="form-grid-row">
          <div class="form-group">
            <label>
              <Icon icon="material-symbols:wc" class="label-icon" />
              性别倾向
            </label>
            <NeuSelect
              v-model="form.gender"
              :options="genderOptions"
              placeholder="选择或由 AI 自动推演"
            />
          </div>

          <div class="form-group">
            <label>
              <Icon icon="material-symbols:calendar-today" class="label-icon" />
              出生日期 / 历法时间
            </label>
            <input
              v-model="form.birthday"
              class="neu-input neu-inset-sm"
              placeholder="例如: 霜降月 12日 或 10月15日"
            />
          </div>
        </div>

        <div class="form-group">
          <label>
            <Icon icon="material-symbols:face" class="label-icon" />
            外貌体征与衣着风格
          </label>
          <input
            v-model="form.appearance"
            class="neu-input neu-inset-sm"
            placeholder="例如: 银白短发、右眼佩戴黄铜单片镜、身披磨损法袍"
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
            placeholder="例如: 表面温和实则多疑、对学术极其执着、不擅拒绝他人"
          />
        </div>

        <div class="form-group highlight-group">
          <div class="label-with-tip">
            <label>
              <Icon icon="material-symbols:hub" class="label-icon accent" />
              世界观与社交网络指引 (AI 智能解析 NPC 与世界书)
            </label>
            <span class="field-hint">核心推荐: 提及的角色将自动生成为关系网 NPC，提及的环境将提炼为世界书</span>
          </div>
          <textarea
            v-model="form.world_guidance"
            class="neu-textarea neu-inset-sm guidance-textarea"
            rows="3"
            placeholder="例如: ta朋友很多，在学校最好的朋友是一个擅长火魔法的金发女生；欠着高年级恶霸一笔炼金实验债务；这所学校是浮空岛上的封闭魔法学院，主角主修召唤学但偷偷研究禁忌炼金..."
          />
        </div>

        <div class="form-group">
          <label>
            <Icon icon="material-symbols:crisis-alert" class="label-icon" />
            开局微观处境与危机
          </label>
          <textarea
            v-model="form.initial_situation"
            class="neu-textarea neu-inset-sm"
            rows="2"
            placeholder="例如: 深夜在旧礼拜堂阁楼整理违禁药剂，门外突然响起了风纪督导巡查的脚步声..."
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
            label="AI 构思推演蓝图"
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
import NeuSelect from './NeuSelect.vue'
import { apiClient } from '../api/client'
import type { CardParseResponse } from '../api/client'
import { useToast } from '../composables/useToast'

const toast = useToast()

defineProps<{
  isOpen: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'blueprint', data: CardParseResponse): void
}>()

const isSubmitting = ref(false)

const genderOptions = [
  { label: '由 AI 自动推演 (随机/匹配背景)', value: '' },
  { label: '女性', value: '女' },
  { label: '男性', value: '男' },
  { label: '非二元 / 中性', value: '非二元' },
  { label: '保密 / 未明', value: '保密' },
]

const form = reactive({
  name: '',
  gender: '',
  birthday: '',
  role: '',
  appearance: '',
  archetype: '',
  world_guidance: '',
  initial_situation: '',
})

const handleSubmit = async () => {
  if (isSubmitting.value) return
  isSubmitting.value = true
  try {
    const res = await apiClient.generateQuickBlueprint(form)
    toast.showSuccess('AI 角色蓝图衍生完成，已载入全量设定审查面板！')
    emit('blueprint', res.data)
    emit('close')
  } catch (err: any) {
    toast.show({
      type: 'error',
      title: '构思衍生失败',
      description: err.response?.data?.detail || err.message || '网络或推演服务发生异常',
    })
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
  max-width: 620px;
  max-height: 90vh;
  overflow-y: auto;
  background: #f0f3f8;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.35rem;
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
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.25rem;
  border-radius: 4px;
  transition: color 0.15s ease;
}

.close-btn:hover {
  color: var(--neu-text-primary);
}

.modal-subtitle {
  font-size: 0.8rem;
  color: var(--neu-text-secondary);
  margin-bottom: 1.1rem;
  line-height: 1.45;
}

.optional-tip {
  color: var(--neu-accent);
  font-weight: 600;
}

.modal-form {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.form-grid-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}

@media (max-width: 640px) {
  .form-grid-row {
    grid-template-columns: 1fr;
  }
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.form-group label {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--neu-text-primary);
}

.label-icon {
  font-size: 0.95rem;
  color: var(--neu-text-secondary);
}

.label-icon.accent {
  color: var(--neu-accent);
}

.label-with-tip {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.field-hint {
  font-size: 0.725rem;
  color: var(--neu-accent);
  font-weight: 500;
}

.highlight-group {
  padding: 0.65rem 0.75rem;
  border-radius: 8px;
  background: rgba(79, 70, 229, 0.04);
  border: 1px dashed rgba(79, 70, 229, 0.25);
}

.neu-input,
.neu-textarea {
  width: 100%;
  padding: 0.6rem 0.8rem;
  border: none;
  outline: none;
  font-family: inherit;
  font-size: 0.85rem;
  color: var(--neu-text-primary);
  background: var(--neu-surface);
  border-radius: 6px;
  box-sizing: border-box;
}

.neu-input:focus,
.neu-textarea:focus {
  box-shadow: inset 3px 3px 6px var(--neu-dark), inset -3px -3px 6px var(--neu-light), 0 0 0 1px var(--neu-accent);
}

.guidance-textarea {
  resize: vertical;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 0.5rem;
}
</style>
