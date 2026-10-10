<template>
  <div class="character-drawer">
    <!-- 头部标签页切换: 故事时间线 vs 角色名录 (采用新拟态内凹分段槽) -->
    <div class="drawer-tabs neu-inset-sm">
      <button
        :class="['tab-btn', { 'is-active': activeTab === 'timeline' }]"
        @click="activeTab = 'timeline'"
      >
        <Icon icon="material-symbols:timeline" class="tab-icon" />
        <span>故事编年 ({{ timeline.length }})</span>
      </button>
      <button
        :class="['tab-btn', { 'is-active': activeTab === 'roster' }]"
        @click="activeTab = 'roster'"
      >
        <Icon icon="material-symbols:group" class="tab-icon" />
        <span>角色菜单 ({{ characters.length }})</span>
      </button>
    </div>

    <!-- 视图 1: 故事编年轴 (平日显示时间线) -->
    <div v-if="activeTab === 'timeline'" class="timeline-view">
      <div class="view-header">
        <span class="view-title">故事切片索引目录</span>
        <span class="view-sub">点击切片快速定位阅读</span>
      </div>

      <div v-if="timeline.length" class="timeline-list">
        <div
          v-for="log in timeline"
          :key="log.id"
          class="timeline-index-item neu-flat-sm neu-hover"
          @click="$emit('select-tick', log.id)"
        >
          <div class="index-top">
            <span class="index-tick">第 {{ log.tick_index }} 刻</span>
            <span class="index-time">{{ log.virtual_time }}</span>
          </div>
          <div class="index-loc">
            <Icon icon="material-symbols:location-on" class="mini-icon" />
            <span>{{ log.location }}</span>
          </div>
          <p class="index-beat">{{ log.plot_beat.slice(0, 50) }}...</p>
        </div>
      </div>

      <div v-else class="empty-hint neu-card neu-inset-sm">
        <Icon icon="material-symbols:hourglass-empty" class="empty-icon" />
        <span>暂无推演历史记录</span>
      </div>
    </div>

    <!-- 视图 2: 角色菜单与切换 -->
    <div v-else class="roster-view">
      <!-- 统一视图标题，与时间线视图对齐视觉节奏 -->
      <div class="view-header">
        <span class="view-title">世界观测名录</span>
        <span class="view-sub">点击卡片切换观测视角</span>
      </div>

      <!-- 操作栏：两端全宽对齐网格，主次清晰的新拟态按钮体系 -->
      <div class="roster-actions">
        <NeuButton
          class="roster-action-btn roster-btn-quick"
          icon="material-symbols:auto-awesome"
          label="快速新建"
          variant="primary"
          @click="$emit('open-quick')"
        />
        <NeuButton
          class="roster-action-btn roster-btn-import"
          icon="material-symbols:upload-file"
          label="导入酒馆卡"
          variant="normal"
          @click="$emit('open-import')"
        />
      </div>

      <div class="characters-grid">
        <div
          v-for="char in characters"
          :key="char.id"
          :class="['char-card', 'neu-flat-sm', 'neu-hover', { 'is-selected': char.id === currentCharacterId }]"
          @click="$emit('select-character', char.id)"
        >
          <div class="char-avatar-box neu-inset-sm">
            <img
              v-if="getCharacterAvatarUrl(char)"
              :src="getCharacterAvatarUrl(char)!"
              :alt="char.name"
              class="char-avatar-img"
              @error="handleAvatarError(char)"
            />
            <Icon v-else icon="material-symbols:account-circle" class="char-avatar-icon" />
          </div>
          <div class="char-info">
            <div class="char-name-row">
              <span class="char-name">{{ char.name }}</span>
              <span v-if="char.id === currentCharacterId" class="active-badge neu-flat-sm">
                当前
              </span>
            </div>
            <span class="char-title">{{ char.title || '漫游者' }}</span>
          </div>

          <!-- 删除角色按钮 -->
          <button
            class="char-delete-btn"
            title="彻底删除此角色及全部推演历史"
            @click.stop="$emit('delete-character', char)"
          >
            <Icon icon="material-symbols:delete" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Icon } from '@iconify/vue'
