<template>
  <div class="living-state-sheet">
    <!-- 角色基础卡片 -->
    <NeuCard class="profile-card" variant="flat">
      <div class="profile-header">
        <div class="avatar-box neu-inset-sm">
          <img
            v-if="resolvedAvatarUrl"
            :src="resolvedAvatarUrl"
            class="avatar-img"
            :alt="character?.name"
            @error="handleAvatarError"
          />
          <Icon v-else icon="material-symbols:account-circle" class="avatar-icon" />
        </div>
        <div class="profile-title-group">
          <h2 class="char-name">{{ character?.name || '未选定角色' }}</h2>
          <div class="char-titles-wrap">
            <span
              v-for="(t, idx) in splitTitles(character?.title)"
              :key="idx"
              class="char-title-chip neu-flat-xs"
            >
              <Icon v-if="idx === 0" icon="material-symbols:badge" class="mini-icon" />
              <span>{{ t }}</span>
            </span>
          </div>
        </div>
      </div>

      <div class="inner-drive-box neu-inset-sm">
        <div class="drive-label">
          <Icon icon="material-symbols:psychology" class="drive-icon" />
          <span>核心内在执念</span>
        </div>
        <p class="drive-text">{{ character?.inner_drive || '暂无终极动机记录' }}</p>
      </div>

      <div class="persona-box">
        <div class="persona-text" :class="{ 'is-collapsed': !isPersonaExpanded && isLongPersona }">
          <p>{{ character?.persona_summary }}</p>
        </div>
        <button
          v-if="isLongPersona"
          type="button"
          class="expand-persona-btn"
          @click="isPersonaExpanded = !isPersonaExpanded"
        >
          <Icon :icon="isPersonaExpanded ? 'material-symbols:expand-less' : 'material-symbols:expand-more'" class="btn-icon" />
          <span>{{ isPersonaExpanded ? '收起完整设定' : '展开查看完整人设' }}</span>
        </button>
      </div>
    </NeuCard>

    <!-- 生理指标与作息看板 -->
    <NeuCard class="vitals-card" variant="flat">
      <div class="section-title">
        <div class="title-left">
          <Icon icon="material-symbols:vital-signs" class="title-icon" />
          <span>生理与即时节律</span>
        </div>
        <span
          v-if="healthDelta !== 0 || staminaDelta !== 0"
          class="recent-change-indicator neu-flat-xs"
        >
          最新变动已同步
        </span>
      </div>

      <div class="meters-container">
        <!-- 健康值 -->
        <NeuMeter
          label="健康值"
          :value="state?.health ?? 100"
          color="var(--neu-success)"
          icon="material-symbols:favorite"
          :delta="healthDelta"
          :sub-text="getHealthStatus(state?.health ?? 100)"
        />

        <!-- 精力值 -->
        <NeuMeter
          label="精力值"
          :value="state?.stamina ?? 90"
          :color="getStaminaColor(state?.stamina ?? 90)"
          icon="material-symbols:bolt"
          :delta="staminaDelta"
          :sub-text="getStaminaStatus(state?.stamina ?? 90)"
        />
      </div>

      <!-- 当前睡眠与节律状态 -->
      <div class="sleep-status-pill neu-inset-sm">
        <Icon
          :icon="state?.is_sleeping ? 'material-symbols:bedtime' : 'material-symbols:timelapse'"
          class="sleep-icon"
          :class="{ 'sleeping-pulse': state?.is_sleeping }"
        />
        <div class="sleep-info">
          <span class="sleep-title">
            {{ state?.is_sleeping ? '深度就寝中 (精力加速恢复)' : '清醒行动中' }}
          </span>
          <span class="sleep-sub">
            作息倾向: {{ character?.circadian_profile?.chronotype || '均衡型' }} ({{ character?.circadian_profile?.typical_rest_window || '自然作息' }})
          </span>
        </div>
      </div>

      <!-- 即时心理与心境看板（新拟态内凹卡片，彻底避免长文本挤压折行） -->
      <div class="mood-card neu-inset-sm">
        <div class="mood-header">
          <Icon icon="material-symbols:psychology" class="mood-icon" />
          <span class="mood-label">即时心境与意绪</span>
        </div>
        <p class="mood-text">{{ state?.psychological_state || '内心波澜不惊，处于平静观察态。' }}</p>
      </div>
    </NeuCard>

    <!-- 随身背包 -->
    <NeuCard class="inventory-card" variant="flat">
      <div class="section-title">
        <div class="title-left">
          <Icon icon="material-symbols:inventory-2" class="title-icon" />
          <span>随身背包物品 ({{ inventory.length }})</span>
        </div>
        <span v-if="addedItems.length" class="recent-change-indicator text-success">
          +{{ addedItems.length }} 新获
        </span>
      </div>

      <div v-if="inventory.length" class="inventory-chips">
        <span
          v-for="(item, idx) in inventory"
          :key="idx"
          class="item-chip neu-flat-sm"
          :class="{ 'is-added-item': isItemAdded(item) }"
        >
          <Icon
            :icon="isItemAdded(item) ? 'material-symbols:add-circle' : 'material-symbols:circle'"
            class="chip-dot"
            :class="{ 'added-dot': isItemAdded(item) }"
          />
          <span class="item-text">{{ item }}</span>
        </span>
      </div>
      <div v-else class="empty-hint">背包空无一物</div>

      <!-- 本次消耗 / 失去的物品展示（新拟态内凹托盘） -->
      <div v-if="removedItems.length" class="inventory-removed-section neu-inset-sm">
        <div class="removed-header">
          <Icon icon="material-symbols:output" class="removed-icon" />
          <span>本次失去 / 消耗 ({{ removedItems.length }})</span>
        </div>
        <div class="removed-chips">
          <span
            v-for="(item, idx) in removedItems"
            :key="'rem-' + idx"
            class="item-chip removed-chip"
          >
            <Icon icon="material-symbols:remove-circle-outline" class="removed-dot" />
            <span class="removed-text">{{ item }}</span>
          </span>
        </div>
      </div>
    </NeuCard>

    <!-- 当前行动目标 -->
    <NeuCard class="goals-card" variant="flat">
      <div class="section-title">
        <div class="title-left">
          <Icon icon="material-symbols:flag" class="title-icon" />
          <span>当前行动目标</span>
        </div>
        <div class="title-tags">
          <span v-if="completedGoals.length" class="recent-change-indicator text-success">
            {{ completedGoals.length }} 达成
          </span>
          <span v-if="addedGoals.length" class="recent-change-indicator text-accent">
            {{ addedGoals.length }} 新增
          </span>
        </div>
      </div>

      <div v-if="completedGoals.length || activeGoals.length" class="goals-list">
        <!-- 1. 本次达成目标（删除线 + 勾选 + 专属新拟态内凹槽位） -->
        <div
          v-for="(goal, idx) in completedGoals"
          :key="'comp-' + idx"
          class="goal-item is-completed neu-inset-sm"
        >
          <div class="goal-state-icon">
            <Icon icon="material-symbols:check-circle" class="completed-icon" />
          </div>
          <div class="goal-body">
            <span class="goal-desc goal-completed-text">{{ goal }}</span>
            <span class="goal-badge completed-badge">已达成</span>
          </div>
        </div>

        <!-- 2. 当前进行中目标（若为本次新增则微凸浮动 + 柔和环境光） -->
        <div
          v-for="(goal, idx) in activeGoals"
          :key="'act-' + idx"
          class="goal-item neu-inset-sm"
          :class="{ 'is-new-goal': isGoalAdded(goal) }"
        >
          <div class="goal-state-icon">
            <Icon
              v-if="isGoalAdded(goal)"
              icon="material-symbols:auto-awesome"
              class="new-goal-icon"
            />
            <span v-else class="goal-num">{{ idx + 1 }}</span>
          </div>
          <div class="goal-body">
            <span class="goal-desc">{{ goal }}</span>
            <span v-if="isGoalAdded(goal)" class="goal-badge new-goal-badge">新目标</span>
          </div>
        </div>
      </div>
      <div v-else class="empty-hint">暂无紧迫短期目标</div>
    </NeuCard>

    <!-- 降维 NPC 关系网 -->
    <NeuCard v-if="relationships.length" class="relationships-card" variant="flat">
      <div class="section-title">
        <div class="title-left">
          <Icon icon="material-symbols:groups" class="title-icon" />
          <span>社交关系 ({{ relationships.length }})</span>
        </div>
      </div>
      <div class="npc-list">
        <div
          v-for="npc in relationships"
          :key="npc.id"
          class="npc-item neu-flat-sm"
          :class="{
            'is-updated-card': isNpcUpdatedInLatest(npc.npc_name),
            'is-new-card': isNpcNewInLatest(npc.npc_name)
          }"
        >
          <!-- 第一行：NPC 姓名与即时状态徽章 -->
          <div class="npc-header-row">
            <div class="npc-name-group">
              <span class="npc-name">{{ npc.npc_name }}</span>
              <span v-if="isNpcNewInLatest(npc.npc_name)" class="npc-state-tag tag-new">
                <Icon icon="material-symbols:person-add" class="state-icon" />
                新结识
              </span>
              <span v-else-if="isNpcUpdatedInLatest(npc.npc_name)" class="npc-state-tag tag-updated">
                <Icon icon="material-symbols:forum" class="state-icon" />
                本次交集
              </span>
            </div>

            <span v-if="npc.is_present" class="presence-tag">
              <Icon icon="material-symbols:location-on" class="presence-icon" />
              在场
            </span>
          </div>

          <!-- 第二行：NPC 身份与定位标签区（多标签流式弹性排列，绝不挤压名字、绝不溢出） -->
          <div v-if="npc.relation_type" class="npc-tags-row">
            <span
              v-for="(tag, tIdx) in splitTitles(npc.relation_type)"
              :key="tIdx"
              class="npc-relation-badge neu-flat-xs"
            >
              {{ tag }}
            </span>
          </div>

          <!-- 第三行：好感度/戒备度以进度条显示（负数采用专属对立/戒备特化样式；正数不显示 + 号） -->
          <div class="npc-affinity-row" :class="{ 'is-negative': npc.affinity < 0 }">
            <div class="affinity-meta">
              <span class="affinity-title">
                <Icon
                  :icon="npc.affinity < 0 ? 'material-symbols:heart-broken' : 'material-symbols:favorite'"
                  class="affinity-icon"
                />
                {{ npc.affinity < 0 ? '戒备度' : '好感度' }}
              </span>
              <div class="affinity-val-group">
                <!-- 本次好感变动增减徽章 -->
                <span
                  v-if="getNpcAffinityDelta(npc.npc_name) !== 0"
                  class="affinity-delta-pill"
                  :class="getNpcAffinityDelta(npc.npc_name) > 0 ? 'delta-positive' : 'delta-negative'"
                >
                  <Icon
                    :icon="getNpcAffinityDelta(npc.npc_name) > 0 ? 'material-symbols:arrow-drop-up' : 'material-symbols:arrow-drop-down'"
                    class="delta-arrow"
                  />
                  {{ getNpcAffinityDelta(npc.npc_name) > 0 ? `+${getNpcAffinityDelta(npc.npc_name)}` : getNpcAffinityDelta(npc.npc_name) }}
                </span>
                <!-- 好感度绝对值：正数不显示 + -->
                <span class="affinity-val" :class="{ 'negative-val': npc.affinity < 0 }">
                  {{ npc.affinity }} / 100
                </span>
              </div>
            </div>
            <div class="affinity-bar-track neu-inset-xs" :class="{ 'track-negative': npc.affinity < 0 }">
              <div
                class="affinity-bar-fill"
                :class="{ 'fill-negative': npc.affinity < 0 }"
                :style="{
                  width: `${Math.min(100, Math.max(0, Math.abs(npc.affinity)))}%`,
                  backgroundColor: getAffinityColor(npc.affinity)
                }"
              ></div>
            </div>
          </div>

          <!-- 第四行：客观人设背景与特殊样式的【对该角色的态度与羁绊】 -->
          <div class="npc-content-body">
            <p v-if="parseNpcSummary(npc.summary).background" class="npc-background">
              {{ parseNpcSummary(npc.summary).background }}
            </p>
            <div
              v-if="parseNpcSummary(npc.summary).attitude"
              class="npc-attitude-card neu-inset-xs"
            >
              <div class="attitude-header">
                <Icon icon="material-symbols:handshake" class="attitude-icon" />
                <span class="attitude-title">对该角色的态度与羁绊</span>
              </div>
              <p class="attitude-text">
                {{ parseNpcSummary(npc.summary).attitude }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </NeuCard>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Icon } from '@iconify/vue'
