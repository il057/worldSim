<template>
  <NeuCard class="timeline-log-card" :class="{ 'is-streaming': isStreaming }" variant="flat">
    <!-- 切片头部元信息 -->
    <div class="log-header">
      <div class="header-left">
        <span class="tick-badge neu-flat-sm">
          <Icon icon="material-symbols:timelapse" class="badge-icon" />
          第 {{ log.tick_index }} 刻
        </span>
        <span class="time-text">
          <Icon icon="material-symbols:schedule" class="meta-icon" />
          {{ log.virtual_time }}
        </span>
      </div>
      <div class="header-right">
        <!-- 非流式推演生成中指示 -->
        <span v-if="isPendingNonStreaming" class="generating-pill neu-flat-xs">
          <Icon icon="material-symbols:progress-activity" class="spin-icon-generating" />
          <span>生成中</span>
        </span>
        <!-- 流式推演神性阶段指示 -->
        <span v-else-if="isStreaming" class="streaming-pill neu-flat-xs">
          <Icon :icon="stageIcon" class="streaming-icon pulse-anim" />
          <span>{{ stageBadgeText }}</span>
        </span>
        <span class="location-text">
          <Icon icon="material-symbols:location-on" class="meta-icon" />
          {{ log.location }}
        </span>
      </div>
    </div>

    <!-- 纯文学正文流 自然段落与拟真手机组件混排 -->
    <div class="log-prose prose-literary" :class="{ 'is-streaming-text': isStreaming }">
      <!-- 1. 非流式状态下的纯净等待指示 -->
      <div v-if="isPendingNonStreaming" class="generating-placeholder neu-inset-sm">
        <Icon icon="material-symbols:progress-activity" class="spin-icon-generating" />
        <span class="generating-text">生成中...</span>
      </div>

      <!-- 2. 流式传输状态下的推进与多阶段呈现 (Pass 1 -> Pass 2) -->
      <template v-else-if="isStreaming">
        <!-- 阶段 A: 尚未拿到衡律之神裁决结果时，显示衡律之神/变数之引推演中 -->
        <div v-if="!log.plot_beat && contentBlocks.length === 0" class="divine-calling-card neu-inset-sm">
          <div class="divine-header">
            <Icon
              :icon="worldStore.streamingStage === 'incident_conceive' ? 'material-symbols:bolt' : 'material-symbols:balance'"
              class="divine-icon pulse-anim"
            />
            <span class="divine-name">
              {{ worldStore.streamingStage === 'incident_conceive' ? '【变数之引】' : '【衡律之神】' }}
            </span>
          </div>
          <div class="divine-msg">
            {{ worldStore.tickStatusText || '正在权衡因果法则与身心节律...' }}
            <span class="typing-cursor"></span>
          </div>
        </div>

        <!-- 阶段 B: 衡律之神裁决完毕，先在楼层展现 Pass 1 衡律之神的裁决事实回复 -->
        <div v-if="log.plot_beat" class="divine-result-card neu-flat-sm">
          <div class="divine-result-header">
            <Icon icon="material-symbols:balance" class="divine-result-icon" />
            <span class="divine-result-tag">【衡律之神·因果裁决】</span>
          </div>
          <div class="divine-result-prose">
            {{ log.plot_beat }}
          </div>
        </div>

        <!-- 阶段 C: 紧接着展现 Pass 2 见证之神的回复 -->
        <!-- 若正文尚未吐出 chunk 时的准备中提示 -->
        <div v-if="log.plot_beat && contentBlocks.length === 0" class="divine-calling-card neu-inset-sm divine-witness-card">
          <div class="divine-header">
            <Icon icon="material-symbols:ink-pen" class="divine-icon pulse-anim" />
            <span class="divine-name">【见证之神】</span>
          </div>
          <div class="divine-msg">
            {{ worldStore.tickStatusText || '正在以有限视角编织时空切片...' }}
            <span class="typing-cursor"></span>
          </div>
        </div>

        <!-- 正文 chunk 吐出时：渲染纯文学段落与手机组件，最后一个段落带光标 -->
        <template v-for="(block, bIdx) in contentBlocks" :key="bIdx">
          <p v-if="block.type === 'text'" class="prose-paragraph">
            <span v-html="formatProseText(block.content)"></span><span v-if="bIdx === contentBlocks.length - 1" class="typing-cursor"></span>
          </p>
          <PhoneMomentsCard v-else-if="block.type === 'moments'" :posts="block.posts" />
          <PhoneForumCard v-else-if="block.type === 'forum'" :data="block.data" />
          <PhoneChatGroup v-else-if="block.type === 'chat'" :items="block.items" :protagonist-name="characterName" />
        </template>
      </template>

      <!-- 3. 常规已落库历史楼层渲染 -->
      <template v-else>
        <template v-for="(block, bIdx) in contentBlocks" :key="bIdx">
          <p v-if="block.type === 'text'" class="prose-paragraph">
            <span v-html="formatProseText(block.content)"></span>
          </p>
          <PhoneMomentsCard v-else-if="block.type === 'moments'" :posts="block.posts" />
          <PhoneForumCard v-else-if="block.type === 'forum'" :data="block.data" />
          <PhoneChatGroup v-else-if="block.type === 'chat'" :items="block.items" :protagonist-name="characterName" />
        </template>
      </template>
    </div>

    <!-- 【衡律之神】客观事实骨架与增量检视器折叠面板 (已定稿楼层随时供查看) -->
    <div v-if="!isStreaming && (log.delta_snapshot || log.plot_beat)" class="delta-inspector">
      <button class="toggle-btn" @click="isExpanded = !isExpanded">
        <Icon
          :icon="isExpanded ? 'material-symbols:expand-less' : 'material-symbols:expand-more'"
          class="toggle-icon"
        />
        <span>{{ isExpanded ? '收起因果裁决详情' : '【衡律之神】因果骨架与即时状态增量检视' }}</span>
      </button>

      <div v-if="isExpanded" class="inspector-content neu-inset-sm">
        <div class="fact-beat">
          <strong>【衡律之神】因果骨架 (Plot Beat):</strong>
          <p>{{ log.plot_beat }}</p>
        </div>

        <div v-if="log.delta_snapshot" class="delta-grid">
          <!-- 休眠与精力判定 -->
          <div class="delta-item">
            <span class="item-title">
              <Icon icon="material-symbols:bedtime" class="item-icon" />
              作息判定:
            </span>
            <span>
              {{ log.delta_snapshot.rest_decision.is_sleeping ? '深度就寝中' : '清醒' }}
              ({{ log.delta_snapshot.rest_decision.rest_reason }})
            </span>
          </div>

          <!-- 生理增量 -->
          <div class="delta-item">
            <span class="item-title">
              <Icon icon="material-symbols:vital-signs" class="item-icon" />
              生理变动:
            </span>
            <span>
              健康 {{ formatDelta(log.delta_snapshot.health_delta) }} | 精力 {{ formatDelta(log.delta_snapshot.stamina_delta) }}
            </span>
          </div>

          <!-- 环境感官线索 -->
          <div v-if="log.delta_snapshot.sensory_cues?.length" class="delta-item sensory-item">
            <span class="item-title">
              <Icon icon="material-symbols:visibility" class="item-icon" />
              感官线索:
            </span>
            <div class="sensory-tags">
              <span v-for="(cue, idx) in log.delta_snapshot.sensory_cues" :key="idx" class="sensory-tag neu-flat-sm">
                {{ cue }}
              </span>
            </div>
          </div>

          <!-- 物品增损 -->
          <div v-if="hasInventoryDelta" class="delta-item">
            <span class="item-title">
              <Icon icon="material-symbols:inventory-2" class="item-icon" />
              行囊增损:
            </span>
            <span>
              <template v-if="log.delta_snapshot.inventory_delta.added?.length">
                获得: [{{ log.delta_snapshot.inventory_delta.added.join(', ') }}]
              </template>
              <template v-if="log.delta_snapshot.inventory_delta.removed?.length">
                消耗: [{{ log.delta_snapshot.inventory_delta.removed.join(', ') }}]
              </template>
            </span>
          </div>
        </div>
      </div>
    </div>
  </NeuCard>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Icon } from '@iconify/vue'
