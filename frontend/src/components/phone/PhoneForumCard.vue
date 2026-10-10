<template>
  <div class="forum-card neu-flat-sm">
    <!-- 论坛头部 Header -->
    <div class="forum-header">
      <div class="forum-brand">
        <Icon icon="material-symbols:dynamic-feed" class="forum-logo-icon" />
        <div class="forum-brand-text">
          <span class="forum-site-title">COMMUNITY BBS</span>
          <span class="forum-site-sub">网络论坛 · 社区热帖</span>
        </div>
      </div>
      <div class="forum-board-badge neu-flat-sm" :class="boardBadgeClass">
        <Icon icon="material-symbols:tag" class="badge-icon" />
        <span>{{ data.boardName || '生活看板' }}</span>
      </div>
    </div>

    <!-- 主贴正文区 -->
    <div class="forum-main-post">
      <!-- 发帖人信息行 -->
      <div class="forum-author-row">
        <AvatarBadge :name="data.author" size="md" />
        <div class="forum-author-meta">
          <span class="forum-author-name">
            {{ getParsedName(data.author).name }}
            <span v-if="getParsedName(data.author).alias" class="name-alias">
              ({{ getParsedName(data.author).alias }})
            </span>
          </span>
          <span class="forum-post-time">刚刚 · 来自内网终端</span>
        </div>
      </div>

      <!-- 帖子标题 (若有) -->
      <h4 v-if="data.title" class="forum-post-title">{{ data.title }}</h4>

      <!-- 帖子正文 -->
      <div class="forum-post-body">
        <p class="body-text">{{ data.body }}</p>

        <!-- 帖子随附图片快照 -->
        <div v-if="data.imageDesc" class="forum-media-box neu-inset-sm">
          <div class="media-icon-wrap">
            <Icon icon="material-symbols:photo-camera" class="media-icon" />
          </div>
          <div class="media-text-wrap">
            <span class="media-tag">贴内附件快照</span>
            <p class="media-desc">“{{ data.imageDesc }}”</p>
          </div>
        </div>
      </div>

      <!-- 纯旁观者数据指示栏 (无用户互动按钮) -->
      <div class="forum-stats-bar">
        <div class="forum-stats-text">
          <span class="stat-item">
            <Icon icon="material-symbols:visibility" class="stat-icon" />
            {{ statsParts.views }}
          </span>
          <span v-if="statsParts.likes" class="stat-item">
            <Icon icon="material-symbols:thumb-up" class="stat-icon" />
            {{ statsParts.likes }}
          </span>
        </div>

        <div class="forum-stats-right">
          <div class="forum-stat-pill">
            <Icon icon="material-symbols:chat-bubble-outline" class="stat-icon" />
            <span>{{ data.comments.length }} 回复</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 锁定通知横幅 (若锁定) -->
    <div v-if="data.isLocked" class="forum-locked-banner neu-inset-sm">
      <Icon icon="material-symbols:lock" class="locked-icon" />
      <span>管理员已锁定该贴，当前禁止回复与跟帖。</span>
    </div>

    <!-- 回帖与评论列表 (纯观察者视角) -->
    <div v-if="data.comments.length > 0" class="forum-comments-section">
      <div class="comments-header">
        <span class="comments-count-title">
          <Icon icon="material-symbols:forum" class="header-icon" />
          回帖讨论 ({{ data.comments.length }})
        </span>
        <span class="sort-tag">热度排序</span>
      </div>

      <div class="comments-list">
        <div
          v-for="(cmt, idx) in data.comments"
          :key="idx"
          class="comment-item neu-inset-sm"
        >
          <AvatarBadge :name="cmt.author" size="sm" />
          <div class="comment-content">
            <div class="comment-header-row">
              <span class="comment-user">
                {{ getParsedName(cmt.author).name }}
                <span v-if="cmt.replyTo" class="reply-target">
                  回复 @{{ getParsedName(cmt.replyTo).name }}
                </span>
              </span>
              <span class="floor-num">#{{ idx + 1 }}</span>
            </div>
            <p class="comment-text">{{ cmt.text }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Icon } from '@iconify/vue'
import AvatarBadge from './AvatarBadge.vue'
import { parseAuthorName, type ForumData } from '../../utils/phoneParser'

const props = defineProps<{
  data: ForumData
}>()

const getParsedName = (raw: string) => parseAuthorName(raw)

const boardBadgeClass = computed(() => {
  const b = props.data.boardName || ''
  if (b.includes('公告') || b.includes('官方')) return 'badge-official'
  if (b.includes('生活') || b.includes('广场')) return 'badge-square'
  if (b.includes('树洞')) return 'badge-treehole'
  return 'badge-default'
})

const statsParts = computed(() => {
  const raw = props.data.statsStr || ''
  const parts = raw.split(/[·•|]/)
  if (parts.length >= 2) {
    return { views: parts[0].trim(), likes: parts[1].trim() }
  }
  return { views: raw || '1.2k 浏览', likes: '' }
})
</script>