import NeuButton from './NeuButton.vue'
import type { StoryLogView } from '../api/client'

const props = withDefaults(
  defineProps<{
    characters: any[]
    currentCharacterId: string
    timeline: StoryLogView[]
    initialTab?: 'timeline' | 'roster'
  }>(),
  {
    initialTab: 'timeline',
  }
)

defineEmits<{
  (e: 'select-character', id: string): void
  (e: 'delete-character', char: any): void
  (e: 'select-tick', logId: number): void
  (e: 'open-quick'): void
  (e: 'open-import'): void
}>()

const activeTab = ref<'timeline' | 'roster'>(props.initialTab)

// 头像三级优雅降级策略：自定义 URL -> DiceBear Slice 风格接口 -> SVG 保底
const failedCustomAvatars = ref<Record<string, boolean>>({})
const failedDicebearAvatars = ref<Record<string, boolean>>({})

function getDicebearUrl(name?: string): string {
  const cleanName = (name || '').trim().replace(/^来自\s+/, '') || 'char'
  const seed = encodeURIComponent(cleanName)
  // 符合项目新拟态冷灰低饱和调性的 DiceBear Slice 头像
  return `https://api.dicebear.com/10.x/slice/svg?seed=${seed}&backgroundColor=e6e9ef,d9dde5,f0f3f8&bodyColor=4a4a50,63636a,37373c,757580,5e72e4`
}

function getCharacterAvatarUrl(char: any): string | null {
  const charKey = String(char?.id ?? char?.name ?? 'unknown')
  // 1. 若有自定义 avatar_url 且未加载失败，优先使用
  if (char?.avatar_url && !failedCustomAvatars.value[charKey]) {
    return char.avatar_url
  }
  // 2. 缺省或自定义头像加载失败时，尝试 DiceBear Slice 头像
  if (!failedDicebearAvatars.value[charKey]) {
    return getDicebearUrl(char?.name)
  }
  // 3. 最终保底返回 null，触发 template 中 SVG 图标渲染
  return null
}

function handleAvatarError(char: any) {
  const charKey = String(char?.id ?? char?.name ?? 'unknown')
  // 若自定义头像存在但失败，先标记自定义失败（触发切换至 DiceBear）
  if (char?.avatar_url && !failedCustomAvatars.value[charKey]) {
    failedCustomAvatars.value = { ...failedCustomAvatars.value, [charKey]: true }
    return
  }
  // 若 DiceBear 头像也失败（或无自定义头像且 DiceBear 加载失败），标记 DiceBear 失败（切入 SVG 保底）
  failedDicebearAvatars.value = { ...failedDicebearAvatars.value, [charKey]: true }
}

defineExpose({
  setTab: (tab: 'timeline' | 'roster') => {
    activeTab.value = tab
  },
})
</script>

<style scoped>
.character-drawer {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

/* 头部标签页内凹分段槽 */
.drawer-tabs {
  display: flex;
  padding: 0.3rem;
  gap: 0.35rem;
  background: var(--neu-surface);
  box-shadow: var(--shadow-inset-sm);
  border-radius: 12px;
}

.tab-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.45rem;
  padding: 0.5rem 0.65rem;
  border: none;
  background: transparent;
  color: var(--neu-text-secondary);
  font-size: 0.8rem;
  font-weight: 600;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.tab-btn:hover:not(.is-active) {
  color: var(--neu-text-primary);
}

.tab-btn.is-active {
  background: var(--neu-surface);
  color: var(--neu-accent);
  box-shadow: var(--shadow-flat-sm);
}

.tab-icon {
  font-size: 1.05rem;
}

/* 编年轴视图 */
.timeline-view, .roster-view {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.view-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 0 0.25rem;
}

.view-title {
  font-size: 0.875rem;
  font-weight: 700;
  color: var(--neu-text-primary);
}

.view-sub {
  font-size: 0.725rem;
  color: var(--neu-text-muted);
}

.timeline-list {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  max-height: calc(100vh - 220px);
  overflow-y: auto;
  padding-right: 0.25rem;
}

.timeline-index-item {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  padding: 0.65rem 0.85rem;
  cursor: pointer;
  border-left: 3px solid var(--neu-accent);
}

.index-top {
  display: flex;
  justify-content: space-between;
  font-size: 0.8rem;
}

.index-tick {
  font-weight: 700;
  color: var(--neu-accent);
}

.index-time {
  color: var(--neu-text-secondary);
}

.index-loc {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.725rem;
  color: var(--neu-text-secondary);
}

.mini-icon {
  font-size: 0.85rem;
}

.index-beat {
  font-size: 0.75rem;
  color: var(--neu-text-muted);
  line-height: 1.35;
}

/* 角色名录操作栏与按钮体系 */
.roster-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.6rem;
  width: 100%;
  box-sizing: border-box;
}