import NeuCard from './NeuCard.vue'
import NeuMeter from './NeuMeter.vue'
import { useWorldStore } from '../stores/world'
import { useTheme } from '../composables/useTheme'
import type {
  CharacterDetailView,
  CharacterStateView,
} from '../api/client'

const props = defineProps<{
  character: CharacterDetailView | null
  state: CharacterStateView | null
}>()

const worldStore = useWorldStore()
const { getDicebearAvatarUrl } = useTheme()

// 头像三级优雅降级策略：自定义 URL -> DiceBear Slice 风格接口 -> SVG 保底
const failedCustomAvatar = ref(false)
const failedDicebearAvatar = ref(false)

watch(
  () => props.character?.id,
  () => {
    failedCustomAvatar.value = false
    failedDicebearAvatar.value = false
  }
)

const resolvedAvatarUrl = computed(() => {
  if (props.character?.avatar_url && !failedCustomAvatar.value) {
    return props.character.avatar_url
  }
  if (!failedDicebearAvatar.value) {
    const cleanName = (props.character?.name || '').trim().replace(/^来自\s+/, '') || 'char'
    return getDicebearAvatarUrl(cleanName)
  }
  return ''
})

function handleAvatarError() {
  if (props.character?.avatar_url && !failedCustomAvatar.value) {
    failedCustomAvatar.value = true
    return
  }
  failedDicebearAvatar.value = true
}

