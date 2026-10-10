<template>
  <NeuCard class="timeline-log-card" :class="{ 'is-streaming': isStreaming }" variant="flat">
    <!-- 切片头部元信息与内联操作区 -->
    <div class="log-header" ref="headerRef">
      <!-- 第一行：刻度与时间 (左侧) + 推演状态与三点操作栏 (右侧) -->
      <div class="header-top-row">
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

        <div class="header-controls">
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

          <!-- 点击三点按钮直接在 header 内联展开的操作栏 -->
          <Transition name="action-bar-unroll">
            <div v-if="showActions" class="inline-action-bar neu-flat-xs">
              <!-- 1. 编辑按钮 -->
              <button
                class="bar-btn"
                :class="{ 'is-active': isEditing }"
                :disabled="isOperating || isTicking"
                @click="toggleEdit"
                title="编辑本刻正文内容"
              >
                <Icon icon="material-symbols:edit-note" class="bar-icon" />
                <span>{{ isEditing ? '退出' : '编辑' }}</span>
              </button>

              <!-- 2. 重写按钮 (仅限最新楼层) -->
              <button
                v-if="canRewrite"
                class="bar-btn"
                :disabled="isOperating || isTicking"
                @click="handleRewrite"
                title="撤销当前刻并由 AI 重新推演"
              >
                <Icon icon="material-symbols:refresh" class="bar-icon" />
                <span>重写</span>
              </button>

              <!-- 3. 删除按钮 (级联删除当前刻及后续所有切片) -->
              <button
                class="bar-btn bar-btn-danger"
                :disabled="isOperating || isTicking"
                @click="handleDelete"
                :title="subsequentCount > 1 ? `删除第 ${log.tick_index} 刻及后续 ${subsequentCount - 1} 条切片` : '删除本刻切片'"
              >
                <Icon icon="material-symbols:delete-outline" class="bar-icon bar-icon-danger" />
                <span>删除</span>
              </button>
            </div>
          </Transition>

          <!-- 三点按钮：平滑触发在 header 直接展开/收起操作栏 -->
          <button
            v-if="!isPendingNonStreaming && !isStreaming"
            class="more-trigger-btn neu-flat-xs"
            :class="{ 'is-active': showActions }"
            @click="showActions = !showActions"
            :title="showActions ? '收起操作栏' : '更多操作（编辑/重写/删除）'"
            aria-label="更多操作"
          >
            <Icon icon="material-symbols:more-horiz" class="more-icon" />
          </button>
        </div>
      </div>

      <!-- 第二行：地点统一靠左独立展示，规避高度参差与文本截断 -->
      <div v-if="log.location" class="header-location-row">
        <Icon icon="material-symbols:location-on" class="location-pin" />
        <span class="location-name">{{ log.location }}</span>
      </div>
    </div>

    <!-- 正文区域：编辑态直接就地替换为文本框，不重复显示两次正文 -->
    <div v-if="isEditing" class="prose-edit-container">
      <textarea
        v-model="editDraft"
        class="prose-edit-textarea neu-inset-sm"
        rows="9"
        placeholder="在此直接修改文学正文内容..."
      ></textarea>
      <div class="edit-toolbar">
        <span class="edit-counter">{{ editDraft.length }} 字</span>
        <div class="edit-btn-group">
          <button class="edit-action-btn cancel-btn neu-flat-xs" :disabled="isSaving" @click="cancelEdit">
            <Icon icon="material-symbols:close" class="btn-icon" />
            <span>取消</span>
          </button>
          <button class="edit-action-btn save-btn neu-flat-xs" :disabled="isSaving" @click="saveEdit">
            <Icon icon="material-symbols:check" class="btn-icon" />
            <span>{{ isSaving ? '保存中...' : '保存修改' }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 纯文学正文流 自然段落与拟真手机组件混排 (非编辑态) -->
    <div v-else class="log-prose prose-literary" :class="{ 'is-streaming-text': isStreaming }">
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
        <span>{{ isExpanded ? '收起裁决与状态详情' : '因果裁决与即时状态变动详情' }}</span>
      </button>

      <div v-if="isExpanded" class="inspector-content neu-inset-sm">
        <div class="fact-beat">
          <strong>事件事实经过:</strong>
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
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { Icon } from '@iconify/vue'
import NeuCard from './NeuCard.vue'
import PhoneMomentsCard from './phone/PhoneMomentsCard.vue'
import PhoneForumCard from './phone/PhoneForumCard.vue'
import PhoneChatGroup from './phone/PhoneChatGroup.vue'
import { parseProseIntoBlocks } from '../utils/phoneParser'
import { useWorldStore } from '../stores/world'
import { useConfirm } from '../composables/useConfirm'
import { useToast } from '../composables/useToast'
import { apiClient, type StoryLogView } from '../api/client'

const props = defineProps<{
  log: StoryLogView
  isLatest?: boolean
  isStreaming?: boolean
}>()

const worldStore = useWorldStore()
const { confirm } = useConfirm()
const toast = useToast()

const characterName = computed(() => worldStore.currentDetail?.name || '')

const headerRef = ref<HTMLElement | null>(null)
const showActions = ref(false)
const isExpanded = ref(false)
const isEditing = ref(false)
const editDraft = ref(props.log.narrative_prose || '')
const isSaving = ref(false)
const isOperating = ref(false)

const isTicking = computed(() => worldStore.isTicking)

// 监听正文变化，未处于编辑态时保持同步
watch(
  () => props.log.narrative_prose,
  (newVal) => {
    if (!isEditing.value) {
      editDraft.value = newVal || ''
    }
  }
)

// 点击页面外部区域时自动收起内联操作栏
const handleDocClick = (e: MouseEvent) => {
  if (showActions.value && headerRef.value && !headerRef.value.contains(e.target as Node)) {
    showActions.value = false
  }
}

onMounted(() => {
  document.addEventListener('pointerdown', handleDocClick)
})

onUnmounted(() => {
  document.removeEventListener('pointerdown', handleDocClick)
})

const isPendingNonStreaming = computed(() => {
  return props.log.id === -999 && !props.isStreaming
})

// 重写仅在最新楼层展示且推演闲置状态下可用
const canRewrite = computed(() => {
  return (
    Boolean(props.isLatest) &&
    !props.isStreaming &&
    !isPendingNonStreaming.value &&
    !worldStore.isTicking &&
    Boolean(props.log.id && props.log.id !== -999)
  )
})

// 计算本刻及后续级联删除的切片总数
const subsequentCount = computed(() => {
  return worldStore.timeline.filter((item) => item.tick_index >= props.log.tick_index).length
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
 * 切换编辑状态
 */
const toggleEdit = () => {
  if (isEditing.value) {
    cancelEdit()
  } else {
    editDraft.value = props.log.narrative_prose || ''
    isEditing.value = true
    showActions.value = false
  }
}

const cancelEdit = () => {
  isEditing.value = false
  editDraft.value = props.log.narrative_prose || ''
}

const saveEdit = async () => {
  if (isSaving.value || !props.log.id || props.log.id === -999) return
  isSaving.value = true
  try {
    if (typeof (worldStore as any).updateTimelineLog === 'function') {
      await (worldStore as any).updateTimelineLog(props.log.id, editDraft.value)
    } else {
      await apiClient.updateTimelineLog(props.log.character_id, props.log.id, {
        narrative_prose: editDraft.value,
      })
      const target = worldStore.timeline.find((i) => i.id === props.log.id)
      if (target) target.narrative_prose = editDraft.value
    }
    toast.showSuccess(`第 ${props.log.tick_index} 刻正文修改已保存`)
    isEditing.value = false
  } catch (err: any) {
    toast.show({
      type: 'error',
      title: '保存修改失败',
      description: err.message || '网络或接口服务异常',
    })
  } finally {
    isSaving.value = false
  }
}

/**
 * 重写最新楼层
 */
const handleRewrite = async () => {
  showActions.value = false
  const ok = await confirm({
    title: '重写故事切片',
    message: `确定要重写第 ${props.log.tick_index} 刻吗？\n当前最新的正文与状态将撤销，并由 AI 重新推演生成。`,
    variant: 'warning',
    confirmText: '重新推演',
    cancelText: '取消',
    icon: 'material-symbols:refresh',
  })

  if (!ok) return

  isOperating.value = true
  try {
    if (typeof (worldStore as any).rewriteLatestLog === 'function') {
      await (worldStore as any).rewriteLatestLog(props.log)
    } else {
      await apiClient.deleteTimelineLog(props.log.character_id, props.log.id)
      worldStore.timeline = worldStore.timeline.filter((i) => i.tick_index < props.log.tick_index)
      await Promise.all([worldStore.refreshState(), worldStore.refreshRelationships()])
      await worldStore.runContinue()
    }
    toast.showSuccess(`已启动第 ${props.log.tick_index} 刻重新推演`)
  } catch (err: any) {
    toast.show({
      type: 'error',
      title: '重写切片失败',
      description: err.message || '操作未完成，请重试',
    })
  } finally {
    isOperating.value = false
  }
}

/**
 * 删除当前切片并自动级联删除后续所有切片，回滚状态
 */
const handleDelete = async () => {
  showActions.value = false
  const count = subsequentCount.value
  let message = ''
  if (count > 1) {
    message = `删除第 ${props.log.tick_index} 刻将同时级联删除此后的所有故事切片（共 ${count} 刻），并自动回滚世界状态至该时刻之前。\n\n此操作不可逆，是否确认删除？`
  } else {
    message = `是否确认删除第 ${props.log.tick_index} 刻故事切片并回滚世界状态至前一刻？\n\n此操作不可逆，是否确认？`
  }

  const ok = await confirm({
    title: '删除故事切片',
    message,
    variant: 'danger',
    confirmText: count > 1 ? `删除 ${count} 刻并回滚` : '确认删除',
    cancelText: '取消',
    icon: 'material-symbols:delete-forever',
  })

  if (!ok) return

  isOperating.value = true
  try {
    if (typeof (worldStore as any).deleteTimelineLog === 'function') {
      await (worldStore as any).deleteTimelineLog(props.log)
    } else {
      await apiClient.deleteTimelineLog(props.log.character_id, props.log.id)
      worldStore.timeline = worldStore.timeline.filter((item) => item.tick_index < props.log.tick_index)
      await Promise.all([worldStore.refreshState(), worldStore.refreshRelationships()])
    }
    toast.showSuccess(
      count > 1
        ? `第 ${props.log.tick_index} 刻及后续 ${count - 1} 刻切片已删除，世界已回滚`
        : `第 ${props.log.tick_index} 刻切片已删除，世界已回滚`
    )
  } catch (err: any) {
    toast.show({
      type: 'error',
      title: '删除切片失败',
      description: err.message || '操作未完成，请重试',
    })
  } finally {
    isOperating.value = false
  }
}

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
  background: var(--neu-surface);
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
  background: var(--neu-surface);
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
  background: var(--neu-surface);
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
  background: var(--neu-surface);
  box-shadow: var(--shadow-flat-sm);
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
  color: var(--neu-text-primary);
}

.log-header {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  margin-bottom: 1rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid rgba(196, 201, 212, 0.4);
  position: relative;
}

.header-top-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  min-height: 28px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  flex-shrink: 0;
}

.header-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  position: relative;
  flex-shrink: 0;
}

