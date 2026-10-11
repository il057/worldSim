<template>
  <div class="world-lore-view">
    <!-- 标头控制栏 (固定在顶部) -->
    <div class="lore-view-header neu-flat-sm">
      <div class="header-left">
        <div class="header-title-group">
          <Icon icon="material-symbols:menu-book" class="view-icon" />
          <h2 class="view-heading">世界书与法则条目</h2>
          <span class="count-badge neu-inset-sm">共 {{ filteredLores.length }} 条设定</span>
        </div>
      </div>

      <div class="header-right">
        <!-- 搜索筛选输入框 -->
        <div class="search-box neu-inset-sm">
          <Icon icon="material-symbols:search" class="search-icon" />
          <input
            v-model="searchQuery"
            placeholder="搜索法则、地点或触发词..."
            class="search-input"
          />
        </div>

        <!-- 录入新条目按钮 -->
        <NeuButton
          class="add-lore-btn"
          icon="material-symbols:add"
          label="新增条目"
          variant="primary"
          @click="toggleAdd"
        />
      </div>
    </div>

    <!-- 可滚动内容区 -->
    <div class="lore-view-body" ref="loreBodyRef">
      <!-- 提示横幅 -->
      <div class="lore-desc-banner neu-flat-sm">
        <div class="banner-left">
          <Icon icon="material-symbols:auto-stories" class="banner-icon" />
          <p class="banner-text">
            管理当前虚拟世界的背景法则与设定。全局常驻条目在所有时刻生效，关键词触发条目随情境激活并送入因果裁决器。
          </p>
        </div>
      </div>

      <!-- 新增条目卡片 -->
      <NeuCard v-if="isAdding" class="add-card" variant="flat">
        <div class="form-header-row">
          <div class="form-title-wrap">
            <Icon icon="material-symbols:post-add" class="form-icon" />
            <h4 class="form-title">录入新世界书条目</h4>
          </div>
          <button class="close-form-btn" @click="isAdding = false" title="取消录入">
            <Icon icon="material-symbols:close" />
          </button>
        </div>

        <div class="form-grid">
          <input
            v-model="newLore.title"
            placeholder="条目标题 (如: 动力核心技术、旧城区禁令)"
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
            placeholder="完整设定文本内容 (支持详尽世界观背景与法则描述)..."
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

      <!-- 条目列表网格 -->
      <div v-if="filteredLores.length" class="lore-grid">
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
                placeholder="条目标题"
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
                placeholder="触发词列表 (逗号分隔)"
                class="form-input neu-inset-sm"
              />
              <textarea
                v-model="editLore.content"
                placeholder="完整设定文本内容..."
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

          <!-- 常态展示条目 -->
          <template v-else>
            <div class="item-header">
              <div class="item-tags">
                <span
                  class="type-pill neu-flat-sm"
                  :class="lore.category === 'static' ? 'is-static' : 'is-dynamic'"
                >
                  <Icon :icon="lore.category === 'static' ? 'material-symbols:public' : 'material-symbols:bolt'" class="pill-icon" />
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
              <span>触发词: {{ lore.trigger_keys }}</span>
            </div>

            <div class="lore-content-container">
              <p
                :ref="(el) => setLoreContentRef(lore.id, el as HTMLElement | null)"
                class="lore-content"
                :class="{ 'is-clamped': !isLoreExpanded(lore.id) }"
              >
                {{ lore.content }}
              </p>
              <button
                v-if="shouldShowExpand(lore.id, lore.content)"
                type="button"
                class="lore-expand-icon-btn"
                :title="isLoreExpanded(lore.id) ? '收起完整设定' : '展开查看完整设定'"
                @click="toggleLoreExpand(lore.id)"
              >
                <Icon
                  :icon="isLoreExpanded(lore.id) ? 'material-symbols:keyboard-arrow-up' : 'material-symbols:keyboard-arrow-down'"
                  class="expand-icon"
                />
              </button>
            </div>
          </template>
        </NeuCard>
      </div>

      <!-- 空白占位提示 -->
      <div v-else class="empty-state neu-card neu-flat">
        <Icon icon="material-symbols:menu-book" class="empty-icon" />
        <span class="empty-title">未找到匹配的世界书条目</span>
        <span class="empty-hint">点击右上角「新增条目」即可为该世界创建全新规则设定</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { Icon } from '@iconify/vue'
import NeuCard from './NeuCard.vue'
import NeuButton from './NeuButton.vue'
import { apiClient } from '../api/client'
import { useConfirm } from '../composables/useConfirm'
import { useToast } from '../composables/useToast'

const props = defineProps<{
  characterId?: string
}>()

defineEmits<{
  (e: 'back'): void
}>()

const { confirm } = useConfirm()
const toast = useToast()

const lores = ref<any[]>([])
const searchQuery = ref('')
const isAdding = ref(false)
const isSubmitting = ref(false)
const loreBodyRef = ref<HTMLElement | null>(null)

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