const isPersonaExpanded = ref(false)
const isLongPersona = computed(() => {
  return (props.character?.persona_summary?.length || 0) > 180
})

// 分解身份/定位头衔，防止超长连缀字符串撑破布局与挤压头像
function splitTitles(title: string | undefined): string[] {
  if (!title) return ['漫游者']
  const parts = title
    .split(/[/、|，,\n]+/)
    .map((s) => s.trim())
    .filter(Boolean)
  return parts.length ? parts : [title.trim()]
}

// 获取最新一条推演日志及其因果裁决快照（Delta Snapshot）
const latestLog = computed(() => {
  if (worldStore.streamingLog?.delta_snapshot) {
    return worldStore.streamingLog
  }
  if (worldStore.timeline.length > 0) {
    return worldStore.timeline[worldStore.timeline.length - 1]
  }
  return null
})

const latestDelta = computed(() => latestLog.value?.delta_snapshot || null)

// 生理增量
const healthDelta = computed(() => latestDelta.value?.health_delta ?? 0)
const staminaDelta = computed(() => latestDelta.value?.stamina_delta ?? 0)

// 行囊增损
const addedItems = computed(() => latestDelta.value?.inventory_delta?.added || [])
const removedItems = computed(() => latestDelta.value?.inventory_delta?.removed || [])
const isItemAdded = (item: string) => addedItems.value.includes(item)