import NeuCard from './NeuCard.vue'
import PhoneMomentsCard from './phone/PhoneMomentsCard.vue'
import PhoneForumCard from './phone/PhoneForumCard.vue'
import PhoneChatGroup from './phone/PhoneChatGroup.vue'
import { parseProseIntoBlocks } from '../utils/phoneParser'
import { useWorldStore } from '../stores/world'
import type { StoryLogView } from '../api/client'

const props = defineProps<{
  log: StoryLogView
  isLatest?: boolean
  isStreaming?: boolean
}>()

const worldStore = useWorldStore()
const characterName = computed(() => worldStore.currentDetail?.name || '')

const isExpanded = ref(false)

const isPendingNonStreaming = computed(() => {
  return props.log.id === -999 && !props.isStreaming
})

const stageBadgeText = computed(() => {
  const stage = worldStore.streamingStage
  if (stage === 'incident_conceive') return '【变数之引】构思变故中'
  if (stage === 'pass1') return '【衡律之神】权衡因果中'
  if (stage === 'pass2') return '【见证之神】编织正文中'
  return '实时流式生成中'
})

const stageIcon = computed(() => {
  const stage = worldStore.streamingStage
  if (stage === 'incident_conceive') return 'material-symbols:bolt'
  if (stage === 'pass1') return 'material-symbols:balance'
  if (stage === 'pass2') return 'material-symbols:ink-pen'
  return 'material-symbols:edit-note'
})