// 展开/收起长文本状态及 DOM 真实溢出检测
const expandedLoreIds = ref<Set<number>>(new Set())
const overflowingLoreIds = ref<Set<number>>(new Set())
const loreContentEls = new Map<number, HTMLElement>()
let resizeObserver: ResizeObserver | null = null

const isLoreExpanded = (id: number) => expandedLoreIds.value.has(id)

const setLoreContentRef = (id: number, el: HTMLElement | null) => {
  if (el) {
    loreContentEls.set(id, el)
    checkSingleOverflow(id, el)
  } else {
    loreContentEls.delete(id)
  }
}

const checkSingleOverflow = (id: number, el: HTMLElement) => {
  // 当处于折叠截断态时，精确检测 scrollHeight 是否大于 clientHeight（即实际渲染多于 2 行）
  if (!expandedLoreIds.value.has(id)) {
    const isOverflow = el.scrollHeight > el.clientHeight + 1
    if (isOverflow) {
      overflowingLoreIds.value.add(id)
    } else {
      overflowingLoreIds.value.delete(id)
    }
  }
}

const checkAllOverflows = () => {
  for (const [id, el] of loreContentEls.entries()) {
    checkSingleOverflow(id, el)
  }
}

const toggleLoreExpand = (id: number) => {
  if (expandedLoreIds.value.has(id)) {
    expandedLoreIds.value.delete(id)
    nextTick(() => {
      const el = loreContentEls.get(id)
      if (el) checkSingleOverflow(id, el)
    })
  } else {
    expandedLoreIds.value.add(id)
  }
}

const shouldShowExpand = (id: number, content?: string) => {
  // 若已被用户手动展开，必须保留收起折叠按钮
  if (expandedLoreIds.value.has(id)) return true
  // 若 DOM 测量显示当前行数已超过 2 行（发生截断溢出），显示展开按钮
  if (overflowingLoreIds.value.has(id)) return true
  // 兜底判定：若含有多段换行（大于 2 行），也直接显示展开按钮
  if (!content) return false
  const trimmed = content.trim()
  const lines = trimmed.split(/\r?\n/).filter(line => line.trim().length > 0)
  return lines.length > 2
}

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
    nextTick(() => {
      checkAllOverflows()
    })
  } catch (err: any) {
    console.error('获取世界书条目失败:', err)
  }
}

onMounted(() => {
  fetchLores()
  window.addEventListener('resize', checkAllOverflows)
  if (typeof ResizeObserver !== 'undefined' && loreBodyRef.value) {
    resizeObserver = new ResizeObserver(() => {
      checkAllOverflows()
    })
    resizeObserver.observe(loreBodyRef.value)
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', checkAllOverflows)
  if (resizeObserver) {
    resizeObserver.disconnect()
  }
})

watch(() => props.characterId, () => {
  editingLoreId.value = null
  fetchLores()
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

watch(filteredLores, () => {
  nextTick(() => {
    checkAllOverflows()
  })
})

const handleCreate = async () => {
  if (!props.characterId) {
    toast.show({ type: 'warning', title: '未选定角色', description: '请先选定或创建一个角色' })
    return
  }
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
  if (!props.characterId) return
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
  if (!props.characterId) return
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
.world-lore-view {
  width: 100%;
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: var(--neu-bg);
  overflow: hidden;
  border-radius: var(--neu-radius, 14px);
}

/* 顶部标头栏 */
.lore-view-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1.25rem;
  flex-shrink: 0;
  z-index: 10;
  border-bottom: 1px solid var(--neu-border, rgba(255, 255, 255, 0.35));
  gap: 1rem;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  min-width: 0;
}

.header-title-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}

.view-icon {
  font-size: 1.35rem;
  color: var(--neu-accent);
  flex-shrink: 0;
}

.view-heading {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--neu-text-primary);
  margin: 0;
  white-space: nowrap;
}

.count-badge {
  font-size: 0.725rem;
  padding: 0.15rem 0.5rem;
  border-radius: 6px;
  color: var(--neu-text-secondary);
  font-weight: 600;
  white-space: nowrap;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  flex-shrink: 0;
}

.search-box {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0 0.85rem;
  height: 38px;
  border-radius: 10px;
  width: 220px;
  box-sizing: border-box;
}

.search-icon {
  font-size: 1.05rem;
  color: var(--neu-text-secondary);
  flex-shrink: 0;
}

.search-input {
  border: none;
  background: transparent;
  outline: none;
  width: 100%;
  font-size: 0.8rem;
  color: var(--neu-text-primary);
}

.add-lore-btn {
  height: 38px !important;
  box-sizing: border-box;
  padding: 0 1rem !important;
  border-radius: 10px !important;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  white-space: nowrap;
}

/* 窄屏响应式：搜索框与新增条目下沉至第二行，新增条目省略文字只留加号图标 */
@media (max-width: 900px) {
  .lore-view-header {
    flex-direction: column;
    align-items: stretch;
    padding: 0.75rem 1rem;
    gap: 0.65rem;
  }

  .header-left {
    width: 100%;
    justify-content: space-between;
  }

  .header-right {
    width: 100%;
    display: flex;
    gap: 0.5rem;
  }

  .search-box {
    flex: 1;
    width: auto;
  }

  .add-lore-btn {
    width: 38px !important;
    padding: 0 !important;
    flex-shrink: 0;
  }

  .add-lore-btn :deep(.btn-label) {
    display: none;
  }
}

/* 可滚动正文主体 */
.lore-view-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 1rem 1.25rem 2rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  scrollbar-width: thin;
  scrollbar-color: var(--scrollbar-thumb) transparent;
}

