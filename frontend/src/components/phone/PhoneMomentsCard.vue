<template>
  <div class="moments-card neu-flat-sm">
    <!-- 动态来源与分类标签 (去设备化，融入叙事流) -->
    <div class="moments-card-header">
      <div class="channel-tag">
        <Icon icon="material-symbols:camera-roll" class="channel-icon" />
        <span>社交动态 · 朋友圈</span>
      </div>
      <span class="read-only-badge">即时快照</span>
    </div>

    <!-- 朋友圈动态流 -->
    <div class="moments-feed">
      <div v-for="post in posts" :key="post.id" class="feed-item">
        <!-- 用户信息行 -->
        <div class="item-user-row">
          <AvatarBadge :name="post.author" size="md" />
          <div class="item-user-meta">
            <div class="item-username">
              <span class="main-name">{{ getParsedName(post.author).name }}</span>
              <span v-if="getParsedName(post.author).alias" class="name-alias">
                ({{ getParsedName(post.author).alias }})
              </span>
            </div>
            <span class="item-time">刚刚 · 来自即时动态</span>
          </div>
        </div>

        <!-- 动态文本与快照卡片 -->
        <div class="item-content-body">
          <p class="post-text">{{ post.text }}</p>

          <!-- 附带现场快照卡片 -->
          <div v-if="post.imageDesc" class="post-media-card neu-inset-sm">
            <div class="media-icon-wrap">
              <Icon icon="material-symbols:photo-camera" class="media-icon" />
            </div>
            <div class="media-text-wrap">
              <span class="media-tag">附带现场快照</span>
              <p class="media-desc">“{{ post.imageDesc }}”</p>
            </div>
          </div>
        </div>

        <!-- 纯旁观者数据状态指示 (无交互按钮) -->
        <div class="item-stats-bar">
          <div class="stat-pill">
            <Icon icon="material-symbols:favorite" class="stat-icon heart-icon" />
            <span>{{ post.likes.length }} 赞</span>
          </div>
          <div class="stat-pill">
            <Icon icon="material-symbols:chat-bubble-outline" class="stat-icon" />
            <span>{{ post.comments.length }} 评论</span>
          </div>
        </div>

        <!-- 点赞与评论展示卡片 (新拟态内凹，纯旁观者视角) -->
        <div
          v-if="post.likes.length > 0 || post.comments.length > 0"
          class="interactions-box neu-inset-sm"
        >
          <!-- 点赞名单 -->
          <div v-if="post.likes.length > 0" class="likes-list-row">
            <Icon icon="material-symbols:favorite" class="likes-heart-icon" />
            <div class="likes-names">
              <span v-for="(uname, uIdx) in post.likes" :key="uIdx" class="like-user-pill">
                {{ uname }}<span v-if="uIdx < post.likes.length - 1">, </span>
              </span>
            </div>
          </div>

          <!-- 评论列表 -->
          <div v-if="post.comments.length > 0" class="comments-list-section">
            <div
              v-for="(cmt, cIdx) in post.comments"
              :key="cIdx"
              class="comment-line"
            >
              <span class="comment-author">{{ cmt.author }}:</span>
              <span class="comment-text">{{ cmt.text }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Icon } from '@iconify/vue'
import AvatarBadge from './AvatarBadge.vue'
import { parseAuthorName, type MomentsPost } from '../../utils/phoneParser'

defineProps<{
  posts: MomentsPost[]
}>()

const getParsedName = (raw: string) => parseAuthorName(raw)
</script>

