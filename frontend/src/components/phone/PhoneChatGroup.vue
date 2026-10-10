<template>
  <div class="chat-flow">
    <div
      v-for="item in items"
      :key="item.id"
      class="chat-row"
      :class="{ 'is-self': isSelf(item.sender) }"
    >
      <!-- 他人头像 (左侧) -->
      <AvatarBadge
        v-if="!isSelf(item.sender)"
        :name="item.sender"
        size="sm"
        class="chat-avatar"
      />

      <!-- 消息内容体 -->
      <div class="bubble-wrapper">
        <!-- 发送人名称 (非自己时显示) -->
        <span v-if="!isSelf(item.sender)" class="bubble-sender-name">
          {{ getParsedName(item.sender).name }}
          <span v-if="getParsedName(item.sender).alias" class="name-alias">
            ({{ getParsedName(item.sender).alias }})
          </span>
        </span>

        <!-- 1. 普通即时文本消息 -->
        <div v-if="item.type === 'message'" class="chat-bubble neu-flat-sm">
          <p class="bubble-text">{{ item.content }}</p>
        </div>

        <!-- 2. 语音消息卡片 -->
        <div v-else-if="item.type === 'voice'" class="voice-card neu-flat-sm">
          <div class="voice-bar">
            <Icon icon="material-symbols:graphic-eq" class="voice-wave-icon" />
            <span class="voice-duration">{{ item.extra?.duration || '8"' }}</span>
          </div>
          <div class="voice-transcript">
            <span class="transcript-tag">语音转文字:</span>
            <p class="transcript-text">“{{ item.content }}”</p>
          </div>
        </div>

        <!-- 3. 定位分享卡片 -->
        <div v-else-if="item.type === 'location'" class="location-card neu-flat-sm">
          <div class="location-header">
            <Icon icon="material-symbols:location-on" class="location-icon" />
            <span class="location-tag">实时位置分享</span>
          </div>
          <div class="location-body">
            <strong class="location-title">{{ item.extra?.locationTitle || item.content }}</strong>
            <p v-if="item.extra?.locationDesc" class="location-desc">
              {{ item.extra?.locationDesc }}
            </p>
          </div>
        </div>

        <!-- 4. 转账消息卡片 -->
        <div v-else-if="item.type === 'transfer'" class="transfer-card neu-flat-sm">
          <div class="transfer-top">
            <div class="transfer-icon-box">
              <Icon icon="material-symbols:currency-exchange" class="transfer-icon" />
            </div>
            <div class="transfer-info">
              <span class="transfer-amount">{{ getTransferAmount(item) }}</span>
              <span class="transfer-note">{{ getTransferNote(item) }}</span>
            </div>
          </div>
          <div class="transfer-footer">
            <span>已存入账户</span>
          </div>
        </div>
      </div>

      <!-- 自己头像 (右侧) -->
      <AvatarBadge
        v-if="isSelf(item.sender)"
        :name="item.sender"
        size="sm"
        :is-character="true"
        class="chat-avatar"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { Icon } from '@iconify/vue'
import AvatarBadge from './AvatarBadge.vue'
import { parseAuthorName, type ChatMessageItem } from '../../utils/phoneParser'

const props = defineProps<{
  items: ChatMessageItem[]
  protagonistName?: string
}>()

const getParsedName = (raw: string) => parseAuthorName(raw)

/** 提取转账金额 (纯金额部分，去除附言) */
const getTransferAmount = (item: ChatMessageItem): string => {
  if (item.extra?.amount) return item.extra.amount
  const m = item.content.match(/^([^\(（]+?)[\s]*[\(（]([^\)）]+)[\)）]/)
  return m ? m[1].trim() : item.content
}

/** 提取转账备注附言 (显示在金额下方，替代重复发件人) */
const getTransferNote = (item: ChatMessageItem): string => {
  if (item.extra?.note && item.extra.note !== '转账附言') return item.extra.note
  const m = item.content.match(/[\(（]([^\)）]+)[\)）]/)
  if (m) return m[1].trim()
  return item.extra?.note || '转账附言'
}

const isSelf = (sender: string) => {
  const clean = sender.trim().toLowerCase()
  if (clean === '我' || clean === 'you' || clean === 'user') return true
  if (props.protagonistName && clean.includes(props.protagonistName.toLowerCase())) return true
  return false
}
</script>