// 目标增损与状态
const completedGoals = computed(() => latestDelta.value?.goal_delta?.completed || [])
const addedGoals = computed(() => latestDelta.value?.goal_delta?.added || [])
const isGoalAdded = (goal: string) => addedGoals.value.includes(goal)

// 人际关系动态
const newNpcs = computed(() => latestDelta.value?.relationship_delta?.new_npcs || [])
const updatedNpcs = computed(() => latestDelta.value?.relationship_delta?.updated_npcs || [])

function isNpcNewInLatest(npcName: string): boolean {
  return newNpcs.value.some((n) => n.npc_name === npcName)
}

function isNpcUpdatedInLatest(npcName: string): boolean {
  return updatedNpcs.value.some((u) => u.npc_name === npcName)
}

function getNpcAffinityDelta(npcName: string): number {
  // 1. 优先使用 worldStore 运行时记录的精准差值
  if (worldStore.lastAffinityDeltas[npcName] !== undefined) {
    return worldStore.lastAffinityDeltas[npcName]
  }
  // 2. 页面初次加载或刷新时，尝试从 timeline 历史日志推导
  const updated = updatedNpcs.value.find((u) => u.npc_name === npcName)
  if (!updated) return 0
  if (worldStore.timeline.length >= 2) {
    for (let i = worldStore.timeline.length - 2; i >= 0; i--) {
      const prevLog = worldStore.timeline[i]
      const prevItem =
        prevLog.delta_snapshot?.relationship_delta?.updated_npcs?.find((u) => u.npc_name === npcName) ||
        prevLog.delta_snapshot?.relationship_delta?.new_npcs?.find((n) => n.npc_name === npcName)
      if (prevItem) {
        return updated.affinity - prevItem.affinity
      }
    }
  }
  return 0
}

