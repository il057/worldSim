<template>
  <div class="living-state-sheet">
    <!-- 角色基础卡片 -->
    <NeuCard class="profile-card" variant="flat">
      <div class="profile-header">
        <div class="avatar-box neu-inset-sm">
          <img
            v-if="character?.avatar_url"
            :src="character.avatar_url"
            class="avatar-img"
            alt="avatar"
          />
          <Icon v-else icon="material-symbols:account-circle" class="avatar-icon" />
        </div>
        <div class="profile-title-group">
          <h2 class="char-name">{{ character?.name || '未选定角色' }}</h2>
          <span class="char-title neu-flat-sm">
            <Icon icon="material-symbols:badge" class="mini-icon" />
            {{ character?.title || '漫游者' }}
          </span>
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
        <Icon icon="material-symbols:vital-signs" class="title-icon" />
        <span>生理与即时节律</span>
      </div>

      <div class="meters-container">
        <!-- 健康值 -->
        <NeuMeter
          label="健康值"
          :value="state?.health ?? 100"
          color="var(--neu-success)"
          icon="material-symbols:favorite"
          :sub-text="getHealthStatus(state?.health ?? 100)"
        />

        <!-- 精力值 -->
        <NeuMeter
          label="精力值"
          :value="state?.stamina ?? 90"
          :color="getStaminaColor(state?.stamina ?? 90)"
          icon="material-symbols:bolt"
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
            作息倾向: {{ character?.circadian_profile?.chronotype }} ({{ character?.circadian_profile?.typical_rest_window }})
          </span>
        </div>
      </div>

      <!-- 心理情绪 -->
      <div class="mood-box">
        <span class="mood-label">即时心理:</span>
        <span class="mood-value">{{ state?.psychological_state || '平静' }}</span>
      </div>
    </NeuCard>

    <!-- 随身背包 -->
    <NeuCard class="inventory-card" variant="flat">
      <div class="section-title">
        <Icon icon="material-symbols:inventory-2" class="title-icon" />
        <span>随身背包物品 ({{ inventory.length }})</span>
      </div>

      <div v-if="inventory.length" class="inventory-chips">
        <span
          v-for="(item, idx) in inventory"
          :key="idx"
          class="item-chip neu-flat-sm"
        >
          <Icon icon="material-symbols:circle" class="chip-dot" />
          {{ item }}
        </span>
      </div>
      <div v-else class="empty-hint">背包空无一物</div>
    </NeuCard>

    <!-- 当前目标栈 -->
    <NeuCard class="goals-card" variant="flat">
      <div class="section-title">
        <Icon icon="material-symbols:flag" class="title-icon" />
        <span>当前行动目标</span>
      </div>

      <div v-if="activeGoals.length" class="goals-list">
        <div
          v-for="(goal, idx) in activeGoals"
          :key="idx"
          class="goal-item neu-inset-sm"
        >
          <span class="goal-num">{{ idx + 1 }}</span>
          <span class="goal-desc">{{ goal }}</span>
        </div>
      </div>
      <div v-else class="empty-hint">暂无紧迫短期目标</div>
    </NeuCard>

    <!-- 降维 NPC 关系网 -->
    <NeuCard v-if="relationships.length" class="relationships-card" variant="flat">
      <div class="section-title">
        <Icon icon="material-symbols:groups" class="title-icon" />
        <span>社交关系 ({{ relationships.length }})</span>
      </div>
      <div class="npc-list">
        <div
          v-for="npc in relationships"
          :key="npc.id"
          class="npc-item neu-flat-sm"
        >
          <!-- 第一行：NPC 姓名与关系类型 -->
          <div class="npc-header">
            <span class="npc-name">{{ npc.npc_name }}</span>
            <span class="npc-relation-badge neu-flat-xs">{{ npc.relation_type }}</span>
          </div>

          <!-- 第二行：好感度以进度条显示（负数采用专属对立/戒备特化样式） -->
          <div class="npc-affinity-row" :class="{ 'is-negative': npc.affinity < 0 }">
            <div class="affinity-meta">
              <span class="affinity-title">
                <Icon
                  :icon="npc.affinity < 0 ? 'material-symbols:heart-broken' : 'material-symbols:favorite'"
                  class="affinity-icon"
                />
                {{ npc.affinity < 0 ? '戒备度' : '好感度' }}
              </span>
              <span class="affinity-val" :class="{ 'negative-val': npc.affinity < 0 }">
                {{ npc.affinity > 0 ? `+${npc.affinity}` : npc.affinity }} / 100
              </span>
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

          <!-- 第三行：客观人设背景与特殊样式的【对该角色的态度与羁绊】 -->
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
import { ref, computed } from 'vue'
import { Icon } from '@iconify/vue'
import NeuCard from './NeuCard.vue'
import NeuMeter from './NeuMeter.vue'
import type {
  CharacterDetailView,
  CharacterStateView,
} from '../api/client'