<style scoped>
/* 严格遵循 05_UI_UX_NEUMORPHIC_SPEC 规范的浅色新拟态论坛卡片 */
.forum-card {
  width: 100%;
  margin: 0.95rem 0;
  border-radius: 14px;
  background: var(--neu-surface, #e6e9ef);
  color: var(--neu-text-primary, #2d3748);
  box-shadow: 3px 3px 8px var(--neu-dark, #c4c9d4), -3px -3px 8px var(--neu-light, #ffffff);
  box-sizing: border-box;
}

.forum-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1.15rem;
  background: rgba(0, 0, 0, 0.02);
  border-bottom: 1px solid rgba(196, 201, 212, 0.4);
}

.forum-brand {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}

.forum-logo-icon {
  font-size: 1.35rem;
  color: var(--neu-accent, #5e72e4);
}

.forum-brand-text {
  display: flex;
  flex-direction: column;
}

.forum-site-title {
  font-size: 0.825rem;
  font-weight: 700;
  letter-spacing: 1.2px;
  color: var(--neu-text-primary, #2d3748);
}

.forum-site-sub {
  font-size: 0.685rem;
  color: var(--neu-text-secondary, #718096);
}

.forum-board-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.25rem 0.65rem;
  border-radius: 9999px;
  font-size: 0.725rem;
  font-weight: 600;
  background: var(--neu-surface, #e6e9ef);
  box-shadow: 1px 1px 3px var(--neu-dark, #c4c9d4), -1px -1px 3px var(--neu-light, #ffffff);
}

.badge-icon {
  font-size: 0.85rem;
}

.badge-official {
  color: #2563eb;
}

.badge-square {
  color: #059669;
}

.badge-treehole {
  color: #7c3aed;
}

.badge-default {
  color: var(--neu-accent, #5e72e4);
}

.forum-main-post {
  padding: 1rem 1.15rem 0.95rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.forum-author-row {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}

.forum-author-meta {
  display: flex;
  flex-direction: column;
}

.forum-author-name {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--neu-text-primary, #2d3748);
}

.name-alias {
  font-size: 0.75rem;
  font-weight: normal;
  color: var(--neu-text-secondary, #718096);
}

.forum-post-time {
  font-size: 0.7rem;
  color: var(--neu-text-muted, #a0aec0);
}

.forum-post-title {
  font-size: 0.975rem;
  font-weight: 700;
  color: var(--neu-text-primary, #2d3748);
  line-height: 1.45;
  margin-top: 0.15rem;
}

.forum-post-body {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.body-text {
  font-size: 0.875rem;
  line-height: 1.65;
  color: var(--neu-text-primary, #2d3748);
  white-space: pre-wrap;
  word-break: break-word;
}

.forum-media-box {
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
  background: rgba(94, 114, 228, 0.12);
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
}

.media-desc {
  font-size: 0.785rem;
  font-style: italic;
  color: var(--neu-text-secondary, #718096);
  line-height: 1.4;
}

.forum-stats-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 0.65rem;
  border-top: 1px solid rgba(196, 201, 212, 0.35);
  margin-top: 0.25rem;
}

.forum-stats-text {
  display: flex;
  gap: 0.85rem;
  font-size: 0.75rem;
  color: var(--neu-text-secondary, #718096);
}

.stat-item {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}

.stat-icon {
  font-size: 0.9rem;
}

.forum-stats-right {
  display: flex;
}

.forum-stat-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  background: var(--neu-surface, #e6e9ef);
  box-shadow: 1px 1px 3px var(--neu-dark, #c4c9d4), -1px -1px 3px var(--neu-light, #ffffff);
  padding: 0.15rem 0.55rem;
  border-radius: 9999px;
  font-size: 0.725rem;
  color: var(--neu-text-secondary, #718096);
  user-select: none;
}

.forum-locked-banner {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.55rem 0.95rem;
  margin: 0.25rem 1.15rem 0.85rem;
  background: rgba(239, 68, 68, 0.12);
  border: 1px solid rgba(239, 68, 68, 0.25);
  border-radius: 8px;
  font-size: 0.75rem;
  color: var(--neu-danger);
}

.locked-icon {
  font-size: 1rem;
  flex-shrink: 0;
}

.forum-comments-section {
  background: rgba(0, 0, 0, 0.02);
  padding: 0.85rem 1.15rem 1.15rem;
  border-top: 1px solid rgba(196, 201, 212, 0.35);
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.comments-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.75rem;
  color: var(--neu-text-secondary, #718096);
  font-weight: 600;
}

.comments-count-title {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}

.header-icon {
  font-size: 0.95rem;
}

.sort-tag {
  font-size: 0.685rem;
  color: var(--neu-text-muted, #a0aec0);
}

.comments-list {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}

.comment-item {
  display: flex;
  align-items: flex-start;
  gap: 0.65rem;
  padding: 0.65rem 0.85rem;
  border-radius: 10px;
  background: var(--neu-surface, #e6e9ef);
  box-shadow: inset 1px 1px 3px var(--neu-dark, #c4c9d4), inset -1px -1px 3px var(--neu-light, #ffffff);
}

.comment-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.comment-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.comment-user {
  font-size: 0.785rem;
  font-weight: 600;
  color: var(--neu-accent, #5e72e4);
}

.reply-target {
  font-size: 0.725rem;
  font-weight: normal;
  color: var(--neu-text-secondary, #718096);
  margin-left: 0.35rem;
}

.floor-num {
  font-size: 0.685rem;
  color: var(--neu-text-muted, #a0aec0);
  font-family: monospace;
}

.comment-text {
  font-size: 0.8rem;
  color: var(--neu-text-primary, #2d3748);
  line-height: 1.45;
  word-break: break-word;
}
</style>
