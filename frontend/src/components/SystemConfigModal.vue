<template>
  <div v-if="isOpen" class="modal-backdrop" @click.self="$emit('close')">
    <NeuCard class="modal-card" variant="flat">
      <div class="modal-header">
        <div class="header-title">
          <Icon icon="material-symbols:settings" class="title-icon" />
          <h3>API 连接与系统设置</h3>
        </div>
        <button class="close-btn" @click="$emit('close')">
          <Icon icon="material-symbols:close" />
        </button>
      </div>

      <div class="modal-scroll-body">
        <!-- 运行状态横幅 -->
        <div class="status-summary neu-flat-sm">
          <span class="status-badge" :class="config.has_api_key ? 'is-configured' : 'is-mock'">
            <Icon :icon="config.has_api_key ? 'material-symbols:check-circle' : 'material-symbols:info'" />
            {{ config.has_api_key ? '已连接模型服务' : '本地规则演示模式 (未配置 API 密钥)' }}
          </span>
          <span v-if="config.api_key_masked" class="key-preview">
            Key: {{ config.api_key_masked }}
          </span>
        </div>

        <p class="panel-desc">
          配置模型接口端点、个性化界面主题与推演运行期参数。配置保存后自动持久化。
        </p>

        <form class="config-form" @submit.prevent="handleSave">
          <!-- ============================================== -->
          <!-- 1. 界面外观与个性化主题 (主题色 + 浅/深模式)      -->
          <!-- ============================================== -->
          <div class="theme-config-section neu-flat-sm">
            <div class="section-title-row">
              <div class="section-title-left">
                <Icon icon="material-symbols:palette" class="section-title-icon" />
                <span class="section-title-text">界面外观与个性化主题</span>
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
                  主题主色调
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
              当前已存 Key: {{ config.api_key_masked }}（若不更改请保持留空）
            </span>
          </div>

          <!-- ============================================== -->
          <!-- 4. 拉取模型操作条                              -->
          <!-- ============================================== -->
          <div class="fetch-action-row neu-inset-sm">
            <div class="fetch-info">
              <span class="fetch-title">
                <Icon icon="material-symbols:smart-toy" class="fetch-icon" />
                模型探测与拉取
              </span>
              <span class="fetch-status" :class="{ 'status-ok': fetchSuccess, 'status-error': fetchError }">
                {{ fetchStatusText }}
              </span>
            </div>
            <NeuButton
              type="button"
              icon="material-symbols:cloud-download"
              label="拉取可用模型"
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
              placeholder="-- 请点击上方【拉取可用模型】按钮选择模型 --"
              searchable
              icon="material-symbols:smart-toy"
            />
            <span class="form-hint">
              {{ modelsList.length > 0 ? `已获取 ${modelsList.length} 个可用模型` : '请点击上方按钮自动拉取接口支持的模型' }}
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
                  <span class="collapse-main-title">推演高级与采样参数调节</span>
                  <span class="collapse-summary-badge">{{ paramsSummaryText }}</span>
                </div>
              </div>

              <div class="collapse-header-right">
                <span class="collapse-state-hint">
                  {{ isParamsExpanded ? '收起参数' : '展开微调' }}
                </span>
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
                    label="上下文长度上限"
                    unit="Tokens"
                    icon="material-symbols:memory"
                    hint="限制推演单次送入模型的最大上下文容量"
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
                    hint="控制输出随机性与文学想象力，默认 1.00"
                  />

                  <NeuSlider
                    v-model="form.llm_frequency_penalty"
                    :min="-2.0"
                    :max="2.0"
                    :step="0.01"
                    label="频率惩罚 (Frequency Penalty)"
                    icon="material-symbols:repeat"
                    hint="降低高频重复字词的出现概率，推荐 0.2 ~ 1.0"
                  />

                  <NeuSlider
                    v-model="form.llm_presence_penalty"
                    :min="-2.0"
                    :max="2.0"
                    :step="0.01"
                    label="存在惩罚 (Presence Penalty)"
                    icon="material-symbols:topic"
                    hint="促使模型引入全新意象与词汇，打破前文意象惯性"
                  />

                  <NeuSlider
                    v-model="form.llm_top_p"
                    :min="0.0"
                    :max="1.0"
                    :step="0.01"
                    label="Top P 采样阈值"
                    icon="material-symbols:filter-alt"
                    hint="限制候选词累积概率阈值，与温度协同微调词汇分布"
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
                  <span>现实时间同步自动演化</span>
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
                  开启后，后台调度器随现实物理时间按步长自动推进推演；关闭后彻底停止后台自动请求，仅在手动点击续写或步进时调用模型。
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
                    <span>同步演化步长周期</span>
                  </label>
                  <span class="sync-step-hint">每次触发向虚拟世界推演的折算时间跨度 (1 ~ 24 小时)</span>
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
                开启后，故事正文将以打字机动效实时呈现；关闭后则在生成完成后一次性显示。
              </span>
            </div>
            <label class="toggle-switch">
              <input type="checkbox" v-model="form.enable_stream_display" />
              <span class="toggle-slider"></span>
            </label>
          </div>

          <!-- ============================================== -->
          <!-- 8. 手机与社交网络交互拟真开关                  -->
          <!-- ============================================== -->
          <div class="stream-toggle-row neu-inset-sm">
            <div class="stream-info">
              <div class="stream-title">
                <Icon icon="material-symbols:phone-iphone" class="stream-icon" />
                <span>手机与社交网络拟真</span>
              </div>
              <span class="stream-hint">
                开启后，角色在适宜情境下可使用手机收发即时消息、语音、转账，或浏览发布朋友圈与论坛热帖，以拟真卡片呈现。
              </span>
            </div>
            <label class="toggle-switch">
              <input type="checkbox" v-model="form.enable_phone_simulation" />
              <span class="toggle-slider"></span>
            </label>
          </div>

          <!-- ============================================== -->
          <!-- 底部动作按钮                                   -->
          <!-- ============================================== -->
          <div class="modal-actions">
            <NeuButton
              type="button"
              icon="material-symbols:cancel"
              label="取消"
              @click="$emit('close')"
            />
            <NeuButton
              type="submit"
              icon="material-symbols:save"
              label="保存配置至数据库"
              variant="accent"
              :loading="isSaving"
            />
          </div>
        </form>
      </div>
    </NeuCard>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive, watch } from 'vue'
