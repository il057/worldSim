<template>
  <div class="world-app">
    <!-- ======================================================== -->
    <!-- 1. 顶部全功能导航控制条 (SillyTavern 风格新拟态 TopBar) -->
    <!-- ======================================================== -->
    <header class="top-nav-bar neu-flat">
      <!-- 左侧：侧边栏切换 + 世界时钟 -->
      <div class="nav-section-left">
        <button
          :class="['icon-action-btn', 'neu-flat-sm', { 'is-active': isLeftDrawerOpen }]"
          title="切换左侧菜单 (角色名录 / 故事编年)"
          @click="toggleLeftDrawer"
        >
          <Icon icon="material-symbols:dock-to-left" class="nav-icon" />
        </button>

        <div class="world-clock-badge neu-inset-sm">
          <Icon icon="material-symbols:timelapse" class="clock-icon" />
          <span class="clock-text">{{ worldStore.currentState?.virtual_time || '时空静止' }}</span>
        </div>

        <div class="state-pill neu-flat-sm hide-mobile">
          <Icon
            :icon="worldStore.isSleeping ? 'material-symbols:bedtime' : 'material-symbols:timelapse'"
            :class="['state-icon', { 'pulse-anim': worldStore.isSleeping }]"
          />
          <span>{{ worldStore.isSleeping ? '休眠恢复中' : '清醒演化中' }}</span>
        </div>
      </div>

      <!-- 中间：核心沙盒推进按钮组 (纯按钮无文本框交互) -->
      <div class="nav-section-center">
        <div class="stepper-controls neu-inset-sm">
          <button
            class="step-btn continue-btn"
            title="智能续写：由 AI 自主判断合理时间切速与情节推进"
            :disabled="worldStore.isTicking"
            @click="worldStore.runContinue()"
          >
            <Icon icon="material-symbols:auto-stories" class="btn-symbol continue-icon" />
            <span class="btn-text continue-text">续写</span>
          </button>

          <button
            class="step-btn"
            title="推进 1 虚拟小时 (+1h)"
            :disabled="worldStore.isTicking"
            @click="worldStore.runStep(1)"
          >
            <Icon icon="line-md:chevron-right" class="btn-symbol" />
            <span class="btn-text">+1h</span>
          </button>

          <button
            class="step-btn"
            title="阶段快进 6 小时 (+6h)"
            :disabled="worldStore.isTicking"
            @click="worldStore.runFastForward('hour_6')"
          >
            <Icon icon="line-md:chevron-double-right" class="btn-symbol" />
            <span class="btn-text">+6h</span>
          </button>

          <button
            class="step-btn"
            title="跨日跃迁 24 小时 (+24h)"
            :disabled="worldStore.isTicking"
            @click="worldStore.runFastForward('day_1')"
          >
            <Icon icon="line-md:chevron-triple-right" class="btn-symbol" />
            <span class="btn-text">+24h</span>
          </button>

          <button
            class="step-btn incident-btn"
            title="触发突发事件 (自主构思或自定义输入)"
            :disabled="worldStore.isTicking"
            @click="isIncidentModalOpen = true"
          >
            <Icon icon="material-symbols:crisis-alert" class="btn-symbol incident-icon" />
            <span class="btn-text incident-text">突发事件</span>
          </button>
        </div>
      </div>

      <!-- 右侧：功能菜单组 (提示词、世界书、设置、重置) -->
      <div class="nav-section-right">
        <!-- 移动端专用的看板呼出按钮 (PC 桌面端常驻，故隐藏此按钮) -->
        <button
          class="icon-action-btn neu-flat-sm show-mobile-only-btn"
          title="查看角色即时看板"
          @click="isMobileRightDrawerOpen = true"
        >
          <Icon icon="material-symbols:vital-signs" class="nav-icon" />
          <span>看板</span>
        </button>

        <!-- 文风与提示词按钮 -->
        <button
          class="icon-action-btn neu-flat-sm"
          title="配置叙事文风、文学技法与字数篇幅"
          @click="isPromptModalOpen = true"
        >
          <Icon icon="material-symbols:style" class="nav-icon" />
          <span class="btn-label-desktop">文风与设定</span>
        </button>

        <!-- 世界书按钮 -->
        <button
          class="icon-action-btn neu-flat-sm"
          title="查看与管理世界书条目"
          @click="isLoreModalOpen = true"
        >
          <Icon icon="material-symbols:menu-book" class="nav-icon" />
          <span class="btn-label-desktop">世界书</span>
        </button>

        <!-- API 与系统设置 -->
        <button
          class="icon-action-btn neu-flat-sm"
          title="模型接口与运行设置"
          @click="isConfigModalOpen = true"
        >
          <Icon icon="material-symbols:settings" class="nav-icon" />
          <span class="btn-label-desktop">设置</span>
        </button>

        <!-- 重置推演历程 -->
        <button
          class="icon-action-btn neu-flat-sm btn-danger-action"
          title="重置当前世界"
          :disabled="worldStore.isTicking"
          @click="handleReset"
        >
          <Icon icon="material-symbols:restart-alt" class="nav-icon" />
        </button>
      </div>
    </header>

    <!-- 异常警告横幅 -->
    <div v-if="worldStore.error" class="error-indicator-banner neu-flat-sm">
      <div class="error-left">
        <Icon icon="material-symbols:error" class="error-icon" />
        <span>{{ worldStore.error }}</span>
      </div>
      <button class="error-close-btn" @click="worldStore.error = null">
        <Icon icon="material-symbols:close" />
      </button>
    </div>

    <!-- ======================================================== -->
    <!-- 2. 主页面三栏结构 (左侧菜单 + 中间小说长卷 + 右侧常驻看板) -->
    <!-- ======================================================== -->
    <div class="workspace-container">
      <!-- 移动端抽屉遮罩 (Backdrop) -->
      <div
        v-if="isLeftDrawerOpenMobile || isMobileRightDrawerOpen"
        class="mobile-drawer-backdrop"
        @click="closeAllDrawers"
      />

      <!-- A. 左侧抽屉 / 侧边栏 (角色菜单 + 故事编年索引) -->
      <aside
        :class="[
          'left-drawer-panel',
          'neu-flat',
          { 'is-open': isLeftDrawerOpen, 'is-closed': !isLeftDrawerOpen, 'mobile-open': isLeftDrawerOpenMobile }
        ]"
      >
        <div class="drawer-header-bar">
          <span class="drawer-header-title">
            <Icon icon="material-symbols:menu" class="header-icon" />
            导航与角色列表
          </span>
          <button class="drawer-close-btn" @click="closeLeftDrawer">
            <Icon icon="material-symbols:close" />
          </button>
        </div>

        <CharacterDrawer
          ref="characterDrawerRef"
          :characters="worldStore.characters"
          :current-character-id="worldStore.currentCharacterId"
          :timeline="worldStore.timeline"
          @select-character="handleSelectCharacter"
          @delete-character="handleDeleteCharacter"
          @select-tick="scrollToTick"
          @open-quick="isQuickModalOpen = true"
          @open-import="isImportModalOpen = true"
        />
      </aside>

      <!-- B. 中间核心：场景小说长卷阅读流 (Novel Timeline Stream) -->
      <main class="center-novel-stream">
        <!-- 始终常驻在顶部的演化长卷标头与微光阅读进度条 -->
        <div class="stream-top-bar neu-flat-sm">
          <div class="stream-title-group">
            <Icon icon="material-symbols:auto-stories" class="book-icon" />
            <h1 class="stream-heading">
              {{ worldStore.currentDetail?.name || '虚拟世界' }} · 演化长卷
            </h1>
          </div>
          <div class="stream-meta-group">
            <span class="counter-badge">
              累计 {{ worldStore.timeline.length }} 刻故事切片
            </span>
          </div>
          <!-- 极简沉浸式阅读进度微光指示槽 (始终常驻顶部，随长卷向下滚动平滑生长) -->
          <div class="read-progress-track" title="阅读进度">
            <div class="read-progress-fill" :style="{ width: `${readProgress}%` }" />
          </div>
        </div>

        <!-- 小说正文切片可滚动长卷流 (独立视口) -->
        <div
          v-if="worldStore.timeline.length || worldStore.streamingLog"
          class="stream-scroll-viewport"
          ref="centerStreamRef"
          @scroll="handleStreamScroll"
        >
          <div class="stream-card-list">
            <div
              v-for="(log, idx) in worldStore.timeline"
              :key="log.id"
              :id="`log-${log.id}`"
              class="log-anchor-wrapper"
            >
              <TimelineLogItem
                :log="log"
                :is-latest="idx === worldStore.timeline.length - 1 && !worldStore.streamingLog"
              />
            </div>

            <!-- 实时流式切片卡片 -->
            <div
              v-if="worldStore.streamingLog"
              id="log-streaming"
              class="log-anchor-wrapper"
            >
              <TimelineLogItem
                :log="worldStore.streamingLog"
                :is-latest="true"
                :is-streaming="true"
              />
            </div>
          </div>
        </div>

        <!-- 空白占位提示 -->
        <div v-else class="empty-world-view neu-card neu-flat">
          <Icon icon="material-symbols:menu-book" class="empty-big-icon" />
          <h2 class="empty-title">当前世界尚未记录任何故事切片</h2>
          <p class="empty-desc">
            点击上方导航条的 <strong>[+1h]</strong> 或 <strong>[突发事件]</strong> 按钮，开启虚拟角色的自主推演历程。
          </p>
        </div>
      </main>

      <!-- C. 右侧：常驻角色 Living State 看板 (Permanent Dashboard) -->
      <aside
        :class="[
          'right-drawer-panel',
          'neu-flat',
          { 'mobile-open': isMobileRightDrawerOpen }
        ]"
      >
        <div class="dashboard-header-bar neu-inset-sm">
          <div class="dashboard-header-title">
            <Icon icon="material-symbols:vital-signs" class="header-icon" />
            <span>角色即时看板</span>
          </div>
          <div class="dashboard-header-right">
            <span class="char-pill">{{ worldStore.currentDetail?.name || '未选定' }}</span>
          </div>
        </div>

        <!-- 常驻显示 LivingStateSheet，不再需要多标签切换与折叠关闭 -->
        <div class="right-panel-body">
          <LivingStateSheet
            :character="worldStore.currentDetail"
            :state="worldStore.currentState"
          />
        </div>
      </aside>
    </div>

    <!-- ======================================================== -->
    <!-- 3. 移动端浮动底部推演控制栏 (移动端拇指友好，纯按钮交互) -->
    <!-- ======================================================== -->
    <div class="mobile-bottom-bar neu-flat show-mobile-only">
      <button
        class="mobile-bottom-btn continue-accent"
        :disabled="worldStore.isTicking"
        @click="worldStore.runContinue()"
      >
        <Icon icon="material-symbols:auto-stories" />
        <span>续写</span>
      </button>

      <button
        class="mobile-bottom-btn"
        :disabled="worldStore.isTicking"
        @click="worldStore.runStep(1)"
      >
        <Icon icon="line-md:chevron-right" />
        <span>+1h</span>
      </button>

      <button
        class="mobile-bottom-btn"
        :disabled="worldStore.isTicking"
        @click="worldStore.runFastForward('hour_6')"
      >
        <Icon icon="line-md:chevron-double-right" />
        <span>+6h</span>
      </button>

      <button
        class="mobile-bottom-btn"
        :disabled="worldStore.isTicking"
        @click="worldStore.runFastForward('day_1')"
      >
        <Icon icon="line-md:chevron-triple-right" />
        <span>+24h</span>
      </button>

      <button
        class="mobile-bottom-btn incident-accent"
        :disabled="worldStore.isTicking"
        @click="isIncidentModalOpen = true"
      >
        <Icon icon="material-symbols:crisis-alert" />
        <span>突发</span>
      </button>

      <button
        class="mobile-bottom-btn"
        @click="isMobileRightDrawerOpen = true"
      >
        <Icon icon="material-symbols:vital-signs" />
        <span>看板</span>
      </button>
    </div>

    <!-- ======================================================== -->
    <!-- 4. 全局模态控制弹窗系统 (Modals)                          -->
    <!-- ======================================================== -->
    <!-- 突发事件触发与自定义配置弹窗 -->
    <IncidentTriggerModal
      :is-open="isIncidentModalOpen"
      @close="isIncidentModalOpen = false"
      @confirm="handleIncidentConfirm"
    />

    <!-- 提示词配置模态弹窗 -->
    <PromptEditorModal
      :is-open="isPromptModalOpen"
      @close="isPromptModalOpen = false"
    />

    <!-- 世界书管理模态弹窗 -->
    <WorldLoreModal
      :is-open="isLoreModalOpen"
      :character-id="worldStore.currentCharacterId"
      @close="isLoreModalOpen = false"
    />

    <!-- API 与引擎配置模态弹窗 -->
    <SystemConfigModal
      :is-open="isConfigModalOpen"
      @close="isConfigModalOpen = false"
    />

    <!-- 角色新建与导入弹窗 -->
    <QuickCharacterModal
      :is-open="isQuickModalOpen"
      @close="isQuickModalOpen = false"
      @blueprint="handleQuickBlueprint"
    />

    <CardImportModal
      :is-open="isImportModalOpen"
      :initial-parse-data="quickBlueprintData"
      @close="handleImportModalClose"
      @imported="handleCharacterCreated"
      @back-to-quick="handleBackToQuick"
    />

    <!-- 新拟态全局 Toast 消息通知 -->
    <NeuToast />

    <!-- 新拟态全局 Confirm 操作确认弹窗 -->
    <NeuConfirmModal />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import { Icon } from '@iconify/vue'