<style scoped>
/* 自然融入小说流的即时消息流，无外部笨重设备框 */
.chat-flow {
  width: 100%;
  margin: 0.85rem 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.chat-row {
  display: flex;
  align-items: flex-start;
  gap: 0.65rem;
}

.chat-row.is-self {
  justify-content: flex-end;
}

.chat-avatar {
  margin-top: 2px;
}

.bubble-wrapper {
  display: flex;
  flex-direction: column;
  max-width: 82%;
  gap: 0.25rem;
}

.chat-row.is-self .bubble-wrapper {
  align-items: flex-end;
}

.bubble-sender-name {
  font-size: 0.725rem;
  color: var(--neu-text-secondary, #718096);
  margin-left: 0.25rem;
  font-weight: 500;
}

.name-alias {
  font-size: 0.685rem;
  color: var(--neu-text-muted, #a0aec0);
}

/* 1. 普通聊天气泡 (新拟态浮凸) */
.chat-bubble {
  padding: 0.55rem 0.85rem;
  border-radius: 12px;
  background: var(--neu-surface, #e6e9ef);
  box-shadow: 2px 2px 6px var(--neu-dark, #c4c9d4), -2px -2px 6px var(--neu-light, #ffffff);
}

.chat-row.is-self .chat-bubble {
  background: #edf2ff;
  box-shadow: 2px 2px 6px var(--neu-dark, #c4c9d4), -2px -2px 6px var(--neu-light, #ffffff);
}

.bubble-text {
  font-size: 0.875rem;
  line-height: 1.5;
  color: var(--neu-text-primary, #2d3748);
  white-space: pre-wrap;
  word-break: break-word;
}

/* 2. 语音消息 */
.voice-card {
  padding: 0.6rem 0.85rem;
  border-radius: 12px;
  background: var(--neu-surface, #e6e9ef);
  box-shadow: 2px 2px 6px var(--neu-dark, #c4c9d4), -2px -2px 6px var(--neu-light, #ffffff);
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  min-width: 190px;
}

.chat-row.is-self .voice-card {
  background: #edf2ff;
  border-color: rgba(94, 114, 228, 0.3);
}

.voice-bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--neu-accent, #5e72e4);
}

.voice-wave-icon {
  font-size: 1.25rem;
}

.voice-duration {
  font-size: 0.8rem;
  font-weight: 700;
  margin-left: auto;
  color: var(--neu-text-secondary, #718096);
}

.voice-transcript {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  padding-top: 0.35rem;
  border-top: 1px dashed rgba(196, 201, 212, 0.6);
}

.transcript-tag {
  font-size: 0.685rem;
  color: var(--neu-text-muted, #a0aec0);
}

.transcript-text {
  font-size: 0.8rem;
  font-style: italic;
  color: var(--neu-text-primary, #2d3748);
  line-height: 1.45;
}

/* 3. 定位分享卡片 */
.location-card {
  padding: 0.65rem 0.85rem;
  border-radius: 12px;
  background: var(--neu-surface, #e6e9ef);
  box-shadow: 2px 2px 6px var(--neu-dark, #c4c9d4), -2px -2px 6px var(--neu-light, #ffffff);
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  min-width: 200px;
}

.location-header {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  color: var(--neu-accent, #5e72e4);
}

.location-icon {
  font-size: 1.05rem;
}

.location-tag {
  font-size: 0.7rem;
  font-weight: 600;
}

.location-body {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.location-title {
  font-size: 0.825rem;
  color: var(--neu-text-primary, #2d3748);
}

.location-desc {
  font-size: 0.725rem;
  color: var(--neu-text-secondary, #718096);
}

/* 4. 转账卡片 */
.transfer-card {
  padding: 0.75rem 0.95rem;
  border-radius: 12px;
  background: #fef9ee;
  box-shadow: 2px 2px 6px var(--neu-dark, #c4c9d4), -2px -2px 6px var(--neu-light, #ffffff);
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  min-width: 210px;
}

.transfer-top {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}

.transfer-icon-box {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #f59e0b;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 1px 1px 3px rgba(0, 0, 0, 0.15);
}

.transfer-icon {
  font-size: 1.15rem;
}

.transfer-info {
  display: flex;
  flex-direction: column;
}

.transfer-amount {
  font-size: 0.95rem;
  font-weight: 700;
  color: #b45309;
}

.transfer-note {
  font-size: 0.75rem;
  color: #78350f;
  margin-top: 2px;
  line-height: 1.35;
  font-weight: 500;
}

.transfer-footer {
  font-size: 0.685rem;
  color: #a16207;
  border-top: 1px dashed rgba(217, 119, 6, 0.2);
  padding-top: 0.3rem;
}
</style>