const props = defineProps<{
  character: CharacterDetailView | null
  state: CharacterStateView | null
}>()

const isPersonaExpanded = ref(false)
const isLongPersona = computed(() => {
  return (props.character?.persona_summary?.length || 0) > 180
})

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

.avatar-box {
  width: 52px;
  height: 52px;
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
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.char-name {
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--neu-text-primary);
}

.char-title {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.15rem 0.5rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--neu-text-secondary);
  align-self: flex-start;
}

.mini-icon {
  font-size: 0.85rem;
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
  gap: 0.4rem;
  font-size: 0.875rem;
  font-weight: 700;
  color: var(--neu-text-primary);
}

.title-icon {
  font-size: 1.1rem;
  color: var(--neu-accent);
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

.mood-box {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8rem;
}

.mood-label {
  color: var(--neu-text-secondary);
  font-weight: 500;
}

.mood-value {
  color: var(--neu-text-primary);
  font-weight: 600;
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
}

.chip-dot {
  font-size: 0.45rem;
  color: var(--neu-accent);
}

.goals-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.goal-item {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
}

.goal-num {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--neu-accent);
  margin-top: 0.1rem;
}

.goal-desc {
  font-size: 0.8rem;
  color: var(--neu-text-primary);
  line-height: 1.4;
}

.npc-list {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.npc-item {
  padding: 0.75rem 0.85rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  border-radius: var(--neu-radius-sm, 8px);
}

.npc-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
}

.npc-name {
  font-size: 0.875rem;
  font-weight: 700;
  color: var(--neu-text-primary);
}

.npc-relation-badge {
  font-size: 0.725rem;
  color: var(--neu-accent);
  font-weight: 600;
  padding: 0.15rem 0.5rem;
  border-radius: 9999px;
  background: var(--neu-base);
  box-shadow: 2px 2px 4px var(--neu-shadow-dark), -2px -2px 4px var(--neu-shadow-light);
  white-space: nowrap;
}

/* 第二行：好感度进度条 */
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

.affinity-val {
  font-weight: 600;
  color: var(--neu-text-primary);
  font-family: monospace;
}

.affinity-bar-track {
  height: 6px;
  border-radius: 9999px;
  background: var(--neu-base);
  overflow: hidden;
  box-shadow: inset 1px 1px 2px var(--neu-shadow-dark), inset -1px -1px 2px var(--neu-shadow-light);
}

.affinity-bar-fill {
  height: 100%;
  border-radius: 9999px;
  transition: width 0.3s ease, background-color 0.3s ease;
}

/* 负数好感（对立/戒备）特化警示样式 */
.npc-affinity-row.is-negative .affinity-title {
  color: #e11d48;
}

.npc-affinity-row.is-negative .affinity-icon {
  color: #e11d48;
}

.affinity-val.negative-val {
  color: #e11d48;
  font-weight: 700;
}

.affinity-bar-track.track-negative {
  background: rgba(225, 29, 72, 0.08);
  border: 1px dashed rgba(225, 29, 72, 0.35);
  box-shadow: inset 1px 1px 3px rgba(225, 29, 72, 0.2), inset -1px -1px 3px var(--neu-shadow-light);
}

.affinity-bar-fill.fill-negative {
  background: linear-gradient(90deg, #f43f5e, #be123c) !important;
  box-shadow: 0 0 6px rgba(225, 29, 72, 0.45);
}

/* 第三行：人设背景与羁绊特殊展示 */
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
  background: var(--neu-base);
  box-shadow: inset 2px 2px 4px var(--neu-shadow-dark), inset -2px -2px 4px var(--neu-shadow-light);
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
