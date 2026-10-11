<template>
  <div class="system-config-panel">

    <!-- 运行状态横幅详细信息与说明 -->
    <div class="status-summary neu-flat-sm">
      <span class="panel-desc">
        调整模型接口、个性化界面色彩与推演运行期参数。配置保存后自动持久化。
      </span>
    </div>

    <form class="config-form" @submit.prevent="handleSave">
      <!-- ============================================== -->
      <!-- 1. 界面外观与个性化主题 (首位呈现，全屏实时响应) -->
      <!-- ============================================== -->
      <div class="theme-config-section neu-flat-sm">
        <div class="section-title-row">
          <div class="section-title-left">
            <Icon icon="material-symbols:palette" class="section-title-icon" />
            <span class="section-title-text">界面外观与主题色彩</span>
          </div>
        </div>

        <!-- 色彩模式切换 (浅色 / 深色 / 跟随系统) -->
        <div class="theme-control-group">
          <label class="control-label">
            <Icon icon="material-symbols:contrast" class="label-icon" />
            色彩模式
          </label>
          <div class="mode-segmented-control neu-inset-sm">
            <button
              type="button"
              class="mode-seg-btn"
              :class="{ 'is-active': themeMode === 'light' }"
              @click="handleSelectMode('light')"
              title="切换为柔和浅色模式"
            >
              <Icon icon="material-symbols:light-mode" class="mode-icon" />
              <span>浅色</span>
            </button>
            <button
              type="button"
              class="mode-seg-btn"
              :class="{ 'is-active': themeMode === 'dark' }"
              @click="handleSelectMode('dark')"
              title="切换为沉浸深色模式"
            >
              <Icon icon="material-symbols:dark-mode" class="mode-icon" />
              <span>深色</span>
            </button>
            <button
              type="button"
              class="mode-seg-btn"
              :class="{ 'is-active': themeMode === 'auto' }"
              @click="handleSelectMode('auto')"
              title="根据操作系统设置自动适配"
            >
              <Icon icon="material-symbols:settings-brightness" class="mode-icon" />
              <span>跟随系统</span>
            </button>
          </div>
        </div>

        <!-- 主题强调色 (Preset 色彩 + 自定义选择) -->
        <div class="theme-control-group">
          <div class="color-label-row">
            <label class="control-label">
              <Icon icon="material-symbols:format-paint" class="label-icon" />
              主题强调色
            </label>
            <span class="active-color-badge">{{ currentColorName }}</span>
          </div>

          <div class="color-palette-bar">
            <div class="presets-row">
              <button
                v-for="preset in presets"
                :key="preset.id"
                type="button"
                class="color-dot-btn"
                :class="{ 'is-selected': isColorActive(preset.color) }"
                :style="{ backgroundColor: preset.color }"
                :title="preset.name"
                @click="handleSelectColor(preset.color)"
              >
                <Icon
                  v-if="isColorActive(preset.color)"
                  icon="material-symbols:check"
                  class="check-icon"
                />
              </button>
            </div>

            <!-- 自定义颜色拾取器 -->
            <div class="custom-color-wrapper">
              <label
                class="custom-color-btn neu-flat-sm neu-hover"
                :class="{ 'is-active': isCustomColorActive }"
                title="选择自定义十六进制颜色"
              >
                <span
                  class="custom-dot-preview"
                  :style="{ backgroundColor: themeColor }"
                />
                <span class="custom-color-text">自定义</span>
                <Icon icon="material-symbols:colorize" class="picker-icon" />
                <input
                  type="color"
                  class="hidden-color-input"
                  :value="themeColor"
                  @input="handleCustomColorInput"
                />
              </label>
            </div>
          </div>
        </div>
      </div>

      <!-- ============================================== -->
      <!-- 2. LLM Base URL (接口地址)                     -->
      <!-- ============================================== -->
      <div class="form-group">
        <label>
          <Icon icon="material-symbols:link" class="label-icon" />
          LLM Base URL (接口地址)
        </label>
        <input
          v-model="form.llm_base_url"
          class="neu-input neu-inset-sm"
          placeholder="https://api.openai.com/v1"
          required
        />
      </div>

      <!-- ============================================== -->
      <!-- 3. LLM API Key (API 密钥)                      -->
      <!-- ============================================== -->
      <div class="form-group">
        <label>
          <Icon icon="material-symbols:key" class="label-icon" />
          API 密钥 (API Key)
        </label>
        <div class="input-with-action">
          <input
            :type="showKey ? 'text' : 'password'"
            v-model="form.llm_api_key"
            class="neu-input neu-inset-sm"
            :placeholder="config.api_key_masked || 'sk-xxxxxxxxxxxxxxxx'"
          />
          <button
            type="button"
            class="toggle-eye-btn"
            @click="showKey = !showKey"
            title="显示/隐藏"
          >
            <Icon :icon="showKey ? 'material-symbols:visibility-off' : 'material-symbols:visibility'" />
          </button>
        </div>
        <span class="form-hint" v-if="config.api_key_masked && !form.llm_api_key">
          已存: {{ config.api_key_masked }}（保持留空则不更改）
        </span>
      </div>

      <!-- ============================================== -->
      <!-- 4. 拉取模型操作条                              -->
      <!-- ============================================== -->
      <div class="fetch-action-row neu-inset-sm">
        <div class="fetch-info">
          <span class="fetch-title">
            <Icon icon="material-symbols:smart-toy" class="fetch-icon" />
            模型探测
          </span>
          <span class="fetch-status" :class="{ 'status-ok': fetchSuccess, 'status-error': fetchError }">
            {{ fetchStatusText }}
          </span>
        </div>
        <NeuButton
          type="button"
          icon="material-symbols:cloud-download"
          label="拉取模型"
          variant="normal"
          :loading="isFetchingModels"
          @click="handleFetchModels"
        />
      </div>

      <!-- ============================================== -->
      <!-- 5. 推演模型选择                                -->
      <!-- ============================================== -->
      <div class="form-group">
        <label>
          <Icon icon="material-symbols:psychology" class="label-icon" />
          推演模型选择
        </label>
        <NeuSelect
          v-model="form.llm_model_name"
          :options="modelSelectOptions"
          placeholder="-- 请点击上方【拉取模型】选择 --"
          searchable
          icon="material-symbols:smart-toy"
        />
        <span class="form-hint">
          {{ modelsList.length > 0 ? `已获取 ${modelsList.length} 个可用模型` : '请点击上方按钮自动拉取支持的模型' }}
        </span>
      </div>

      <!-- ============================================== -->
      <!-- 6. 推演高级与采样参数 (可折叠防过长手风琴)         -->
      <!-- ============================================== -->
      <div class="collapsible-params-section">
        <button
          type="button"
          class="collapse-trigger-btn neu-flat-sm neu-hover"
          :class="{ 'is-open': isParamsExpanded }"
          @click="isParamsExpanded = !isParamsExpanded"
        >
          <div class="collapse-header-left">
            <Icon icon="material-symbols:tune" class="collapse-icon" />
            <div class="collapse-title-group">
              <span class="collapse-main-title">高级采样参数</span>
              <span class="collapse-summary-badge">{{ paramsSummaryText }}</span>
            </div>
          </div>

          <div class="collapse-header-right">
            <Icon
              icon="material-symbols:keyboard-arrow-down"
              class="chevron-icon"
              :class="{ 'is-expanded': isParamsExpanded }"
            />
          </div>
        </button>

        <!-- 折叠面板内容区 -->
        <Transition name="accordion-collapse">
          <div v-show="isParamsExpanded" class="collapsible-content-body neu-inset-sm">
            <!-- 上下文 Token 滑条 -->
            <div class="nested-slider-wrap">
              <NeuSlider
                v-model="form.llm_context_window"
                :min="512"
                :max="2000000"
                :step="512"
                label="上下文上限"
                unit="Tokens"
                icon="material-symbols:memory"
                hint="单次推演最大上下文"
              />
            </div>

            <!-- 采样参数网格 -->
            <div class="sampling-sliders-grid">
              <NeuSlider
                v-model="form.llm_temperature"
                :min="0.0"
                :max="2.0"
                :step="0.01"
                label="温度 (Temperature)"
                icon="material-symbols:thermostat"
                hint="控制输出随机性与文学想象力"
              />

              <NeuSlider
                v-model="form.llm_frequency_penalty"
                :min="-2.0"
                :max="2.0"
                :step="0.01"
                label="频率惩罚 (Frequency Penalty)"
                icon="material-symbols:repeat"
                hint="降低高频重复词概率"
              />

              <NeuSlider
                v-model="form.llm_presence_penalty"
                :min="-2.0"
                :max="2.0"
                :step="0.01"
                label="存在惩罚 (Presence Penalty)"
                icon="material-symbols:topic"
                hint="促使引入全新意象词汇"
              />

              <NeuSlider
                v-model="form.llm_top_p"
                :min="0.0"
                :max="1.0"
                :step="0.01"
                label="Top P 阈值"
                icon="material-symbols:filter-alt"
                hint="候选词累积概率阈值"
              />
            </div>
          </div>
        </Transition>
      </div>

      <!-- ============================================== -->
      <!-- 7. 现实时间同步自动演化开关与步长控制          -->
      <!-- ============================================== -->
      <div class="stream-toggle-row sync-toggle-box neu-inset-sm">
        <div class="sync-toggle-header">
          <div class="stream-info">
            <div class="stream-title">
              <Icon icon="material-symbols:timelapse" class="stream-icon" />
              <span>现实时间同步演化</span>
              <span
                class="sync-status-badge"
                :class="form.enable_realtime_sync ? 'badge-active' : 'badge-inactive'"
              >
                <Icon
                  :icon="form.enable_realtime_sync ? 'material-symbols:sync' : 'material-symbols:sync-disabled'"
                  class="badge-icon"
                />
                {{ form.enable_realtime_sync ? '演化中' : '已暂停' }}
              </span>
            </div>
            <span class="stream-hint">
              开启后后台按步长自动推进推演；关闭后仅手动步进时推演。
            </span>
          </div>
          <label class="toggle-switch">
            <input type="checkbox" v-model="form.enable_realtime_sync" />
            <span class="toggle-slider"></span>
          </label>
        </div>

        <!-- 演化步长配置行：开启时展开微调 -->
        <Transition name="accordion-collapse">
          <div v-show="form.enable_realtime_sync" class="sync-step-config neu-flat-sm">
            <div class="sync-step-label-group">
              <label class="sync-step-label">
                <Icon icon="material-symbols:nest-clock-farsight-analog" class="label-icon" />
                <span>同步周期</span>
              </label>
              <span class="sync-step-hint">每次推进折算时长 (1 ~ 24h)</span>
            </div>
            <div class="sync-step-input-wrap">
              <input
                type="number"
                v-model.number="form.realtime_tick_hours"
                min="1"
                max="24"
                class="neu-input neu-inset-sm sync-step-input"
                :required="form.enable_realtime_sync"
              />
              <span class="sync-unit-label">小时 / 次</span>
            </div>
          </div>
        </Transition>
      </div>

      <!-- ============================================== -->
      <!-- 8. 推演正文流式输出开关                        -->
      <!-- ============================================== -->
      <div class="stream-toggle-row neu-inset-sm">
        <div class="stream-info">
          <div class="stream-title">
            <Icon icon="material-symbols:stream" class="stream-icon" />
            <span>推演正文实时打字效果</span>
          </div>
          <span class="stream-hint">
            开启后正文实时以打字机呈现；关闭后生成完毕一次性展现。
          </span>
        </div>
        <label class="toggle-switch">
          <input type="checkbox" v-model="form.enable_stream_display" />
          <span class="toggle-slider"></span>
        </label>
      </div>

      <!-- ============================================== -->
      <!-- 9. 手机与社交网络交互拟真开关                  -->
      <!-- ============================================== -->
      <div class="stream-toggle-row neu-inset-sm">
        <div class="stream-info">
          <div class="stream-title">
            <Icon icon="material-symbols:phone-iphone" class="stream-icon" />
            <span>手机与社交拟真</span>
          </div>
          <span class="stream-hint">
            适宜情境下角色可使用手机收发即时消息、朋友圈或论坛。
          </span>
        </div>
        <label class="toggle-switch">
          <input type="checkbox" v-model="form.enable_phone_simulation" />
          <span class="toggle-slider"></span>
        </label>
      </div>

    </form>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { Icon } from '@iconify/vue'