import { Icon } from '@iconify/vue'
import NeuCard from './NeuCard.vue'
import NeuButton from './NeuButton.vue'
import NeuSlider from './NeuSlider.vue'
import NeuSelect from './NeuSelect.vue'
import { apiClient } from '../api/client'
import { useToast } from '../composables/useToast'
import { useWorldStore } from '../stores/world'
import { useTheme, type ThemeMode } from '../composables/useTheme'

const props = defineProps<{
  isOpen: boolean
}>()

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

// 参数调整折叠状态（默认收起，防止菜单过长）
const isParamsExpanded = ref(false)

const modelSelectOptions = computed(() => {
  const list = [...modelsList.value]
  if (form.llm_model_name && !list.includes(form.llm_model_name)) {
    return [
      { label: `${form.llm_model_name} (当前已存配置)`, value: form.llm_model_name, badge: '当前' },
      ...list.map((m) => ({ label: m, value: m })),
    ]
  }
  return list.map((m) => ({ label: m, value: m }))
})

const fetchStatusText = ref('点击右侧按钮测试并获取模型')
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
  return `温度 ${form.llm_temperature.toFixed(2)} · TopP ${form.llm_top_p.toFixed(2)} · ${kTokens}k Tokens`
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

    // 若系统已有配置且已有有效 Key，尝试自动拉取一次模型列表
    if (res.data.has_api_key && modelsList.value.length === 0) {
      await handleFetchModels(true)
    }
  } catch (err: any) {
    console.error('获取系统配置失败:', err)
  }
}

onMounted(() => {
  if (props.isOpen) fetchConfig()
})

