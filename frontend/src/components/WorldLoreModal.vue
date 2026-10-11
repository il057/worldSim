<template>
  <div v-if="isOpen" class="modal-backdrop" @click.self="$emit('close')">
    <NeuCard class="modal-card" variant="flat">
      <div class="modal-header">
        <div class="header-title">
          <Icon icon="material-symbols:menu-book" class="title-icon" />
          <h3>世界书与法则条目</h3>
        </div>
        <div class="header-actions">
          <NeuButton
            icon="material-symbols:add"
            label="新增条目"
            variant="primary"
            @click="toggleAdd"
          />
          <button class="close-btn" @click="$emit('close')">
            <Icon icon="material-symbols:close" />
          </button>
        </div>
      </div>

      <div class="modal-scroll-body">
        <p class="panel-desc">
        管理当前世界的背景法则与设定。常驻条目全局生效，动态条目根据情境关键词自动激活。
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
          <div class="segmented-control neu-inset-sm">
            <button
              type="button"
              class="segment-btn"
              :class="{ active: newLore.category === 'static' }"
              @click="newLore.category = 'static'"
            >
              <Icon icon="material-symbols:public" class="segment-icon" />
              <span>全局常驻 (静态)</span>
            </button>
            <button
              type="button"
              class="segment-btn"
              :class="{ active: newLore.category === 'dynamic' }"
              @click="newLore.category = 'dynamic'"
            >
              <Icon icon="material-symbols:bolt" class="segment-icon" />
              <span>关键词触发 (动态)</span>
            </button>
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
          <!-- 编辑模式表单 -->
          <div v-if="editingLoreId === lore.id" class="edit-form">
            <div class="edit-header">
              <span class="edit-title">编辑设定条目</span>
              <span class="edit-id-tag">#{{ lore.id }}</span>
            </div>
            <div class="form-grid">
              <input
                v-model="editLore.title"
                placeholder="条目标题 (如: 动力核心技术)"
                class="form-input neu-inset-sm"
                required
              />
              <div class="segmented-control neu-inset-sm">
                <button
                  type="button"
                  class="segment-btn"
                  :class="{ active: editLore.category === 'static' }"
                  @click="editLore.category = 'static'"
                >
                  <Icon icon="material-symbols:public" class="segment-icon" />
                  <span>全局常驻 (静态)</span>
                </button>
                <button
                  type="button"
                  class="segment-btn"
                  :class="{ active: editLore.category === 'dynamic' }"
                  @click="editLore.category = 'dynamic'"
                >
                  <Icon icon="material-symbols:bolt" class="segment-icon" />
                  <span>关键词触发 (动态)</span>
                </button>
              </div>
              <input
                v-if="editLore.category === 'dynamic'"
                v-model="editLore.trigger_keys"
                placeholder="触发词列表 (逗号分隔，如: 动力核心,齿轮,工坊)"
                class="form-input neu-inset-sm"
              />
              <textarea
                v-model="editLore.content"
                placeholder="完整设定文本内容 (支持详尽世界观背景描述)..."
                rows="4"
                class="form-textarea neu-inset-sm"
                required
              />
              <div class="form-actions">
                <NeuButton
                  icon="material-symbols:cancel"
                  label="取消"
                  @click="cancelEdit"
                />
                <NeuButton
                  icon="material-symbols:check"
                  label="保存修改"
                  variant="accent"
                  :loading="isUpdating"
                  @click="handleUpdate(lore.id)"
                />
              </div>
            </div>
          </div>

          <!-- 常态展示 -->
          <template v-else>
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
              <div class="item-actions">
                <button class="action-btn edit-btn" title="编辑条目" @click="startEdit(lore)">
                  <Icon icon="material-symbols:edit-note" />
                </button>
                <button class="action-btn delete-btn" title="删除条目" @click="handleDelete(lore.id)">
                  <Icon icon="material-symbols:delete-outline" />
                </button>
              </div>
            </div>

            <div v-if="lore.trigger_keys" class="triggers-tag neu-inset-sm">
              <Icon icon="material-symbols:bolt" class="trigger-icon" />
              <span>触发关键词: {{ lore.trigger_keys }}</span>
            </div>

            <p class="lore-content">{{ lore.content }}</p>
          </template>
        </NeuCard>
      </div>

      <div v-else class="empty-state neu-card neu-inset-sm">
        <Icon icon="material-symbols:auto-stories" class="empty-icon" />
        <span>未找到匹配的世界书条目</span>
      </div>
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
import { useConfirm } from '../composables/useConfirm'
import { useToast } from '../composables/useToast'

const props = defineProps<{
  isOpen: boolean
  characterId: string
}>()

defineEmits<{
  (e: 'close'): void
}>()

const { confirm } = useConfirm()
const toast = useToast()

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

const editingLoreId = ref<number | null>(null)
const isUpdating = ref(false)
const editLore = ref({
  category: 'static',
  trigger_keys: '',
  title: '',
  content: '',
})

const toggleAdd = () => {
  isAdding.value = !isAdding.value
  if (isAdding.value) {
    editingLoreId.value = null
  }
}