import TimelineLogItem from './components/TimelineLogItem.vue'
import LivingStateSheet from './components/LivingStateSheet.vue'
import CharacterDrawer from './components/CharacterDrawer.vue'
import PromptEditorModal from './components/PromptEditorModal.vue'
import WorldLoreModal from './components/WorldLoreModal.vue'
import SystemConfigModal from './components/SystemConfigModal.vue'
import QuickCharacterModal from './components/QuickCharacterModal.vue'
import CardImportModal from './components/CardImportModal.vue'
import IncidentTriggerModal from './components/IncidentTriggerModal.vue'
import NeuToast from './components/NeuToast.vue'
import NeuConfirmModal from './components/NeuConfirmModal.vue'
import { useWorldStore } from './stores/world'
import { useConfirm } from './composables/useConfirm'
import { useToast } from './composables/useToast'
import type { CardParseResponse } from './api/client'

const worldStore = useWorldStore()
const { confirm } = useConfirm()
const toast = useToast()

// 抽屉与模态状态
const centerStreamRef = ref<HTMLElement | null>(null)
const isLeftDrawerOpen = ref(window.innerWidth >= 1280) // 桌面宽屏默认打开左侧
const isLeftDrawerOpenMobile = ref(false)               // 移动端左侧抽屉开关
const isMobileRightDrawerOpen = ref(false)              // 移动端右侧看板开关