const formatDelta = (val: number) => {
  if (val > 0) return `+${val}`
  return `${val}`
}

const contentBlocks = computed(() => {
  if (!props.log.narrative_prose) return []
  return parseProseIntoBlocks(props.log.narrative_prose)
})

/**
 * 将文学段落中的各类对白/心绪引用赋予不同的雅致色彩
 * 支持双引号 “...”, 角标引 「...」与『...』, 单引号 ‘...’, 英文双引号 "..."
 */
const formatProseText = (raw: string): string => {
  if (!raw) return ''
  const escaped = raw
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')

  let formatted = escaped.replace(
    /(「[^」\n]*[」]?|『[^』\n]*[』]?)/g,
    '<span class="prose-dialogue prose-dialogue-corner">$1</span>'
  )

  formatted = formatted.replace(
    /(‘[^’\n]*[’]?)/g,
    '<span class="prose-dialogue prose-dialogue-single">$1</span>'
  )

  formatted = formatted.replace(
    /(“[^”\n]*[”]?|&quot;[^&"\n]*(&quot;)?)/g,
    '<span class="prose-dialogue prose-dialogue-double">$1</span>'
  )

  return formatted
}

const hasInventoryDelta = computed(() => {
  const inv = props.log.delta_snapshot?.inventory_delta
  return Boolean(inv?.added?.length || inv?.removed?.length)
})
</script>

<style scoped>
.timeline-log-card {
  margin-bottom: 1.5rem;
  background: #f0f3f8;
  border-left: 4px solid var(--neu-accent);
}

.timeline-log-card.is-streaming {
  border-left: 4px solid #3b82f6;
  box-shadow: 0 0 12px rgba(59, 130, 246, 0.15);
}

.generating-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.15rem 0.55rem;
  border-radius: 9999px;
  font-size: 0.725rem;
  color: var(--neu-text-secondary);
  font-weight: 600;
  background: var(--neu-base);
  box-shadow: 1px 1px 3px var(--neu-shadow-dark), -1px -1px 3px var(--neu-shadow-light);
}

.streaming-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.15rem 0.55rem;
  border-radius: 9999px;
  font-size: 0.725rem;
  color: var(--neu-accent);
  font-weight: 600;
  background: var(--neu-base);
  box-shadow: 1px 1px 3px var(--neu-shadow-dark), -1px -1px 3px var(--neu-shadow-light);
}

.streaming-icon {
  font-size: 0.85rem;
}

.pulse-anim {
  animation: pulse-ring 1.5s infinite ease-in-out;
}

@keyframes pulse-ring {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.45; transform: scale(0.92); }
}

.typing-cursor {
  display: inline-block;
  width: 3px;
  height: 1.1em;
  background-color: var(--neu-accent);
  vertical-align: -0.15em;
  margin-left: 3px;
  border-radius: 1px;
  animation: cursor-blink 0.8s infinite;
}