function parseNpcSummary(summary: string | undefined): { background: string; attitude: string } {
  if (!summary) return { background: '', attitude: '' }
  const raw = summary.trim()
  const match = raw.split(/【对该角色的态度与羁绊】[：:]?\s*/)
  if (match.length >= 2) {
    return {
      background: match[0].trim(),
      attitude: match.slice(1).join('【对该角色的态度与羁绊】：').trim(),
    }
  }
  const matchAlt = raw.split(/【态度与羁绊】[：:]?\s*/)
  if (matchAlt.length >= 2) {
    return {
      background: matchAlt[0].trim(),
      attitude: matchAlt.slice(1).join('【态度与羁绊】：').trim(),
    }
  }
  return {
    background: raw,
    attitude: '',
  }
}

function getAffinityColor(affinity: number): string {
  if (affinity < 0) {
    if (affinity <= -60) return '#be123c' // 极度对立/敌视
    return '#e11d48' // 戒备/厌恶
  }
  if (affinity >= 70) return 'var(--neu-accent)'
  if (affinity >= 50) return 'var(--neu-success)'
  if (affinity >= 30) return 'var(--neu-warning)'
  return '#94a3b8' // 平平淡淡 / 中立
}

const inventory = computed(() => props.state?.inventory || [])
const activeGoals = computed(() => props.state?.active_goals || [])
const relationships = computed(() => props.character?.relationships || [])

const getHealthStatus = (val: number) => {
  if (val > 80) return '健全'
  if (val > 50) return '擦伤轻度受创'
  return '危重衰竭'
}

const getStaminaStatus = (val: number) => {
  if (val > 70) return '充沛'
  if (val > 30) return '轻微疲乏'
  if (val > 15) return '极度疲惫'
  return '濒临昏厥'
}

const getStaminaColor = (val: number) => {
  if (val > 60) return 'var(--neu-accent)'
  if (val > 25) return 'var(--neu-warning)'
  return 'var(--neu-danger)'
}
</script>

<style scoped>
.living-state-sheet {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.profile-card {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 0.85rem;
}

/* 坚固的正圆形头像，flex-shrink 设为 0，绝对不被长标题挤压变形 */
.avatar-box {
  width: 52px;
  height: 52px;
  min-width: 52px;
  min-height: 52px;
  flex-shrink: 0;
  aspect-ratio: 1 / 1;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--neu-accent);
  overflow: hidden;
}

.avatar-img {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
}

.avatar-icon {
  font-size: 2.25rem;
}

.profile-title-group {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.char-name {
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--neu-text-primary);
  line-height: 1.3;
  word-break: break-word;
}

/* 主角身份多标签流式排列，弹性自适应包裹 */
.char-titles-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  align-items: center;
}

.char-title-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.15rem 0.5rem;
  font-size: 0.725rem;
  font-weight: 600;
  color: var(--neu-text-secondary);
  border-radius: 6px;
  background: var(--neu-surface);
  box-shadow: 2px 2px 4px var(--neu-dark), -2px -2px 4px var(--neu-light);
  line-height: 1.35;
  word-break: break-word;
  max-width: 100%;
}

.mini-icon {
  font-size: 0.85rem;
  color: var(--neu-accent);
}

.inner-drive-box {
  padding: 0.65rem 0.85rem;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.drive-label {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--neu-accent);
}

.drive-icon {
  font-size: 0.95rem;
}

.drive-text {
  font-size: 0.825rem;
  color: var(--neu-text-primary);
  line-height: 1.45;
}

.persona-box {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.persona-text {
  font-size: 0.8rem;
  color: var(--neu-text-secondary);
  line-height: 1.55;
  white-space: pre-line;
  word-break: break-word;
  transition: all 0.25s ease;
}

.persona-text.is-collapsed {
  max-height: 120px;
  overflow: hidden;
  position: relative;
  mask-image: linear-gradient(to bottom, rgba(0, 0, 0, 1) 60%, rgba(0, 0, 0, 0) 100%);
  -webkit-mask-image: linear-gradient(to bottom, rgba(0, 0, 0, 1) 60%, rgba(0, 0, 0, 0) 100%);
}

.expand-persona-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.25rem;
  background: none;
  border: none;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--neu-accent);
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  align-self: flex-start;
  border-radius: 6px;
  transition: all 0.2s;
}