<style scoped>
/* 严格遵循 05_UI_UX_NEUMORPHIC_SPEC 规范的浅色新拟态社交动态卡片 */
.moments-card {
  width: 100%;
  margin: 0.95rem 0;
  border-radius: 14px;
  background: var(--neu-surface, #e6e9ef);
  color: var(--neu-text-primary, #2d3748);
  box-shadow: 3px 3px 8px var(--neu-dark, #c4c9d4), -3px -3px 8px var(--neu-light, #ffffff);
  box-sizing: border-box;
}

.moments-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.55rem 0.95rem;
  background: rgba(0, 0, 0, 0.015);
  border-bottom: 1px solid rgba(196, 201, 212, 0.35);
}

.channel-tag {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--neu-accent, #5e72e4);
  letter-spacing: 0.5px;
}

.channel-icon {
  font-size: 0.95rem;
}

.read-only-badge {
  font-size: 0.68rem;
  color: var(--neu-text-muted, #a0aec0);
  background: rgba(0, 0, 0, 0.03);
  padding: 0.1rem 0.45rem;
  border-radius: 4px;
}

.moments-feed {
  padding: 0.95rem 1.1rem 1.1rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.feed-item {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  padding-bottom: 0.85rem;
  border-bottom: 1px solid rgba(196, 201, 212, 0.3);
}

.feed-item:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.item-user-row {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}

.item-user-meta {
  display: flex;
  flex-direction: column;
}

.item-username {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--neu-text-primary, #2d3748);
  display: flex;
  align-items: center;
  gap: 0.3rem;
}

.name-alias {
  font-size: 0.75rem;
  font-weight: normal;
  color: var(--neu-text-secondary, #718096);
}

.item-time {
  font-size: 0.7rem;
  color: var(--neu-text-muted, #a0aec0);
}

.item-content-body {
  margin-left: 2.85rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.post-text {
  font-size: 0.875rem;
  line-height: 1.6;
  color: var(--neu-text-primary, #2d3748);
  white-space: pre-wrap;
  word-break: break-word;
}

.post-media-card {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.65rem 0.85rem;
  border-radius: 10px;
  background: var(--neu-surface, #e6e9ef);
  box-shadow: inset 2px 2px 5px var(--neu-dark, #c4c9d4), inset -2px -2px 5px var(--neu-light, #ffffff);
}

.media-icon-wrap {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: rgba(var(--neu-accent-rgb, 94, 114, 228), 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.media-icon {
  font-size: 1.1rem;
  color: var(--neu-accent, #5e72e4);
}

.media-text-wrap {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.media-tag {
  font-size: 0.685rem;
  font-weight: 600;
  color: var(--neu-accent, #5e72e4);
  letter-spacing: 0.5px;
}

.media-desc {
  font-size: 0.785rem;
  font-style: italic;
  color: var(--neu-text-secondary, #718096);
  line-height: 1.4;
}

/* 纯旁观者统计药丸 */
.item-stats-bar {
  margin-left: 2.85rem;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.85rem;
  padding-top: 0.25rem;
}

.stat-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.75rem;
  color: var(--neu-text-secondary, #718096);
  background: var(--neu-surface, #e6e9ef);
  box-shadow: 1px 1px 3px var(--neu-dark, #c4c9d4), -1px -1px 3px var(--neu-light, #ffffff);
  padding: 0.15rem 0.55rem;
  border-radius: 9999px;
  user-select: none;
}

.stat-icon {
  font-size: 0.85rem;
}

.heart-icon {
  color: #ef4444;
}

.interactions-box {
  margin-left: 2.85rem;
  padding: 0.65rem 0.85rem;
  border-radius: 10px;
  background: var(--neu-surface, #e6e9ef);
  box-shadow: inset 2px 2px 5px var(--neu-dark, #c4c9d4), inset -2px -2px 5px var(--neu-light, #ffffff);
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  font-size: 0.8rem;
}

.likes-list-row {
  display: flex;
  align-items: flex-start;
  gap: 0.4rem;
  color: var(--neu-text-secondary, #718096);
  line-height: 1.45;
  border-bottom: 1px solid rgba(196, 201, 212, 0.4);
  padding-bottom: 0.35rem;
}

.likes-heart-icon {
  font-size: 0.95rem;
  color: #ef4444;
  margin-top: 1px;
  flex-shrink: 0;
}

.likes-names {
  font-weight: 500;
  color: var(--neu-text-primary, #2d3748);
}

.like-user-pill {
  color: var(--neu-accent, #5e72e4);
}

.comments-list-section {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  line-height: 1.5;
}

.comment-line {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.comment-author {
  font-weight: 600;
  color: var(--neu-accent, #5e72e4);
  font-size: 0.785rem;
}

.comment-text {
  color: var(--neu-text-primary, #2d3748);
  font-size: 0.785rem;
}
</style>