import NeuButton from './NeuButton.vue'
import NeuSlider from './NeuSlider.vue'
import NeuSelect from './NeuSelect.vue'
import { apiClient } from '../api/client'
import { useToast } from '../composables/useToast'
import { useWorldStore } from '../stores/world'
import { useTheme, type ThemeMode } from '../composables/useTheme'

const emit = defineEmits<{
  (e: 'close'): void
}>()

const toast = useToast()
const worldStore = useWorldStore()
const { themeMode, themeColor, presets, setThemeMode, setThemeColor } = useTheme()

const config = ref<any>({})
const isSaving = ref(false)
const isFetchingModels = ref(false)
const showKey = ref(false)
const modelsList = ref<string[]>([])

// 参数调整折叠状态
const isParamsExpanded = ref(false)

const modelSelectOptions = computed(() => {
  const list = [...modelsList.value]
  if (form.llm_model_name && !list.includes(form.llm_model_name)) {
    return [
      { label: `${form.llm_model_name} (当前配置)`, value: form.llm_model_name, badge: '当前' },
      ...list.map((m) => ({ label: m, value: m })),
    ]
  }
  return list.map((m) => ({ label: m, value: m }))
})

const fetchStatusText = ref('点击探测可用模型')
const fetchSuccess = ref(false)
const fetchError = ref(false)