.header-location-row {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.825rem;
  color: var(--neu-text-secondary);
  line-height: 1.45;
  word-break: break-word;
  padding-left: 0.15rem;
}

.location-pin {
  color: var(--neu-accent);
  font-size: 0.95rem;
  flex-shrink: 0;
}

.location-name {
  color: var(--neu-text-secondary);
  font-weight: 500;
}

.tick-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.25rem 0.65rem;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--neu-accent);
  white-space: nowrap;
  flex-shrink: 0;
  line-height: 1;
}

.badge-icon {
  font-size: 1rem;
  flex-shrink: 0;
}

.time-text {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.825rem;
  color: var(--neu-text-secondary);
  white-space: nowrap;
  flex-shrink: 0;
  line-height: 1;
}

.meta-icon {
  font-size: 0.95rem;
  flex-shrink: 0;
}

/* 三点更多操作触发按钮 */
.more-trigger-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 8px;
  border: none;
  background: var(--neu-base);
  color: var(--neu-text-secondary);
  cursor: pointer;
  box-shadow: 1px 1px 3px var(--neu-shadow-dark), -1px -1px 3px var(--neu-shadow-light);
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  flex-shrink: 0;
}

.more-trigger-btn:hover {
  color: var(--neu-accent);
  transform: translateY(-1px);
}