watch(() => props.isOpen, (open) => {
  if (open) fetchConfig()
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
  fetchStatusText.value = '正在连接远程端点探测模型...'

  try {
    const res = await apiClient.fetchModels({
      llm_base_url: form.llm_base_url,
      llm_api_key: form.llm_api_key,
    })

    const fetched = res.data.models || []
    if (fetched.length === 0) {
      fetchError.value = true
      fetchStatusText.value = '接口已连通，但未返回可用模型列表'
    } else {
      modelsList.value = fetched
      fetchSuccess.value = true
      fetchStatusText.value = `已拉取到 ${fetched.length} 个模型`

      // 若当前选中的模型不在列表中，自动选中首项
      if (!fetched.includes(form.llm_model_name)) {
        form.llm_model_name = fetched[0]
      }
    }
  } catch (err: any) {
    fetchError.value = true
    const errMsg = err.response?.data?.detail || err.message || '拉取模型失败'
    fetchStatusText.value = `拉取失败: ${errMsg}`
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
    toast.showSuccess('配置已成功保存', 'LLM 运行期参数、主题样式与推演偏好已持久化至数据库并即时生效')
    form.llm_api_key = ''
    await fetchConfig()
    emit('close')
  } catch (err: any) {
    toast.showErrorByCode(undefined, `配置更新失败: ${err.message}`)
  } finally {
    isSaving.value = false
  }
}
</script>

<style scoped>
/* ==================================================== */
/* 模态框整体布局                                       */
/* ==================================================== */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.55);
  backdrop-filter: blur(5px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.modal-card {
  width: 100%;
  max-width: 600px;
  background: var(--neu-surface);
  max-height: 88vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.title-icon {
  font-size: 1.35rem;
  color: var(--neu-accent);
}

.header-title h3 {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--neu-text-primary);
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.25rem;
  color: var(--neu-text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  transition: color 0.15s ease;
}

.close-btn:hover {
  color: var(--neu-accent);
}

.modal-scroll-body {
  overflow-y: auto;
  overflow-x: hidden;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  padding-right: 0.35rem;
  padding-bottom: 0.5rem;
  scrollbar-width: thin;
  scrollbar-color: rgba(196, 201, 212, 0.55) transparent;
}

.modal-scroll-body::-webkit-scrollbar {
  width: 5px;
}

.modal-scroll-body::-webkit-scrollbar-track {
  background: transparent;
}

.modal-scroll-body::-webkit-scrollbar-thumb {
  background: rgba(196, 201, 212, 0.55);
  border-radius: 999px;
}

.modal-scroll-body::-webkit-scrollbar-thumb:hover {
  background: var(--neu-text-secondary);
}

.status-summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0.75rem;
  font-size: 0.8rem;
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
  font-size: 0.75rem;
  color: var(--neu-text-secondary);
  font-family: monospace;
}

.panel-desc {
  font-size: 0.8rem;
  color: var(--neu-text-secondary);
  line-height: 1.45;
}

.config-form {
  display: flex;
  flex-direction: column;
  gap: 0.95rem;
}

/* ==================================================== */
/* 1. 主题与外观个性化面板                             */
/* ==================================================== */
.theme-config-section {
  padding: 0.95rem 1rem;
  border-radius: 14px;
  background: var(--neu-surface);
  border: 1px solid var(--neu-border, rgba(255, 255, 255, 0.35));
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.section-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 0.45rem;
  border-bottom: 1px solid rgba(196, 201, 212, 0.25);
}

.section-title-left {
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.section-title-icon {
  font-size: 1.15rem;
  color: var(--neu-accent);
}

.section-title-text {
  font-size: 0.875rem;
  font-weight: 700;
  color: var(--neu-text-primary);
}

.theme-control-group {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.control-label {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--neu-text-primary);
}

.label-icon {
  font-size: 0.95rem;
  color: var(--neu-accent);
}

.color-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.active-color-badge {
  font-size: 0.725rem;
  font-weight: 600;
  color: var(--neu-accent);
  background: rgba(94, 114, 228, 0.1);
  padding: 0.15rem 0.5rem;
  border-radius: 6px;
}

/* 模式分段按钮 (Segmented Control) */
.mode-segmented-control {
  display: flex;
  padding: 0.25rem;
  border-radius: 10px;
  gap: 0.25rem;
  background: var(--neu-surface);
}

.mode-seg-btn {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  padding: 0.45rem 0.6rem;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--neu-text-secondary);
  font-size: 0.8rem;
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
  font-size: 1.05rem;
}

/* 主题色彩条 */
.color-palette-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.presets-row {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  flex-wrap: wrap;
}

.color-dot-btn {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: 2px solid transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.2s;
  box-shadow: 1px 1px 3px var(--neu-shadow-dark), -1px -1px 3px var(--neu-shadow-light);
  padding: 0;
}

.color-dot-btn:hover {
  transform: scale(1.15);
}

.color-dot-btn.is-selected {
  transform: scale(1.18);
  border-color: #ffffff;
  box-shadow: 0 0 8px rgba(0, 0, 0, 0.35);
}

.check-icon {
  font-size: 0.95rem;
  color: #ffffff;
  filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.5));
}

.custom-color-wrapper {
  position: relative;
}

.custom-color-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.35rem 0.65rem;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.775rem;
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
  width: 14px;
  height: 14px;
  border-radius: 50%;
  box-shadow: 0 0 3px rgba(0, 0, 0, 0.3);
}

.custom-color-text {
  font-size: 0.775rem;
}

.picker-icon {
  font-size: 0.95rem;
  color: var(--neu-text-secondary);
}

.hidden-color-input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
  pointer-events: none;
}

/* ==================================================== */
/* 表单控件通用基础                                     */
/* ==================================================== */
.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.form-group label {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.825rem;
  font-weight: 600;
  color: var(--neu-text-primary);
}

.neu-input {
  width: 100%;
  padding: 0.65rem 0.85rem;
  border: none;
  outline: none;
  font-family: inherit;
  font-size: 0.85rem;
  color: var(--neu-text-primary);
  background: var(--neu-surface);
  border-radius: var(--neu-radius, 10px);
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
  right: 0.75rem;
  background: none;
  border: none;
  color: var(--neu-text-secondary);
  cursor: pointer;
  font-size: 1.15rem;
}

.fetch-action-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.65rem 0.85rem;
  border-radius: var(--neu-radius, 10px);
  gap: 0.75rem;
  background: var(--neu-surface);
}