const form = reactive({
  llm_base_url: '',
  llm_api_key: '',
  llm_model_name: '',
  llm_context_window: 60000,
  llm_temperature: 1.0,
  llm_frequency_penalty: 0.0,
  llm_presence_penalty: 0.0,
  llm_top_p: 1.0,
  enable_realtime_sync: false,
  realtime_tick_hours: 1,
  enable_stream_display: true,
  enable_phone_simulation: false,
  theme_mode: 'light' as ThemeMode,
  theme_color: '#5e72e4',
})

// 参数摘要文本
const paramsSummaryText = computed(() => {
  const kTokens = Math.round(form.llm_context_window / 1024)
  return `温 ${form.llm_temperature.toFixed(2)} · P ${form.llm_top_p.toFixed(2)} · ${kTokens}k`
})

// 主题色彩相关计算与交互
const isColorActive = (color: string) => {
  return themeColor.value.toLowerCase() === color.toLowerCase()
}

const isCustomColorActive = computed(() => {
  return !presets.some((p) => p.color.toLowerCase() === themeColor.value.toLowerCase())
})

const currentColorName = computed(() => {
  const preset = presets.find((p) => p.color.toLowerCase() === themeColor.value.toLowerCase())
  return preset ? preset.name : `自定义 (${themeColor.value.toUpperCase()})`
})