.roster-actions :deep(.neu-btn),
.roster-action-btn {
  width: 100%;
  height: 38px;
  padding: 0 0.5rem;
  font-size: 0.8rem;
  font-weight: 600;
  border-radius: 10px;
  gap: 0.35rem;
  box-sizing: border-box;
}

/* 快速新建：主操作微光与微渐变 */
.roster-actions :deep(.roster-btn-quick) {
  background: linear-gradient(135deg, rgba(94, 114, 228, 0.08) 0%, rgba(94, 114, 228, 0.02) 100%), var(--neu-surface);
  border: 1px solid rgba(94, 114, 228, 0.22);
  color: var(--neu-accent);
}

.roster-actions :deep(.roster-btn-quick:hover:not(.is-disabled)) {
  border-color: rgba(94, 114, 228, 0.45);
  box-shadow: var(--shadow-hover);
}

/* 导入酒馆卡：次操作高亮边框与干净触感 */
.roster-actions :deep(.roster-btn-import) {
  background: var(--neu-surface);
  border: 1px solid rgba(255, 255, 255, 0.65);
  color: var(--neu-text-primary);
}

.roster-actions :deep(.roster-btn-import:hover:not(.is-disabled)) {
  color: var(--neu-accent);
  box-shadow: var(--shadow-hover);
}

.characters-grid {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  max-height: calc(100vh - 240px);
  overflow-y: auto;
  padding-right: 0.25rem;
}

.char-card {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.65rem 0.85rem;
  cursor: pointer;
  border: 1px solid transparent;
}

.char-card.is-selected {
  border-color: var(--neu-accent);
  box-shadow: var(--shadow-inset-sm);
}

.char-avatar-box {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  color: var(--neu-accent);
  flex-shrink: 0;
  background: var(--neu-surface);
}

.char-avatar-img {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
}

.char-avatar-icon {
  font-size: 2.2rem;
  color: var(--neu-accent);
}

.char-info {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  flex: 1;
}

.char-name-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.char-name {
  font-size: 0.875rem;
  font-weight: 700;
  color: var(--neu-text-primary);
}

.active-badge {
  font-size: 0.675rem;
  padding: 0.1rem 0.4rem;
  color: var(--neu-accent);
  font-weight: 600;
}

.char-title {
  font-size: 0.75rem;
  color: var(--neu-text-secondary);
}

.char-delete-btn {
  background: none;
  border: none;
  color: var(--neu-text-muted);
  font-size: 1.15rem;
  padding: 0.35rem;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0.5;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  flex-shrink: 0;
}

.char-card:hover .char-delete-btn {
  opacity: 0.9;
}

.char-delete-btn:hover {
  opacity: 1;
  color: var(--neu-danger);
  background: rgba(239, 68, 68, 0.12);
  transform: scale(1.1);
}

.empty-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.4rem;
  padding: 2rem;
  color: var(--neu-text-muted);
  font-size: 0.8rem;
}

.empty-icon {
  font-size: 2rem;
}
</style>
