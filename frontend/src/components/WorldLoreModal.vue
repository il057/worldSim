<template>
  <div v-if="isOpen" class="modal-backdrop" @click.self="$emit('close')">
    <NeuCard class="modal-card" variant="flat">
      <div class="modal-header">
        <div class="header-title">
          <Icon icon="material-symbols:menu-book" class="title-icon" />
          <h3>世界书与法则条目 (WorldBook)</h3>
        </div>
        <div class="header-actions">
          <NeuButton
            icon="material-symbols:add"
            label="新增条目"
            variant="primary"
            @click="isAdding = !isAdding"
          />
          <button class="close-btn" @click="$emit('close')">
            <Icon icon="material-symbols:close" />
          </button>
        </div>
      </div>

      <p class="panel-desc">
        容纳完整酒馆世界书，无字数压榨截断。静态世界书常驻生效，动态条目根据地点与关键词自动激活。
      </p>

      <!-- 搜索筛选 -->
      <div class="search-box neu-inset-sm">
        <Icon icon="material-symbols:search" class="search-icon" />
        <input
          v-model="searchQuery"
          placeholder="搜索世界说法则、地点或触发词..."
          class="search-input"
        />
      </div>

      <!-- 新增表单 -->
      <NeuCard v-if="isAdding" class="add-card" variant="flat">
        <h4 class="form-title">录入新世界书条目</h4>
        <div class="form-grid">
          <input
            v-model="newLore.title"
            placeholder="条目标题 (如: 动力核心技术)"
            class="form-input neu-inset-sm"
            required
          />
          <div class="category-select">
            <label class="radio-label">
              <input type="radio" value="static" v-model="newLore.category" />
              全局常驻 (静态)
            </label>
            <label class="radio-label">
              <input type="radio" value="dynamic" v-model="newLore.category" />
              关键词触发 (动态)
            </label>
          </div>
          <input
            v-if="newLore.category === 'dynamic'"
            v-model="newLore.trigger_keys"
            placeholder="触发词列表 (逗号分隔，如: 动力核心,齿轮,工坊)"
            class="form-input neu-inset-sm"
          />
          <textarea
            v-model="newLore.content"
            placeholder="完整设定文本内容 (支持详尽世界观背景描述)..."
            rows="4"
            class="form-textarea neu-inset-sm"
            required
          />
          <div class="form-actions">
            <NeuButton
              icon="material-symbols:cancel"
              label="取消"
              @click="isAdding = false"
            />
            <NeuButton
              icon="material-symbols:check"
              label="保存条目"
              variant="accent"
              :loading="isSubmitting"
              @click="handleCreate"
            />
          </div>
        </div>
      </NeuCard>

      <!-- 条目列表 -->
      <div v-if="filteredLores.length" class="lore-list">
        <NeuCard
          v-for="lore in filteredLores"
          :key="lore.id"
          class="lore-item-card"
          variant="flat"
        >
          <div class="item-header">
            <div class="item-tags">
              <span
                class="type-pill neu-flat-sm"
                :class="lore.category === 'static' ? 'is-static' : 'is-dynamic'"
              >
                {{ lore.category === 'static' ? '全局常驻' : '动态触发' }}
              </span>
              <span class="lore-title">{{ lore.title }}</span>
            </div>
            <button class="delete-btn" title="删除条目" @click="handleDelete(lore.id)">
              <Icon icon="material-symbols:delete-outline" />
            </button>
          </div>

          <div v-if="lore.trigger_keys" class="triggers-tag neu-inset-sm">
            <Icon icon="material-symbols:bolt" class="trigger-icon" />
            <span>触发关键词: {{ lore.trigger_keys }}</span>
          </div>

          <p class="lore-content">{{ lore.content }}</p>
        </NeuCard>
      </div>

      <div v-else class="empty-state neu-card neu-inset-sm">
        <Icon icon="material-symbols:auto-stories" class="empty-icon" />
        <span>未找到匹配的世界书条目</span>
      </div>
    </NeuCard>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { Icon } from '@iconify/vue'
import NeuCard from './NeuCard.vue'
import NeuButton from './NeuButton.vue'
import { apiClient } from '../api/client'

const props = defineProps<{
  isOpen: boolean
  characterId: string
}>()

defineEmits<{
  (e: 'close'): void
}>()