.expand-persona-btn:hover {
  background: rgba(79, 70, 229, 0.08);
}

.expand-persona-btn .btn-icon {
  font-size: 0.95rem;
}

.vitals-card {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.4rem;
  font-size: 0.875rem;
  font-weight: 700;
  color: var(--neu-text-primary);
}

.title-left {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.title-icon {
  font-size: 1.1rem;
  color: var(--neu-accent);
}

.title-tags {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

/* 新拟态微内凹状态指示胶囊 */
.recent-change-indicator {
  font-size: 0.68rem;
  font-weight: 600;
  padding: 0.12rem 0.45rem;
  border-radius: 9999px;
  background: var(--neu-surface);
  box-shadow: inset 1px 1px 3px var(--neu-dark), inset -1px -1px 3px var(--neu-light);
  line-height: 1.25;
  color: var(--neu-accent);
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}

.recent-change-indicator.text-success {
  color: var(--neu-success);
  box-shadow: inset 1px 1px 3px var(--neu-dark), inset -1px -1px 3px var(--neu-light), inset 0 0 3px rgba(56, 161, 105, 0.18);
}

.recent-change-indicator.text-accent {
  color: var(--neu-accent);
  box-shadow: inset 1px 1px 3px var(--neu-dark), inset -1px -1px 3px var(--neu-light), inset 0 0 3px rgba(94, 114, 228, 0.18);
}

.meters-container {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.sleep-status-pill {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.65rem 0.85rem;
}

.sleep-icon {
  font-size: 1.35rem;
  color: var(--neu-accent);
}

.sleeping-pulse {
  color: #8b5cf6;
  animation: pulse-glow 2s infinite ease-in-out;
}

@keyframes pulse-glow {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}

.sleep-info {
  display: flex;
  flex-direction: column;
}

.sleep-title {
  font-size: 0.825rem;
  font-weight: 600;
  color: var(--neu-text-primary);
}

.sleep-sub {
  font-size: 0.725rem;
  color: var(--neu-text-muted);
}

/* 即时心理与心境看板：微内凹槽位结构，优雅容纳长文本段落 */
.mood-card {
  padding: 0.65rem 0.85rem;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.mood-header {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--neu-accent);
}

.mood-icon {
  font-size: 0.95rem;
}

.mood-label {
  white-space: nowrap;
}

.mood-text {
  font-size: 0.825rem;
  color: var(--neu-text-primary);
  line-height: 1.5;
  word-break: break-word;
  white-space: pre-wrap;
  margin: 0;
}

.inventory-card, .goals-card, .relationships-card {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.inventory-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.item-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.3rem 0.65rem;
  font-size: 0.8rem;
  color: var(--neu-text-primary);
  transition: all 0.25s ease;
}

/* 本次新获得物品高亮特效：立体微凸 + 绿意柔光 */
.item-chip.is-added-item {
  box-shadow: 2px 2px 5px var(--neu-dark), -2px -2px 5px var(--neu-light), inset 0 0 0 1px rgba(56, 161, 105, 0.4);
}

.chip-dot {
  font-size: 0.45rem;
  color: var(--neu-accent);
}

.chip-dot.added-dot {
  font-size: 0.85rem;
  color: var(--neu-success);
}

.item-added-badge {
  font-size: 0.65rem;
  font-weight: 700;
  padding: 0.08rem 0.35rem;
  border-radius: 9999px;
  background: var(--neu-surface);
  box-shadow: inset 1px 1px 2px var(--neu-dark), inset -1px -1px 2px var(--neu-light);
  color: var(--neu-success);
  margin-left: 0.2rem;
}

/* 失去 / 消耗的物品区块（新拟态内凹托盘与立体小卡片） */
.inventory-removed-section {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  padding: 0.6rem 0.75rem;
  border-radius: 8px;
}

.removed-header {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.725rem;
  font-weight: 600;
  color: var(--neu-danger);
}

.removed-icon {
  font-size: 0.85rem;
}

.removed-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.item-chip.removed-chip {
  padding: 0.25rem 0.55rem;
  font-size: 0.75rem;
  background: var(--neu-surface);
  border-radius: 6px;
  box-shadow: 2px 2px 4px var(--neu-dark), -2px -2px 4px var(--neu-light);
  opacity: 0.8;
}

.removed-dot {
  font-size: 0.85rem;
  color: var(--neu-danger);
}

.removed-text {
  text-decoration: line-through;
  color: var(--neu-text-muted);
}

.goals-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.goal-item {
  display: flex;
  align-items: flex-start;
  gap: 0.55rem;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  transition: all 0.25s ease;
}

.goal-state-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 0.05rem;
}

.goal-num {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--neu-accent);
}

.goal-body {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  flex: 1;
  min-width: 0;
}

.goal-desc {
  font-size: 0.8rem;
  color: var(--neu-text-primary);
  line-height: 1.4;
  word-break: break-word;
}

.goal-badge {
  font-size: 0.65rem;
  font-weight: 700;
  padding: 0.1rem 0.4rem;
  border-radius: 9999px;
  white-space: nowrap;
  flex-shrink: 0;
  background: var(--neu-surface);
  line-height: 1.25;
}

/* 目标达成：内凹槽位质感 + 柔和通透绿意 */
.goal-item.is-completed {
  opacity: 0.85;
}

.completed-icon {
  font-size: 1.15rem;
  color: var(--neu-success);
}

.goal-completed-text {
  text-decoration: line-through;
  color: var(--neu-text-muted);
}

.completed-badge {
  color: var(--neu-success);
  box-shadow: 1px 1px 3px var(--neu-dark), -1px -1px 3px var(--neu-light);
}

/* 目标新增：立体微凸浮动 + 柔和环境光 */
.goal-item.is-new-goal {
  box-shadow: 2px 2px 6px var(--neu-dark), -2px -2px 6px var(--neu-light), inset 0 0 0 1px rgba(94, 114, 228, 0.35);
}

.new-goal-icon {
  font-size: 1.15rem;
  color: var(--neu-accent);
  animation: pulse-glow 2.5s infinite;
}

.new-goal-badge {
  color: var(--neu-accent);
  box-shadow: inset 1px 1px 2px var(--neu-dark), inset -1px -1px 2px var(--neu-light);
}

.npc-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.npc-item {
  padding: 0.75rem 0.85rem;
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  border-radius: var(--neu-radius-sm, 8px);
  transition: all 0.25s ease;
}

.npc-item.is-updated-card {
  box-shadow: 3px 3px 8px var(--neu-dark), -3px -3px 8px var(--neu-light), inset 0 0 0 1px rgba(94, 114, 228, 0.3);
}

.npc-item.is-new-card {
  box-shadow: 3px 3px 8px var(--neu-dark), -3px -3px 8px var(--neu-light), inset 0 0 0 1px rgba(56, 161, 105, 0.35);
}

/* 第一行：名字与状态徽章 */
.npc-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
}