// 模态弹窗状态
const isPromptModalOpen = ref(false)
const isLoreModalOpen = ref(false)
const isConfigModalOpen = ref(false)
const isQuickModalOpen = ref(false)
const isImportModalOpen = ref(false)
const isIncidentModalOpen = ref(false)
const quickBlueprintData = ref<CardParseResponse | null>(null)

const handleQuickBlueprint = (blueprint: CardParseResponse) => {
  isQuickModalOpen.value = false
  quickBlueprintData.value = blueprint
  isImportModalOpen.value = true
}

const handleImportModalClose = () => {
  isImportModalOpen.value = false
  quickBlueprintData.value = null
}

const handleBackToQuick = () => {
  isImportModalOpen.value = false
  quickBlueprintData.value = null
  isQuickModalOpen.value = true
}

const handleIncidentConfirm = (incidentDescription?: string) => {
  isIncidentModalOpen.value = false
  worldStore.triggerIncident(incidentDescription)
}

onMounted(async () => {
  await worldStore.initialize()
  scrollToBottom()
})

const toggleLeftDrawer = () => {
  if (window.innerWidth < 1024) {
    isLeftDrawerOpenMobile.value = !isLeftDrawerOpenMobile.value
  } else {
    isLeftDrawerOpen.value = !isLeftDrawerOpen.value
  }
}