const handleSelectMode = (mode: ThemeMode) => {
  setThemeMode(mode)
  form.theme_mode = mode
}

const handleSelectColor = (color: string) => {
  setThemeColor(color)
  form.theme_color = color
}

const handleCustomColorInput = (e: Event) => {
  const target = e.target as HTMLInputElement
  if (target?.value) {
    setThemeColor(target.value)
    form.theme_color = target.value
  }
}

const fetchConfig = async () => {
  try {
    const res = await apiClient.getSystemConfig()
    config.value = res.data
    form.llm_base_url = res.data.llm_base_url || 'https://api.openai.com/v1'
    form.llm_model_name = res.data.llm_model_name || 'gpt-4o-mini'
    form.llm_context_window = res.data.llm_context_window ?? 60000
    form.llm_temperature = res.data.llm_temperature ?? 1.0
    form.llm_frequency_penalty = res.data.llm_frequency_penalty ?? 0.0
    form.llm_presence_penalty = res.data.llm_presence_penalty ?? 0.0
    form.llm_top_p = res.data.llm_top_p ?? 1.0
    form.enable_realtime_sync =
      res.data.enable_realtime_sync === true || res.data.enable_realtime_sync === 'true'
    form.realtime_tick_hours = res.data.realtime_tick_hours ?? 1
    form.enable_stream_display =
      res.data.enable_stream_display !== false && res.data.enable_stream_display !== 'false'
    form.enable_phone_simulation =
      res.data.enable_phone_simulation === true || res.data.enable_phone_simulation === 'true'

    if (res.data.theme_mode) {
      form.theme_mode = res.data.theme_mode
      if (!localStorage.getItem('neu_theme_mode')) {
        setThemeMode(res.data.theme_mode)
      }
    }
    if (res.data.theme_color) {
      form.theme_color = res.data.theme_color
      if (!localStorage.getItem('neu_theme_color')) {
        setThemeColor(res.data.theme_color)
      }
    }

    worldStore.setEnableStreamDisplay(form.enable_stream_display)

    if (res.data.has_api_key && modelsList.value.length === 0) {
      await handleFetchModels(true)
    }
  } catch (err: any) {
    console.error('获取系统配置失败:', err)
  }
}