.npc-name-group {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  min-width: 0;
  flex: 1;
}

/* NPC 名字坚决不换行，不被身份挤压 */
.npc-name {
  font-size: 0.925rem;
  font-weight: 700;
  color: var(--neu-text-primary);
  white-space: nowrap;
  flex-shrink: 0;
}

.npc-state-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  font-size: 0.675rem;
  font-weight: 600;
  padding: 0.1rem 0.45rem;
  border-radius: 9999px;
  background: var(--neu-surface);
  line-height: 1.25;
  box-shadow: 1px 1px 3px var(--neu-dark), -1px -1px 3px var(--neu-light);
}

.npc-state-tag.tag-new {
  color: var(--neu-success);
  box-shadow: 1px 1px 3px var(--neu-dark), -1px -1px 3px var(--neu-light), inset 0 0 3px rgba(56, 161, 105, 0.18);
}

.npc-state-tag.tag-updated {
  color: var(--neu-accent);
  box-shadow: 1px 1px 3px var(--neu-dark), -1px -1px 3px var(--neu-light), inset 0 0 3px rgba(94, 114, 228, 0.18);
}

.state-icon {
  font-size: 0.75rem;
}

.presence-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.15rem;
  font-size: 0.675rem;
  font-weight: 600;
  color: var(--neu-success);
  padding: 0.1rem 0.45rem;
  border-radius: 9999px;
  background: var(--neu-surface);
  box-shadow: inset 1px 1px 2px var(--neu-dark), inset -1px -1px 2px var(--neu-light);
  flex-shrink: 0;
}