const closeLeftDrawer = () => {
  if (window.innerWidth < 1024) {
    isLeftDrawerOpenMobile.value = false
  } else {
    isLeftDrawerOpen.value = false
  }
}

const closeAllDrawers = () => {
  isLeftDrawerOpenMobile.value = false
  isMobileRightDrawerOpen.value = false
}

const readProgress = ref(0)

const handleStreamScroll = (e: Event) => {
  const el = e.target as HTMLElement
  if (!el) return
  const maxScroll = el.scrollHeight - el.clientHeight
  if (maxScroll <= 0) {
    readProgress.value = 100
  } else {
    readProgress.value = Math.min(100, Math.max(0, Math.round((el.scrollTop / maxScroll) * 100)))
  }
}

const scrollToBottom = () => {
  nextTick(() => {
    if (centerStreamRef.value) {
      centerStreamRef.value.scrollTo({
        top: centerStreamRef.value.scrollHeight,
        behavior: 'smooth',
      })
      readProgress.value = 100
    }
    window.scrollTo({
      top: document.body.scrollHeight,
      behavior: 'smooth',
    })
  })
}

const scrollToTick = (logId: number) => {
  nextTick(() => {
    const el = document.getElementById(`log-${logId}`)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  })
}

watch(
  () => worldStore.timeline.length,
  () => {
    scrollToBottom()
  }
)