onMounted(() => {
  fetchConfig()
})

// 拉取模型列表
const handleFetchModels = async (silent = false) => {
  if (!form.llm_base_url) {
    if (!silent) toast.show({ type: 'warning', title: '缺少接口地址', description: '请先填入 LLM Base URL 接口地址' })
    return
  }

  isFetchingModels.value = true
  fetchError.value = false
  fetchSuccess.value = false
  fetchStatusText.value = '正在探测模型...'

  try {
    const res = await apiClient.fetchModels({
      llm_base_url: form.llm_base_url,
      llm_api_key: form.llm_api_key,
    })

    const fetched = res.data.models || []
    if (fetched.length === 0) {
      fetchError.value = true
      fetchStatusText.value = '未返回可用模型列表'
    } else {
      modelsList.value = fetched
      fetchSuccess.value = true
      fetchStatusText.value = `已拉取 ${fetched.length} 个模型`

      if (!fetched.includes(form.llm_model_name)) {
        form.llm_model_name = fetched[0]
      }
    }
  } catch (err: any) {
    fetchError.value = true
    const errMsg = err.response?.data?.detail || err.message || '拉取模型失败'
    fetchStatusText.value = `探测失败: ${errMsg}`
    if (!silent) {
      toast.show({ type: 'error', title: '拉取模型失败', description: errMsg })
    }
  } finally {
    isFetchingModels.value = false
  }
}

const handleSave = async () => {
  if (!form.llm_model_name) {
    toast.show({ type: 'warning', title: '缺少模型配置', description: '请先选择或拉取推演模型' })
    return
  }

  isSaving.value = true
  try {
    await apiClient.updateSystemConfig({
      llm_base_url: form.llm_base_url,
      llm_api_key: form.llm_api_key,
      llm_model_name: form.llm_model_name,
      llm_context_window: form.llm_context_window,
      llm_temperature: form.llm_temperature,
      llm_frequency_penalty: form.llm_frequency_penalty,
      llm_presence_penalty: form.llm_presence_penalty,
      llm_top_p: form.llm_top_p,
      enable_realtime_sync: form.enable_realtime_sync,
      realtime_tick_hours: form.realtime_tick_hours,
      enable_stream_display: form.enable_stream_display,
      enable_phone_simulation: form.enable_phone_simulation,
      theme_mode: themeMode.value,
      theme_color: themeColor.value,
    })
    worldStore.setEnableStreamDisplay(form.enable_stream_display)
    toast.showSuccess('配置已成功保存', '运行期参数与主题已持久化并即时生效')
    form.llm_api_key = ''
    await fetchConfig()
    emit('close')
  } catch (err: any) {
    toast.showErrorByCode(undefined, `配置更新失败: ${err.message}`)
  } finally {
    isSaving.value = false
  }
}

defineExpose({
  handleSave,
  isSaving,
})
</script>

<style scoped>
.system-config-panel {
  display: flex;
  flex-direction: column;
  gap: 0.95rem;
  width: 100%;
}

.status-summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0.75rem;
  font-size: 0.775rem;
  border-radius: 9px;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-weight: 600;
}

.status-badge.is-configured {
  color: var(--neu-success);
}

.status-badge.is-mock {
  color: var(--neu-warning);
}

.key-preview {
  font-size: 0.725rem;
  color: var(--neu-text-secondary);
  font-family: monospace;
}

.panel-desc {
  font-size: 0.775rem;
  color: var(--neu-text-secondary);
  line-height: 1.45;
  margin: 0;
}

.config-form {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  padding-bottom: 2.2rem;
}

/* 1. 主题与外观 */
.theme-config-section {
  padding: 0.85rem 0.95rem;
  border-radius: 12px;
  background: var(--neu-surface);
  border: 1px solid var(--neu-border, rgba(255, 255, 255, 0.35));
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}

.section-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 0.4rem;
  border-bottom: 1px solid rgba(196, 201, 212, 0.25);
}

.section-title-left {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.section-title-icon {
  font-size: 1.1rem;
  color: var(--neu-accent);
}

.section-title-text {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--neu-text-primary);
}

.theme-control-group {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.control-label {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.775rem;
  font-weight: 600;
  color: var(--neu-text-primary);
}

.label-icon {
  font-size: 0.9rem;
  color: var(--neu-accent);
}

.color-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.active-color-badge {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--neu-accent);
  background: rgba(var(--neu-accent-rgb, 94, 114, 228), 0.1);
  padding: 0.15rem 0.45rem;
  border-radius: 5px;
}