.more-trigger-btn:active,
.more-trigger-btn.is-active {
  box-shadow: inset 1px 1px 2px var(--neu-shadow-dark), inset -1px -1px 2px var(--neu-shadow-light);
  color: var(--neu-accent);
}

.more-icon {
  font-size: 1.15rem;
}

/* 内联操作栏 (直接在 header 右侧平滑展开) */
.inline-action-bar {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 2px 5px;
  border-radius: 9999px;
  background: var(--neu-base);
  box-shadow: inset 1px 1px 3px var(--neu-shadow-dark), inset -1px -1px 3px var(--neu-shadow-light);
  flex-shrink: 0;
  white-space: nowrap;
  height: 28px;
  box-sizing: border-box;
}

.bar-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  padding: 0.15rem 0.5rem;
  border: none;
  background: transparent;
  border-radius: 9999px;
  font-size: 0.725rem;
  font-weight: 600;
  color: var(--neu-text-secondary);
  cursor: pointer;
  line-height: 1;
  transition: all 0.15s ease;
}

.bar-btn:hover:not(:disabled) {
  color: var(--neu-accent);
  background: rgba(var(--neu-accent-rgb, 94, 114, 228), 0.12);
}

.bar-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.bar-btn.is-active {
  color: var(--neu-accent);
  background: var(--neu-surface);
  box-shadow: 1px 1px 2px var(--neu-shadow-dark);
}