watch(
  () => worldStore.streamingLog,
  (val) => {
    if (val) {
      scrollToBottom()
    }
  }
)

watch(
  () => worldStore.streamingLog?.narrative_prose,
  () => {
    scrollToBottom()
  }
)

const handleSelectCharacter = async (charId: string) => {
  await worldStore.selectCharacter(charId)
  if (window.innerWidth < 1024) {
    isLeftDrawerOpenMobile.value = false
  }
}

const handleCharacterCreated = async (characterId: string) => {
  isQuickModalOpen.value = false
  isImportModalOpen.value = false
  quickBlueprintData.value = null
  await worldStore.initialize()
  await worldStore.selectCharacter(characterId)
}

const handleDeleteCharacter = async (char: any) => {
  const confirmed = await confirm({
    title: '彻底删除角色',
    message: `确定要彻底删除角色【${char.name}】吗？\n\n该操作将永久删除此角色的全部推演故事切片、即时机能状态、世界书专属法则与关系网，不可恢复！`,
    confirmText: '彻底删除',
    cancelText: '取消',
    variant: 'danger',
    icon: 'material-symbols:delete-forever',
  })
  if (confirmed) {
    await worldStore.deleteCharacter(char.id)
    toast.showSuccess('角色已删除', `角色【${char.name}】及其全部数据已彻底清理。`)
  }
}

const handleReset = async () => {
  const confirmed = await confirm({
    title: '重置推演世界',
    message: '确定要重置当前角色的推演世界吗？历史小说切片将被清空，状态回滚至开局处境。',
    confirmText: '重置世界',
    cancelText: '取消',
    variant: 'warning',
    icon: 'material-symbols:restart-alt',
  })
  if (confirmed) {
    await worldStore.resetWorld()
    toast.showSuccess('世界已重置', '推演长卷与即时状态已回滚至初始世界。')
  }
}
</script>

<style scoped>
.world-app {
  height: 100vh;
  max-height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background-color: var(--neu-bg);
  padding-bottom: 0;
}

/* ========================================= */
/* 1. 顶部导航条 (Top Navigation Bar)        */
/* ========================================= */
.top-nav-bar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.55rem 1.25rem;
  position: sticky;
  top: 0;
  z-index: 50;
  backdrop-filter: blur(10px);
  gap: 0.75rem;
  border-radius: 0 0 16px 16px;
}

.nav-section-left,
.nav-section-center,
.nav-section-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.icon-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.45rem 0.65rem;
  border: none;
  background: var(--neu-surface);
  color: var(--neu-text-primary);
  border-radius: 10px;
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 500;
  user-select: none;
  transition: all 0.2s;
}

.icon-action-btn:hover {
  color: var(--neu-accent);
}

.icon-action-btn.is-active {
  color: var(--neu-accent);
  box-shadow: var(--shadow-active);
}

.btn-danger-action:hover {
  color: var(--neu-danger);
}

.nav-icon {
  font-size: 1.25rem;
  flex-shrink: 0;
}

.btn-label-desktop {
  font-size: 0.8rem;
  font-weight: 600;
}

.world-clock-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.45rem 0.75rem;
  font-weight: 700;
  font-size: 0.85rem;
  color: var(--neu-text-primary);
  white-space: nowrap;
}

.clock-icon {
  color: var(--neu-accent);
  font-size: 1.15rem;
}

.state-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.45rem 0.65rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--neu-text-secondary);
  white-space: nowrap;
}

.state-icon {
  font-size: 1rem;
  color: var(--neu-accent);
}

.pulse-anim {
  color: var(--neu-accent);
  animation: pulse-glow 2s infinite ease-in-out;
}

@keyframes pulse-glow {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}

/* 核心推演按钮组 (新拟态内凹槽与高触感物理按键体系) */
.stepper-controls {
  display: inline-flex;
  align-items: center;
  padding: 0.3rem;
  gap: 0.35rem;
  border-radius: 12px;
}

.step-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.42rem 0.75rem;
  border: none;
  background: var(--neu-surface);
  color: var(--neu-text-primary);
  font-size: 0.825rem;
  font-weight: 600;
  border-radius: 9px;
  cursor: pointer;
  box-shadow: var(--shadow-flat-sm);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  white-space: nowrap;
  user-select: none;
  outline: none;
}

.step-btn:hover:not(:disabled) {
  box-shadow: var(--shadow-hover);
  color: var(--neu-accent);
  transform: translateY(-1px);
}