.mode-segmented-control {
  display: flex;
  padding: 0.2rem;
  border-radius: 9px;
  gap: 0.2rem;
  background: var(--neu-surface);
}

.mode-seg-btn {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  padding: 0.4rem 0.5rem;
  border: none;
  border-radius: 7px;
  background: transparent;
  color: var(--neu-text-secondary);
  font-size: 0.775rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
}

.mode-seg-btn:hover {
  color: var(--neu-text-primary);
}

.mode-seg-btn.is-active {
  background: var(--neu-surface);
  color: var(--neu-accent);
  font-weight: 700;
  box-shadow: var(--shadow-flat-sm);
}

.mode-icon {
  font-size: 0.95rem;
}

.color-palette-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.4rem;
  flex-wrap: wrap;
}

.presets-row {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  flex-wrap: wrap;
}

.color-dot-btn {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 2px solid transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.2s ease, box-shadow 0.2s;
  box-shadow: 1px 1px 3px var(--neu-shadow-dark), -1px -1px 3px var(--neu-shadow-light);
  padding: 0;
}

.color-dot-btn:hover {
  transform: scale(1.15);
}

.color-dot-btn.is-selected {
  transform: scale(1.18);
  border-color: #ffffff;
  box-shadow: 0 0 6px rgba(0, 0, 0, 0.35);
}

.check-icon {
  font-size: 0.85rem;
  color: #ffffff;
}

.custom-color-wrapper {
  position: relative;
}

.custom-color-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.3rem 0.55rem;
  border-radius: 7px;
  cursor: pointer;
  font-size: 0.725rem;
  color: var(--neu-text-primary);
  user-select: none;
  background: var(--neu-surface);
  box-shadow: var(--shadow-flat-sm);
  transition: all 0.2s ease;
}

.custom-color-btn.is-active {
  box-shadow: var(--shadow-active);
  color: var(--neu-accent);
  font-weight: 700;
}

.custom-dot-preview {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.custom-color-text {
  font-size: 0.725rem;
}

.picker-icon {
  font-size: 0.85rem;
  color: var(--neu-text-secondary);
}

.hidden-color-input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
  pointer-events: none;
}

/* 通用表单控件 */
.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.form-group label {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--neu-text-primary);
}

.neu-input {
  width: 100%;
  padding: 0.55rem 0.75rem;
  border: none;
  outline: none;
  font-family: inherit;
  font-size: 0.825rem;
  color: var(--neu-text-primary);
  background: var(--neu-surface);
  border-radius: var(--neu-radius-sm, 8px);
}

.neu-input:focus {
  box-shadow: inset 3px 3px 6px var(--neu-dark), inset -3px -3px 6px var(--neu-light), 0 0 0 1px var(--neu-accent);
}

.input-with-action {
  position: relative;
  display: flex;
  align-items: center;
}

.toggle-eye-btn {
  position: absolute;
  right: 0.65rem;
  background: none;
  border: none;
  color: var(--neu-text-secondary);
  cursor: pointer;
  font-size: 1.1rem;
}

.fetch-action-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.55rem 0.75rem;
  border-radius: var(--neu-radius-sm, 8px);
  gap: 0.65rem;
  background: var(--neu-surface);
}

.fetch-info {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  min-width: 0;
}

.fetch-title {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.775rem;
  font-weight: 600;
  color: var(--neu-text-primary);
}

.fetch-icon {
  font-size: 0.9rem;
  color: var(--neu-accent);
}