.lore-view-body::-webkit-scrollbar {
  width: 6px;
}

.lore-view-body::-webkit-scrollbar-track {
  background: transparent;
}

.lore-view-body::-webkit-scrollbar-thumb {
  background: var(--scrollbar-thumb);
  border-radius: 999px;
}

.lore-view-body::-webkit-scrollbar-thumb:hover {
  background: var(--scrollbar-thumb-hover);
}

/* 提示横幅 */
.lore-desc-banner {
  padding: 0.75rem 1rem;
  border-radius: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.banner-left {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.banner-icon {
  font-size: 1.25rem;
  color: var(--neu-accent);
  flex-shrink: 0;
}

.banner-text {
  font-size: 0.8rem;
  color: var(--neu-text-secondary);
  line-height: 1.45;
  margin: 0;
}

/* 新增条目卡片 */
.add-card {
  padding: 1.15rem;
  border-radius: 14px;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.form-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.form-title-wrap {
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.form-icon {
  font-size: 1.15rem;
  color: var(--neu-accent);
}

.form-title {
  font-size: 0.925rem;
  font-weight: 700;
  color: var(--neu-text-primary);
  margin: 0;
}

.close-form-btn {
  background: none;
  border: none;
  color: var(--neu-text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  font-size: 1.1rem;
}

.form-grid {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.form-input, .form-textarea {
  width: 100%;
  border: none;
  padding: 0.65rem 0.85rem;
  background: var(--neu-surface);
  color: var(--neu-text-primary);
  font-family: inherit;
  font-size: 0.825rem;
  outline: none;
  border-radius: 8px;
}

.form-textarea {
  resize: vertical;
  line-height: 1.5;
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
  background: var(--neu-surface);
  font-weight: 700;
  box-shadow: var(--shadow-flat-sm);
}

.segment-icon {
  font-size: 1rem;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding-top: 0.25rem;
}

/* 条目卡片单列全宽布局 (避免双列挤压编辑框与正文) */
.lore-grid {
  display: flex;
  flex-direction: column;
  gap: 1.15rem;
  width: 100%;
}

.lore-item-card {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1.15rem;
  border-radius: 14px;
  width: 100%;
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
}

.item-tags {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}

.type-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.2rem 0.5rem;
  font-size: 0.7rem;
  font-weight: 700;
  border-radius: 6px;
  white-space: nowrap;
}

.pill-icon {
  font-size: 0.85rem;
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
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-actions {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  flex-shrink: 0;
}

.action-btn {
  background: none;
  border: none;
  color: var(--neu-text-secondary);
  cursor: pointer;
  font-size: 1.15rem;
  padding: 0.25rem;
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

.triggers-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.25rem 0.55rem;
  font-size: 0.725rem;
  color: var(--neu-warning);
  align-self: flex-start;
  border-radius: 6px;
}

.trigger-icon {
  font-size: 0.85rem;
}

.lore-content-container {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.lore-content {
  font-size: 0.825rem;
  color: var(--neu-text-secondary);
  line-height: 1.6;
  margin: 0;
  white-space: pre-line;
  transition: all 0.2s ease;
}

.lore-content.is-clamped {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.lore-expand-icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  align-self: center; /* 居中于卡片中轴 */
  width: 36px;
  height: 22px;
  padding: 0;
  margin-top: 0.35rem;
  background: transparent; /* 纯平无凸起 */
  border: none;
  border-radius: 6px;
  color: var(--neu-text-secondary);
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
}

.lore-expand-icon-btn:hover {
  color: var(--neu-accent);
}

.expand-icon {
  font-size: 1.35rem;
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
  border-bottom: 1px dashed rgba(196, 201, 212, 0.35);
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

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.65rem;
  padding: 3rem 1.5rem;
  text-align: center;
  border-radius: 14px;
}

.empty-icon {
  font-size: 2.75rem;
  color: var(--neu-accent);
  opacity: 0.7;
}

.empty-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--neu-text-primary);
}

.empty-hint {
  font-size: 0.8rem;
  color: var(--neu-text-muted);
}

@media (max-width: 900px) {
  .search-box {
    width: 150px;
  }
}
</style>