.step-btn:active:not(:disabled) {
  box-shadow: var(--shadow-active);
  transform: translateY(0.5px);
}

.step-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none !important;
  box-shadow: var(--shadow-flat-sm) !important;
}

.btn-symbol {
  font-size: 1.1rem;
}

/* 智能续写：主推演物理按键，微拟态光感浮雕与微弧切面 */
.continue-btn {
  background: linear-gradient(
    135deg,
    rgba(var(--neu-accent-rgb, 94, 114, 228), 0.12) 0%,
    rgba(var(--neu-accent-rgb, 94, 114, 228), 0.02) 55%,
    var(--neu-surface) 100%
  );
  color: var(--neu-accent);
  border: none;
  box-shadow:
    var(--shadow-flat-sm),
    inset 1px 1px 1.5px var(--neu-light),
    inset -1px -1px 1.5px rgba(0, 0, 0, 0.04);
  position: relative;
}

.continue-btn:hover:not(:disabled) {
  background: linear-gradient(
    135deg,
    rgba(var(--neu-accent-rgb, 94, 114, 228), 0.18) 0%,
    rgba(var(--neu-accent-rgb, 94, 114, 228), 0.05) 60%,
    var(--neu-surface) 100%
  );
  color: var(--neu-accent-hover);
  border-color: rgba(var(--neu-accent-rgb, 94, 114, 228), 0.55);
  box-shadow:
    var(--shadow-hover),
    0 0 12px rgba(var(--neu-accent-rgb, 94, 114, 228), 0.22),
    inset 1px 1px 2px var(--neu-light);
  transform: translateY(-1.5px);
}

.continue-btn:active:not(:disabled) {
  box-shadow:
    var(--shadow-active),
    inset 1px 1px 3px rgba(var(--neu-accent-rgb, 94, 114, 228), 0.2);
  transform: translateY(0.5px);
}

.continue-icon {
  color: var(--neu-accent);
  filter: drop-shadow(0 1px 1.5px rgba(var(--neu-accent-rgb, 94, 114, 228), 0.3));
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.continue-btn:hover:not(:disabled) .continue-icon {
  transform: scale(1.1) rotate(-4deg);
}

.continue-text {
  font-weight: 700;
  letter-spacing: 0.02em;
}

/* 突发事件：变数干预高能按键，立体现拟态光泽与双向光影 */
.incident-btn {
  background: linear-gradient(
    145deg,
    rgba(255, 255, 255, 0.24) 0%,
    rgba(255, 255, 255, 0.04) 40%,
    rgba(0, 0, 0, 0.12) 100%
  ), var(--neu-accent);
  color: #ffffff;
  border: none;
  box-shadow:
    var(--shadow-flat-sm),
    0 2px 8px rgba(var(--neu-accent-rgb, 94, 114, 228), 0.35),
    inset 1px 1px 1.5px rgba(255, 255, 255, 0.45),
    inset -1px -1px 2px rgba(0, 0, 0, 0.22);
  position: relative;
}

.incident-btn:hover:not(:disabled) {
  background: linear-gradient(
    145deg,
    rgba(255, 255, 255, 0.32) 0%,
    rgba(255, 255, 255, 0.08) 40%,
    rgba(0, 0, 0, 0.15) 100%
  ), var(--neu-accent-hover);
  color: #ffffff;
  border-color: rgba(255, 255, 255, 0.38);
  box-shadow:
    var(--shadow-hover),
    0 4px 16px rgba(var(--neu-accent-rgb, 94, 114, 228), 0.48),
    inset 1px 1px 2px rgba(255, 255, 255, 0.55);
  transform: translateY(-1.5px);
}

.incident-btn:active:not(:disabled) {
  box-shadow:
    var(--shadow-active),
    inset 2px 2px 5px rgba(0, 0, 0, 0.32),
    inset -1px -1px 2px rgba(255, 255, 255, 0.15);
  transform: translateY(0.5px);
}

.incident-icon {
  color: #ffffff;
  filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.3));
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.incident-btn:hover:not(:disabled) .incident-icon {
  transform: scale(1.12);
}

.incident-text {
  font-weight: 700;
  letter-spacing: 0.02em;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.25);
}

/* 深色模式下的微调 */
[data-theme="dark"] .continue-btn {
  background: linear-gradient(
    135deg,
    rgba(var(--neu-accent-rgb, 94, 114, 228), 0.16) 0%,
    rgba(var(--neu-accent-rgb, 94, 114, 228), 0.04) 60%,
    var(--neu-surface) 100%
  );
  border-color: rgba(var(--neu-accent-rgb, 94, 114, 228), 0.36);
}