const startEdit = (lore: any) => {
  isAdding.value = false
  editingLoreId.value = lore.id
  editLore.value = {
    category: lore.category || 'static',
    trigger_keys: lore.trigger_keys || '',
    title: lore.title || '',
    content: lore.content || '',
  }
}

const cancelEdit = () => {
  editingLoreId.value = null
  editLore.value = {
    category: 'static',
    trigger_keys: '',
    title: '',
    content: '',
  }
}

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
  if (open) {
    editingLoreId.value = null
    fetchLores()
  }
})

watch(() => props.characterId, () => {
  if (props.isOpen) {
    editingLoreId.value = null
    fetchLores()
  }
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
    toast.show({ type: 'warning', title: '请填写完整', description: '请填写标题与完整设定内容' })
    return
  }
  isSubmitting.value = true
  try {
    await apiClient.createLore(props.characterId, newLore.value)
    newLore.value = { category: 'static', trigger_keys: '', title: '', content: '' }
    isAdding.value = false
    await fetchLores()
    toast.showSuccess('条目已录入', '新世界书设定已成功录入世界法则。')
  } catch (err: any) {
    toast.show({ type: 'error', title: '创建失败', description: err.message })
  } finally {
    isSubmitting.value = false
  }
}

const handleUpdate = async (id: number) => {
  if (!editLore.value.title.trim() || !editLore.value.content.trim()) {
    toast.show({ type: 'warning', title: '请填写完整', description: '请填写标题与完整设定内容' })
    return
  }
  isUpdating.value = true
  try {
    await apiClient.updateLore(props.characterId, id, editLore.value)
    editingLoreId.value = null
    await fetchLores()
    toast.showSuccess('条目已更新', '世界书设定已成功更新。')
  } catch (err: any) {
    toast.show({ type: 'error', title: '更新失败', description: err.message })
  } finally {
    isUpdating.value = false
  }
}

const handleDelete = async (id: number) => {
  const confirmed = await confirm({
    title: '删除世界书条目',
    message: '确定要删除此世界书条目吗？该设定将不再作为法则常驻或被触发词激活。',
    confirmText: '删除条目',
    cancelText: '取消',
    variant: 'danger',
    icon: 'material-symbols:delete-outline',
  })
  if (confirmed) {
    try {
      await apiClient.deleteLore(props.characterId, id)
      if (editingLoreId.value === id) {
        editingLoreId.value = null
      }
      await fetchLores()
      toast.showSuccess('条目已删除', '该世界书条目已成功移除。')
    } catch (err: any) {
      toast.show({ type: 'error', title: '删除失败', description: err.message })
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
  background: var(--neu-surface);
  max-height: 88vh;
  overflow: hidden; /* 防止外露直角滚动条破坏模态框圆角 */
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.modal-scroll-body {
  overflow-y: auto;
  overflow-x: hidden;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 0.25rem 0.85rem 1.75rem 0.85rem;
  scrollbar-width: thin;
  scrollbar-color: rgba(196, 201, 212, 0.55) transparent;
}

.modal-scroll-body::-webkit-scrollbar {
  width: 5px;
}

.modal-scroll-body::-webkit-scrollbar-track {
  background: transparent;
}

.modal-scroll-body::-webkit-scrollbar-thumb {
  background: rgba(196, 201, 212, 0.55);
  border-radius: 999px;
}

.modal-scroll-body::-webkit-scrollbar-thumb:hover {
  background: var(--neu-text-secondary);
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
  padding: 0.55rem 0.85rem;
  border-radius: 12px;
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
  background: var(--neu-surface);
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

.segmented-control {
  display: flex;
  padding: 0.25rem;
  border-radius: 10px;
  gap: 0.35rem;
}

.segment-btn {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  padding: 0.45rem 0.75rem;
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--neu-text-secondary);
  background: transparent;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  user-select: none;
}

.segment-btn:hover:not(.active) {
  color: var(--neu-text-primary);
}

.segment-btn.active {
  color: var(--neu-accent);
  background: var(--neu-surface, #f0f3f8);
  font-weight: 600;
  box-shadow: var(--shadow-flat-sm);
}

.segment-icon {
  font-size: 1rem;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

.lore-list {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  padding: 0.25rem 0 0.5rem 0;
  overflow: visible; /* 严禁对子项阴影做硬边裁剪，彻底杜绝生硬长方形截断 */
}

.lore-item-card {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  padding: 1.1rem;
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

.item-actions {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.action-btn {
  background: none;
  border: none;
  color: var(--neu-text-secondary);
  cursor: pointer;
  font-size: 1.15rem;
  padding: 0.2rem;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.edit-btn:hover {
  color: var(--neu-accent);
  background: rgba(var(--neu-accent-rgb, 94, 114, 228), 0.12);
}

.delete-btn:hover {
  color: var(--neu-danger);
  background: rgba(239, 68, 68, 0.12);
}

.edit-form {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.edit-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 0.35rem;
  border-bottom: 1px dashed rgba(0, 0, 0, 0.08);
}

.edit-title {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--neu-accent);
}

.edit-id-tag {
  font-size: 0.75rem;
  color: var(--neu-text-muted);
  font-family: monospace;
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