@keyframes cursor-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* 非流式生成中占位 */
.generating-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.6rem;
  padding: 1.25rem 1rem;
  border-radius: 10px;
  color: var(--neu-text-secondary);
  font-size: 0.9rem;
  font-weight: 500;
}

.spin-icon-generating {
  font-size: 1.2rem;
  animation: spin-generating 1s linear infinite;
  color: var(--neu-accent);
}

@keyframes spin-generating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 神性呼唤中卡片 */
.divine-calling-card {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.85rem 1rem;
  border-radius: 10px;
  margin-bottom: 0.85rem;
  font-size: 0.85rem;
  color: var(--neu-text-secondary);
}

.divine-calling-card.divine-witness-card {
  border-left: 3px solid #6366f1;
}

.divine-header {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  flex-shrink: 0;
}

.divine-icon {
  font-size: 1.1rem;
  color: var(--neu-accent);
}

.divine-name {
  font-weight: 600;
  color: var(--neu-accent);
}

.divine-msg {
  display: inline-flex;
  align-items: center;
  font-style: italic;
}

/* 衡律之神裁决结果展示横幅 */
.divine-result-card {
  margin-bottom: 1rem;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  border-left: 3px solid var(--neu-accent);
  background: rgba(240, 243, 248, 0.75);
}

.divine-result-header {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  margin-bottom: 0.35rem;
}

.divine-result-icon {
  font-size: 0.95rem;
  color: var(--neu-accent);
}

.divine-result-tag {
  font-size: 0.775rem;
  font-weight: 600;
  color: var(--neu-accent);
  letter-spacing: 0.02em;
}

.divine-result-prose {
  font-size: 0.85rem;
  line-height: 1.6;
  color: #374151;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid rgba(196, 201, 212, 0.4);
}

.header-left, .header-right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.tick-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.25rem 0.65rem;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--neu-accent);
}

.badge-icon {
  font-size: 1rem;
}

.time-text, .location-text {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.825rem;
  color: var(--neu-text-secondary);
}

.meta-icon {
  font-size: 0.95rem;
}

.log-prose {
  font-size: 0.975rem;
  color: #24292e;
  line-height: 1.95;
  margin-bottom: 1rem;
}

.prose-paragraph {
  text-indent: 2em;
  margin-bottom: 0.85rem;
  white-space: pre-wrap;
}

.prose-paragraph:last-child {
  margin-bottom: 0;
}

:deep(.prose-dialogue) {
  font-weight: 500;
  letter-spacing: 0.01em;
  transition: color 0.15s ease;
}

:deep(.prose-dialogue-double) {
  color: #3730a3; /* 典雅深邃的靛蓝对白，区别于正文普通文本 */
}

:deep(.prose-dialogue-corner) {
  color: #b45309; /* 东方角标引『』「」温暖沉稳的琥珀/金赭色，显现机锋留白 */
}

:deep(.prose-dialogue-single) {
  color: #0f766e; /* 沉静松石绿，显现心理轻声或自言自语 */
}

.delta-inspector {
  margin-top: 0.75rem;
  padding-top: 0.5rem;
}

.toggle-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  background: none;
  border: none;
  color: var(--neu-text-secondary);
  font-size: 0.8rem;
  cursor: pointer;
  padding: 0.25rem 0.5rem;
  border-radius: 6px;
  transition: all 0.2s;
}

.toggle-btn:hover {
  color: var(--neu-accent);
}

.toggle-icon {
  font-size: 1.1rem;
}

.inspector-content {
  margin-top: 0.5rem;
  padding: 0.85rem 1rem;
  font-size: 0.825rem;
  color: var(--neu-text-secondary);
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.fact-beat strong {
  color: var(--neu-text-primary);
  display: block;
  margin-bottom: 0.25rem;
}

.delta-grid {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.delta-item {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
}

.item-title {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  color: var(--neu-text-primary);
  font-weight: 600;
  flex-shrink: 0;
}

.item-icon {
  font-size: 0.95rem;
}

.sensory-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.sensory-tag {
  padding: 0.15rem 0.5rem;
  font-size: 0.75rem;
  background: var(--neu-surface);
  color: var(--neu-text-primary);
}
</style>