[data-theme="dark"] .incident-btn {
  border-color: rgba(255, 255, 255, 0.15);
  box-shadow:
    var(--shadow-flat-sm),
    0 2px 10px rgba(var(--neu-accent-rgb, 94, 114, 228), 0.45),
    inset 1px 1px 1.5px rgba(255, 255, 255, 0.3),
    inset -1px -1px 2px rgba(0, 0, 0, 0.45);
}

.spin-icon {
  animation: spin 1s linear infinite;
  font-size: 1.15rem;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.error-indicator-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.65rem 1rem;
  margin: 0.5rem 1rem 0;
  color: var(--neu-danger);
  font-size: 0.825rem;
}

.error-left {
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.error-icon {
  font-size: 1.15rem;
}

.error-close-btn {
  background: none;
  border: none;
  color: var(--neu-danger);
  cursor: pointer;
}

/* ========================================= */
/* 2. 工作区三栏布局 (Workspace Layout)       */
/* ========================================= */
.workspace-container {
  display: flex;
  flex: 1;
  min-height: 0;
  gap: 1.25rem;
  padding: 0.75rem 1.25rem;
  width: 100%;
  position: relative;
  overflow: hidden;
}

/* A. 左侧抽屉 (Left Drawer) */
.left-drawer-panel {
  width: 310px;
  flex-shrink: 0;
  height: 100%;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.left-drawer-panel.is-closed {
  display: none;
}

/* B. 中间小说正文流 (Center Novel Stream) */
.center-novel-stream {
  flex: 1;
  min-width: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  overflow: hidden;
}

.stream-top-bar {
  position: relative;
  overflow: hidden;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1.25rem;
  flex-shrink: 0;
  z-index: 10;
}

/* 小说正文切片独立滚动长卷视口 */
.stream-scroll-viewport {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  scrollbar-width: none; /* Firefox: 彻底隐藏外部悬空滚动条 */
  -ms-overflow-style: none; /* IE / Edge */
}

.stream-scroll-viewport::-webkit-scrollbar {
  display: none; /* Chrome, Safari, Edge WebKit: 彻底隐藏外部悬空滚动条 */
  width: 0;
  height: 0;
}

/* 顶部沉浸式极细阅读进度微光指示槽 (替代外部悬空滚动条) */
.read-progress-track {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2.5px;
  background: var(--neu-border);
  pointer-events: none;
}

.read-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--neu-accent) 0%, var(--neu-accent-hover) 100%);
  box-shadow: 0 0 6px var(--neu-accent);
  transition: width 0.15s ease-out;
  border-radius: 0 2px 2px 0;
}

.stream-title-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.book-icon {
  font-size: 1.35rem;
  color: var(--neu-accent);
}

.stream-heading {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--neu-text-primary);
}

.counter-badge {
  font-size: 0.775rem;
  color: var(--neu-text-secondary);
}

.stream-card-list {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  padding-bottom: 2rem;
}

.empty-world-view {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4.5rem 2rem;
  gap: 1rem;
  text-align: center;
  color: var(--neu-text-muted);
}

.empty-big-icon {
  font-size: 4rem;
  color: var(--neu-dark);
}

.empty-title {
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--neu-text-primary);
}

.empty-desc {
  font-size: 0.85rem;
  color: var(--neu-text-secondary);
  max-width: 450px;
  line-height: 1.6;
}

/* C. 右侧常驻看板 (Permanent Right Dashboard) */
.right-drawer-panel {
  width: 380px;
  flex-shrink: 0;
  height: 100%;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.dashboard-header-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0.75rem;
  border-radius: 10px;
}

.dashboard-header-title {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--neu-text-primary);
}

.dashboard-header-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.char-pill {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--neu-accent);
}

.show-mobile-flex {
  display: none;
}

.show-mobile-only-btn {
  display: none;
}

.drawer-header-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid rgba(196, 201, 212, 0.3);
}

.drawer-header-title {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--neu-text-primary);
}

.header-icon {
  font-size: 1.1rem;
  color: var(--neu-accent);
}

