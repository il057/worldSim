<template>
  <NeuCard class="timeline-log-card" variant="flat">
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
        <span class="location-text">
          <Icon icon="material-symbols:location-on" class="meta-icon" />
          {{ log.location }}
        </span>
      </div>
    </div>

    <!-- 纯文学正文流 (Pass 2) 自然段落排版 -->
    <div class="log-prose prose-literary">
      <p
        v-for="(para, pIdx) in paragraphs"
        :key="pIdx"
        class="prose-paragraph"
      >
        {{ para }}
      </p>
    </div>

    <!-- Pass 1 客观事实骨架与增量检视器折叠面板 -->
    <div v-if="log.delta_snapshot || log.plot_beat" class="delta-inspector">
      <button class="toggle-btn" @click="isExpanded = !isExpanded">
        <Icon
          :icon="isExpanded ? 'material-symbols:expand-less' : 'material-symbols:expand-more'"
          class="toggle-icon"
        />
        <span>{{ isExpanded ? '收起裁决详情' : '查看本轮客观事实骨架与状态增量' }}</span>
      </button>

      <div v-if="isExpanded" class="inspector-content neu-inset-sm">
        <div class="fact-beat">
          <strong>事实骨架 (Plot Beat):</strong>
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
import type { StoryLogView } from '../api/client'

const props = defineProps<{
  log: StoryLogView
  isLatest?: boolean
}>()

const isExpanded = ref(false)

const formatDelta = (val: number) => {
  if (val > 0) return `+${val}`
  return `${val}`
}

const paragraphs = computed(() => {
  if (!props.log.narrative_prose) return []
  return props.log.narrative_prose
    .split(/\n+/)
    .map((p) => p.trim())
    .filter((p) => p.length > 0)
})

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