.fetch-status {
  font-size: 0.7rem;
  color: var(--neu-text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.status-ok {
  color: var(--neu-accent);
  font-weight: 500;
}

.status-error {
  color: #ef4444;
}

.form-hint {
  font-size: 0.7rem;
  color: var(--neu-text-muted);
}

/* 高级采样参数折叠手风琴 */
.collapsible-params-section {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.collapse-trigger-btn {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.65rem 0.85rem;
  border-radius: 10px;
  background: var(--neu-surface);
  border: 1px solid var(--neu-border, rgba(255, 255, 255, 0.35));
  cursor: pointer;
  user-select: none;
  width: 100%;
  text-align: left;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.collapse-trigger-btn.is-open {
  box-shadow: var(--shadow-active);
}

.collapse-header-left {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}

.collapse-icon {
  font-size: 1.15rem;
  color: var(--neu-accent);
  flex-shrink: 0;
}

.collapse-title-group {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  min-width: 0;
}

.collapse-main-title {
  font-size: 0.825rem;
  font-weight: 700;
  color: var(--neu-text-primary);
}

.collapse-summary-badge {
  font-size: 0.675rem;
  color: var(--neu-text-secondary);
  font-family: monospace;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.collapse-header-right {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.chevron-icon {
  font-size: 1.15rem;
  color: var(--neu-text-secondary);
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.chevron-icon.is-expanded {
  transform: rotate(180deg);
  color: var(--neu-accent);
}

.collapsible-content-body {
  padding: 0.85rem;
  border-radius: 10px;
  background: var(--neu-surface);
  display: flex;
  flex-direction: column;
  gap: 0.95rem;
}

.sampling-sliders-grid {
  display: flex;
  flex-direction: column;
  gap: 0.95rem;
}

.accordion-collapse-enter-active,
.accordion-collapse-leave-active {
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  max-height: 850px;
  overflow: hidden;
  opacity: 1;
}

.accordion-collapse-enter-from,
.accordion-collapse-leave-to {
  max-height: 0;
  opacity: 0;
  padding-top: 0;
  padding-bottom: 0;
  margin-top: 0;
  margin-bottom: 0;
}

/* 特性开关行 */
.stream-toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 0.85rem;
  border-radius: var(--neu-radius-sm, 8px);
  gap: 0.75rem;
  background: var(--neu-surface);
  border: 1px solid var(--neu-border, rgba(255, 255, 255, 0.35));
}

.stream-info {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.stream-title {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.825rem;
  font-weight: 600;
  color: var(--neu-text-primary);
}

.stream-icon {
  font-size: 1rem;
  color: var(--neu-accent);
}

.stream-hint {
  font-size: 0.7rem;
  color: var(--neu-text-secondary);
  line-height: 1.35;
}

.sync-toggle-box {
  flex-direction: column;
  align-items: stretch;
  gap: 0.65rem;
}

.sync-toggle-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.sync-status-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  font-size: 0.65rem;
  font-weight: 600;
  padding: 0.1rem 0.35rem;
  border-radius: 9999px;
  line-height: 1;
}

.sync-status-badge.badge-active {
  background: rgba(34, 197, 94, 0.15);
  color: #16a34a;
}

.sync-status-badge.badge-inactive {
  background: rgba(148, 163, 184, 0.15);
  color: var(--neu-text-secondary);
}

.sync-step-config {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.55rem 0.75rem;
  border-radius: var(--neu-radius-sm, 8px);
  background: var(--neu-surface);
  border: 1px solid var(--neu-border, rgba(255, 255, 255, 0.35));
}

.sync-step-label-group {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}

.sync-step-label {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.775rem;
  font-weight: 600;
  color: var(--neu-text-primary);
}

.sync-step-hint {
  font-size: 0.675rem;
  color: var(--neu-text-secondary);
}

.sync-step-input-wrap {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  flex-shrink: 0;
}

.sync-step-input {
  width: 60px;
  text-align: center;
  padding: 0.35rem 0.45rem;
  font-weight: 600;
  border-radius: var(--neu-radius-sm, 8px);
}

.sync-unit-label {
  font-size: 0.7rem;
  color: var(--neu-text-secondary);
  font-weight: 500;
}

.toggle-switch {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
  flex-shrink: 0;
  cursor: pointer;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: var(--neu-surface);
  box-shadow: inset 2px 2px 4px var(--neu-shadow-dark), inset -2px -2px 4px var(--neu-shadow-light);
  border-radius: 9999px;
  transition: 0.3s;
}

.toggle-slider:before {
  position: absolute;
  content: "";
  height: 16px;
  width: 16px;
  left: 4px;
  bottom: 4px;
  background-color: #94a3b8;
  border-radius: 50%;
  box-shadow: 1px 1px 3px var(--neu-shadow-dark);
  transition: 0.3s;
}

.toggle-switch input:checked + .toggle-slider {
  background-color: rgba(var(--neu-accent-rgb, 94, 114, 228), 0.22);
}

.toggle-switch input:checked + .toggle-slider:before {
  transform: translateX(20px);
  background-color: var(--neu-accent);
  box-shadow: 0 0 6px var(--neu-accent);
}

</style>