.drawer-close-btn {
  background: none;
  border: none;
  font-size: 1.25rem;
  color: var(--neu-text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
}

.right-panel-body {
  display: flex;
  flex-direction: column;
}

/* ========================================= */
/* 3. 移动端专属浮动控制栏 (Mobile Controls) */
/* ========================================= */
.mobile-bottom-bar {
  display: none;
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 60;
  padding: 0.5rem 1rem;
  justify-content: space-around;
  border-radius: 16px 16px 0 0;
  backdrop-filter: blur(10px);
}

.mobile-bottom-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.2rem;
  padding: 0.35rem 0.85rem;
  border: none;
  background: transparent;
  color: var(--neu-text-primary);
  font-size: 0.725rem;
  font-weight: 600;
  cursor: pointer;
}

.mobile-bottom-btn.continue-accent {
  color: var(--neu-accent);
  border-radius: 10px;
  background: linear-gradient(
    135deg,
    rgba(var(--neu-accent-rgb, 94, 114, 228), 0.12) 0%,
    rgba(var(--neu-accent-rgb, 94, 114, 228), 0.02) 100%
  ), var(--neu-surface);
  box-shadow: var(--shadow-flat-sm);
  border: 1px solid rgba(var(--neu-accent-rgb, 94, 114, 228), 0.25);
}

.mobile-bottom-btn.incident-accent {
  color: #ffffff;
  border-radius: 10px;
  background: linear-gradient(
    145deg,
    rgba(255, 255, 255, 0.22) 0%,
    rgba(0, 0, 0, 0.1) 100%
  ), var(--neu-accent);
  box-shadow:
    var(--shadow-flat-sm),
    0 2px 8px rgba(var(--neu-accent-rgb, 94, 114, 228), 0.35);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.mobile-drawer-backdrop {
  display: none;
}

/* ========================================= */
/* 4. 响应式断点适配 (Mobile & Tablet)      */
/* ========================================= */
@media (max-width: 1280px) {
  .left-drawer-panel {
    width: 280px;
  }
  .right-drawer-panel {
    width: 350px;
  }
}

@media (max-width: 1024px) {
  .btn-label-desktop {
    display: none;
  }
  .hide-mobile {
    display: none !important;
  }
  .show-mobile-only-btn {
    display: inline-flex;
  }
  .show-mobile-flex {
    display: flex;
  }

  /* 移动端抽屉遮罩 */
  .mobile-drawer-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(30, 41, 59, 0.45);
    backdrop-filter: blur(4px);
    z-index: 80;
  }

  /* 左侧抽屉在移动端默认滑出在屏幕左外侧 */
  .left-drawer-panel {
    position: fixed;
    top: 0;
    bottom: 0;
    left: 0;
    width: 82vw;
    max-width: 340px;
    height: 100vh;
    z-index: 90;
    box-shadow: 10px 0 30px rgba(0, 0, 0, 0.2);
    border-radius: 0 16px 16px 0;
    transform: translateX(-105%);
    transition: transform 0.3s ease;
    display: flex !important;
  }

  .left-drawer-panel.mobile-open {
    transform: translateX(0);
  }

  /* 右侧看板在移动端默认收在右侧外，点击后滑出 */
  .right-drawer-panel {
    position: fixed;
    top: 0;
    bottom: 0;
    right: 0;
    width: 88vw;
    max-width: 420px;
    height: 100vh;
    z-index: 90;
    box-shadow: -10px 0 30px rgba(0, 0, 0, 0.2);
    border-radius: 16px 0 0 16px;
    transform: translateX(105%);
    transition: transform 0.3s ease;
  }

  .right-drawer-panel.mobile-open {
    transform: translateX(0);
  }

  .show-mobile-only {
    display: flex;
  }

  .world-app {
    height: auto;
    max-height: none;
    min-height: 100vh;
    overflow: visible;
    padding-bottom: 5rem;
  }

  .workspace-container {
    height: auto;
    overflow: visible;
    padding: 0.75rem 0.5rem;
  }

  .center-novel-stream {
    height: auto;
    overflow: visible;
    padding-right: 0;
  }

  .stream-scroll-viewport {
    height: auto;
    overflow: visible;
  }

  .nav-section-center {
    display: none; /* 移动端在顶部隐藏步进组，移至底部大拇指栏 */
  }
}

@media (max-width: 640px) {
  .top-nav-bar {
    padding: 0.5rem 0.75rem;
  }
  .world-clock-badge {
    padding: 0.35rem 0.55rem;
    font-size: 0.75rem;
  }
  .clock-icon {
    font-size: 1rem;
  }
  .icon-action-btn {
    padding: 0.4rem 0.5rem;
  }
  .nav-icon {
    font-size: 1.15rem;
  }
}
</style>