.bar-btn-danger:hover:not(:disabled) {
  color: var(--neu-danger) !important;
  background: rgba(229, 62, 62, 0.15) !important;
}

.bar-icon {
  font-size: 0.95rem;
}

.bar-icon-danger {
  color: inherit;
}

/* 动效：展开内联操作栏 (纯平滑淡入微移，杜绝抖动与高度变化) */
.action-bar-unroll-enter-active,
.action-bar-unroll-leave-active {
  transition: opacity 0.18s ease, transform 0.18s cubic-bezier(0.16, 1, 0.3, 1);
  transform-origin: right center;
}

.action-bar-unroll-enter-from,
.action-bar-unroll-leave-to {
  opacity: 0;
  transform: scale(0.92) translateX(6px);
}

.action-bar-unroll-enter-to,
.action-bar-unroll-leave-from {
  opacity: 1;
  transform: scale(1) translateX(0);
}

/* 正文编辑文本框容器 */
.prose-edit-container {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  margin-bottom: 1rem;
}

.prose-edit-textarea {
  width: 100%;
  padding: 0.85rem 1rem;
  border: none;
  outline: none;
  border-radius: 10px;
  background: var(--neu-surface);
  box-shadow: var(--shadow-inset-sm);
  font-size: 0.95rem;
  line-height: 1.85;
  color: var(--neu-text-primary);
  font-family: inherit;
  resize: vertical;
  min-height: 160px;
  box-sizing: border-box;
}

.prose-edit-textarea:focus {
  box-shadow: var(--shadow-inset), 0 0 0 2px rgba(var(--neu-accent-rgb, 94, 114, 228), 0.35);
}

.edit-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 0.25rem;
}

.edit-counter {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--neu-text-muted);
}

.edit-btn-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.edit-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.35rem 0.85rem;
  border: none;
  border-radius: 8px;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.18s ease;
}

.edit-action-btn.cancel-btn {
  color: var(--neu-text-secondary);
  background: var(--neu-base);
  box-shadow: 1px 1px 3px var(--neu-shadow-dark), -1px -1px 3px var(--neu-shadow-light);
}

.edit-action-btn.cancel-btn:hover:not(:disabled) {
  color: var(--neu-text-primary);
}

.edit-action-btn.save-btn {
  color: #fff;
  background: var(--neu-accent);
  box-shadow: 2px 2px 6px var(--neu-shadow-dark), -1px -1px 3px var(--neu-shadow-light);
}

.edit-action-btn.save-btn:hover:not(:disabled) {
  filter: brightness(1.08);
}

.edit-action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 响应式移动端换行布局 */
@media (max-width: 680px) {
  .log-header {
    gap: 0.4rem;
  }

  .header-top-row {
    gap: 0.5rem;
  }

  .header-left {
    gap: 0.45rem;
  }

  .header-location-row {
    font-size: 0.8rem;
  }
}


.meta-icon {
  font-size: 0.95rem;
}

.log-prose {
  font-size: 0.975rem;
  color: var(--neu-text-primary);
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
  color: var(--dialogue-double, var(--neu-accent)); /* 依据主题色动态衍生，自适应深浅背景 */
}

:deep(.prose-dialogue-corner) {
  color: var(--dialogue-corner, var(--neu-accent-hover)); /* 东方角标引『』「」，主题邻近微暖/高对比层次 */
}

:deep(.prose-dialogue-single) {
  color: var(--dialogue-single, var(--neu-accent)); /* 单引号心绪/轻声，同主题淡雅微光 */
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