.presence-icon {
  font-size: 0.75rem;
}

/* 第二行：NPC 身份标签流式排布，支持自动换行，绝不溢出容器 */
.npc-tags-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  max-width: 100%;
}

.npc-relation-badge {
  font-size: 0.725rem;
  color: var(--neu-accent);
  font-weight: 600;
  padding: 0.15rem 0.5rem;
  border-radius: 9999px;
  background: var(--neu-surface);
  box-shadow: 2px 2px 4px var(--neu-dark), -2px -2px 4px var(--neu-light);
  line-height: 1.35;
  word-break: break-all;
  max-width: 100%;
}

/* 第三行：好感度进度条 */
.npc-affinity-row {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.affinity-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.725rem;
}

.affinity-title {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  color: var(--neu-text-secondary);
  font-weight: 500;
}

.affinity-icon {
  font-size: 0.85rem;
  color: var(--neu-accent);
}

.affinity-val-group {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

/* 本次好感变动增减徽章 */
.affinity-delta-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.1rem;
  font-size: 0.7rem;
  font-weight: 700;
  padding: 0.08rem 0.45rem;
  border-radius: 9999px;
  font-family: monospace;
  line-height: 1.2;
  background: var(--neu-surface);
  box-shadow: 1px 1px 3px var(--neu-dark), -1px -1px 3px var(--neu-light);
}

.affinity-delta-pill.delta-positive {
  color: var(--neu-success);
  box-shadow: 1px 1px 3px var(--neu-dark), -1px -1px 3px var(--neu-light), inset 0 0 3px rgba(56, 161, 105, 0.18);
}

.affinity-delta-pill.delta-negative {
  color: var(--neu-danger);
  box-shadow: 1px 1px 3px var(--neu-dark), -1px -1px 3px var(--neu-light), inset 0 0 3px rgba(229, 62, 62, 0.18);
}

.affinity-val {
  font-weight: 600;
  color: var(--neu-text-primary);
  font-family: monospace;
}

.affinity-bar-track {
  height: 6px;
  border-radius: 9999px;
  background: var(--neu-surface);
  overflow: hidden;
  box-shadow: inset 1px 1px 2px var(--neu-dark), inset -1px -1px 2px var(--neu-light);
}

.affinity-bar-fill {
  height: 100%;
  border-radius: 9999px;
  transition: width 0.3s ease, background-color 0.3s ease;
}

/* 负数好感（对立/戒备）特化警示样式 */
.npc-affinity-row.is-negative .affinity-title {
  color: var(--neu-danger);
}

.npc-affinity-row.is-negative .affinity-icon {
  color: var(--neu-danger);
}

.affinity-val.negative-val {
  color: var(--neu-danger);
  font-weight: 700;
}

.affinity-bar-track.track-negative {
  background: rgba(229, 62, 62, 0.08);
  box-shadow: inset 1px 1px 3px rgba(229, 62, 62, 0.2), inset -1px -1px 3px var(--neu-light);
}

.affinity-bar-fill.fill-negative {
  background: linear-gradient(90deg, #f43f5e, #be123c) !important;
  box-shadow: 0 0 6px rgba(229, 62, 62, 0.45);
}

/* 第四行：人设背景与羁绊特殊展示 */
.npc-content-body {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  margin-top: 0.15rem;
}

.npc-background {
  font-size: 0.775rem;
  color: var(--neu-text-secondary);
  line-height: 1.55;
  margin: 0;
  white-space: pre-wrap;
}

.npc-attitude-card {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  padding: 0.5rem 0.65rem;
  border-radius: 6px;
  background: var(--neu-surface);
  box-shadow: inset 2px 2px 4px var(--neu-dark), inset -2px -2px 4px var(--neu-light);
  border-left: 3px solid var(--neu-accent);
}

.attitude-header {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.725rem;
  font-weight: 600;
  color: var(--neu-accent);
}

.attitude-icon {
  font-size: 0.85rem;
}

.attitude-title {
  letter-spacing: 0.02em;
}

.attitude-text {
  font-size: 0.75rem;
  color: var(--neu-text-primary);
  line-height: 1.5;
  margin: 0;
  white-space: pre-wrap;
}

.empty-hint {
  font-size: 0.8rem;
  color: var(--neu-text-muted);
  font-style: italic;
  padding: 0.25rem 0;
}
</style>