const lores = ref<any[]>([])
const searchQuery = ref('')
const isAdding = ref(false)
const isSubmitting = ref(false)

const newLore = ref({
  category: 'static',
  trigger_keys: '',
  title: '',
  content: '',
})

const fetchLores = async () => {
  if (!props.characterId) return
  try {
    const res = await apiClient.getLores(props.characterId)
    lores.value = res.data
  } catch (err: any) {
    console.error('获取世界书条目失败:', err)
  }
}

onMounted(() => {
  if (props.isOpen) fetchLores()
})

watch(() => props.isOpen, (open) => {
  if (open) fetchLores()
})

watch(() => props.characterId, () => {
  if (props.isOpen) fetchLores()
})

const filteredLores = computed(() => {
  if (!searchQuery.value.trim()) return lores.value
  const q = searchQuery.value.toLowerCase()
  return lores.value.filter(
    (l) =>
      l.title.toLowerCase().includes(q) ||
      l.content.toLowerCase().includes(q) ||
      (l.trigger_keys && l.trigger_keys.toLowerCase().includes(q))
  )
})

const handleCreate = async () => {
  if (!newLore.value.title || !newLore.value.content) {
    alert('请填写标题与内容')
    return
  }
  isSubmitting.value = true
  try {
    await apiClient.createLore(props.characterId, newLore.value)
    newLore.value = { category: 'static', trigger_keys: '', title: '', content: '' }
    isAdding.value = false
    await fetchLores()
  } catch (err: any) {
    alert(`创建失败: ${err.message}`)
  } finally {
    isSubmitting.value = false
  }
}

const handleDelete = async (id: number) => {
  if (confirm('确定要删除此世界书条目吗？')) {
    try {
      await apiClient.deleteLore(props.characterId, id)
      await fetchLores()
    } catch (err: any) {
      alert(`删除失败: ${err.message}`)
    }
  }
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
  max-width: 680px;
  background: #f0f3f8;
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
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--neu-text-primary);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.25rem;
  color: var(--neu-text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
}

.panel-desc {
  font-size: 0.8rem;
  color: var(--neu-text-secondary);
  line-height: 1.45;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
}

.search-icon {
  font-size: 1.1rem;
  color: var(--neu-text-secondary);
}

.search-input {
  border: none;
  background: transparent;
  outline: none;
  width: 100%;
  font-size: 0.825rem;
  color: var(--neu-text-primary);
}

.add-card {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  background: #f0f3f8;
}

.form-title {
  font-size: 0.9rem;
  font-weight: 700;
  color: var(--neu-text-primary);
}

.form-grid {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}

.form-input, .form-textarea {
  width: 100%;
  border: none;
  padding: 0.6rem 0.75rem;
  background: var(--neu-surface);
  color: var(--neu-text-primary);
  font-family: inherit;
  font-size: 0.825rem;
  outline: none;
}

.category-select {
  display: flex;
  gap: 1rem;
  font-size: 0.8rem;
  color: var(--neu-text-primary);
}

.radio-label {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  cursor: pointer;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

.lore-list {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  max-height: 480px;
  overflow-y: auto;
  padding-right: 0.25rem;
}

.lore-item-card {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  padding: 0.95rem;
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.item-tags {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.type-pill {
  padding: 0.15rem 0.5rem;
  font-size: 0.7rem;
  font-weight: 700;
}

.type-pill.is-static {
  color: var(--neu-accent);
}

.type-pill.is-dynamic {
  color: var(--neu-warning);
}

.lore-title {
  font-size: 0.9rem;
  font-weight: 700;
  color: var(--neu-text-primary);
}

.delete-btn {
  background: none;
  border: none;
  color: var(--neu-text-secondary);
  cursor: pointer;
  font-size: 1.15rem;
  transition: color 0.2s;
}

.delete-btn:hover {
  color: var(--neu-danger);
}

.triggers-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.25rem 0.5rem;
  font-size: 0.725rem;
  color: var(--neu-warning);
  align-self: flex-start;
}

.trigger-icon {
  font-size: 0.85rem;
}

.lore-content {
  font-size: 0.8rem;
  color: var(--neu-text-secondary);
  line-height: 1.6;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 2rem;
  color: var(--neu-text-muted);
  font-size: 0.85rem;
}

.empty-icon {
  font-size: 2.25rem;
}
</style>