.fetch-info {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  min-width: 0;
}

.fetch-title {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--neu-text-primary);
}

.fetch-icon {
  font-size: 0.95rem;
  color: var(--neu-accent);
}

.fetch-status {
  font-size: 0.725rem;
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
  font-size: 0.725rem;
  color: var(--neu-text-muted);
}

/* ==================================================== */
/* 2. 推演高级与采样参数折叠组                          */
/* ==================================================== */
.collapsible-params-section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.collapse-trigger-btn {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 0.95rem;
  border-radius: 12px;
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
  gap: 0.6rem;
  min-width: 0;
}

.collapse-icon {
  font-size: 1.25rem;
  color: var(--neu-accent);
  flex-shrink: 0;
}

.collapse-title-group {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  min-width: 0;
}

.collapse-main-title {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--neu-text-primary);
}

.collapse-summary-badge {
  font-size: 0.7rem;
  color: var(--neu-text-secondary);
  font-family: monospace;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.collapse-header-right {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-shrink: 0;
}

.collapse-state-hint {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--neu-accent);
}

.chevron-icon {
  font-size: 1.25rem;
  color: var(--neu-text-secondary);
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.chevron-icon.is-expanded {
  transform: rotate(180deg);
  color: var(--neu-accent);
}

.collapsible-content-body {
  padding: 1rem;
  border-radius: 12px;
  background: var(--neu-surface);
  display: flex;
  flex-direction: column;
  gap: 1.15rem;
}

.nested-slider-wrap {
  margin-top: 0.2rem;
}

.sampling-sliders-grid {
  display: flex;
  flex-direction: column;
  gap: 1.1rem;
}

.nested-tick-group {
  padding-top: 0.35rem;
  border-top: 1px solid rgba(196, 201, 212, 0.25);
}

/* 手风琴折叠动画 */
.accordion-collapse-enter-active,
.accordion-collapse-leave-active {
  transition: all 0.28s cubic-bezier(0.4, 0, 0.2, 1);
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

/* ==================================================== */
/* 3. 特性开关 (Stream & Phone Simulation)             */
/* ==================================================== */
.stream-toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.85rem 1rem;
  border-radius: var(--neu-radius-sm, 8px);
  gap: 1rem;
  background: var(--neu-surface);
  border: 1px solid var(--neu-border, rgba(255, 255, 255, 0.35));
}

.stream-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.stream-title {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--neu-text-primary);
}

.stream-icon {
  font-size: 1.1rem;
  color: var(--neu-accent);
}

.stream-hint {
  font-size: 0.75rem;
  color: var(--neu-text-secondary);
  line-height: 1.4;
}

/* ==================================================== */
/* 现实时间同步演化开关与步长控制 (Sync Toggle Box)     */
/* ==================================================== */
.sync-toggle-box {
  flex-direction: column;
  align-items: stretch;
  gap: 0.75rem;
}

.sync-toggle-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.sync-status-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.15rem 0.45rem;
  border-radius: 9999px;
  line-height: 1;
  transition: all 0.25s ease;
  vertical-align: middle;
}

.sync-status-badge .badge-icon {
  font-size: 0.85rem;
}

.sync-status-badge.badge-active {
  background: rgba(34, 197, 94, 0.15);
  color: #16a34a;
  border: 1px solid rgba(34, 197, 94, 0.3);
}

.sync-status-badge.badge-inactive {
  background: rgba(148, 163, 184, 0.15);
  color: var(--neu-text-secondary);
  border: 1px solid rgba(148, 163, 184, 0.25);
}

.sync-step-config {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.65rem 0.85rem;
  border-radius: var(--neu-radius-sm, 8px);
  background: var(--neu-surface);
  border: 1px solid var(--neu-border, rgba(255, 255, 255, 0.35));
}

.sync-step-label-group {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.sync-step-label {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--neu-text-primary);
}

.sync-step-hint {
  font-size: 0.725rem;
  color: var(--neu-text-secondary);
}

.sync-step-input-wrap {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  flex-shrink: 0;
}

.sync-step-input {
  width: 76px;
  text-align: center;
  padding: 0.4rem 0.5rem;
  font-weight: 600;
  border-radius: var(--neu-radius-sm, 8px);
}

.sync-unit-label {
  font-size: 0.75rem;
  color: var(--neu-text-secondary);
  font-weight: 500;
  white-space: nowrap;
}

/* 拟物滑动开关 (Neu Toggle Switch) */
.toggle-switch {
  position: relative;
  display: inline-block;
  width: 48px;
  height: 26px;
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
  height: 18px;
  width: 18px;
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
  transform: translateX(22px);
  background-color: var(--neu-accent);
  box-shadow: 0 0 6px var(--neu-accent);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 0.5rem;
}
</style>
