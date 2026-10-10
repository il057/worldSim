<template>
  <div v-if="isOpen" class="modal-backdrop" @click.self="$emit('close')">
    <NeuCard class="modal-card" variant="flat">
      <div class="modal-header">
        <div class="header-title">
          <Icon icon="material-symbols:settings" class="title-icon" />
          <h3>API 连接与推演引擎配置</h3>
        </div>
        <button class="close-btn" @click="$emit('close')">
          <Icon icon="material-symbols:close" />
        </button>
      </div>

      <div class="modal-scroll-body">
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
        配置模型接口服务（支持 DeepSeek、OpenAI、Claude、Qwen 等主流模型）。配置将自动保存。
      </p>

      <form class="config-form" @submit.prevent="handleSave">
        <!-- 1. LLM Base URL -->
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

        <!-- 2. LLM API Key -->
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

        <!-- 3. 拉取模型操作条 -->
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

        <!-- 4. 推演模型选择 (下拉选择，禁止用户随意自行输入) -->
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

        <!-- 5. 上下文 Token (采用 NeuSlider 滑动设置，512 - 2,000,000) -->
        <div class="form-group-slider">
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

        <!-- 6. 模型采样参数精细调节 (SillyTavern 风格新拟态控制组) -->
        <div class="sampling-params-card neu-flat-sm">
          <div class="sampling-header">
            <Icon icon="material-symbols:tune" class="sampling-icon" />
            <span class="sampling-title">采样高级参数调节</span>
          </div>

          <div class="sampling-sliders-grid">
            <NeuSlider
              v-model="form.llm_temperature"
              :min="0.0"
              :max="2.0"
              :step="0.01"
              label="温度"
              icon="material-symbols:thermostat"
              hint="控制输出随机性与文学想象力，默认 1.00"
            />

            <NeuSlider
              v-model="form.llm_frequency_penalty"
              :min="-2.0"
              :max="2.0"
              :step="0.01"
              label="频率惩罚"
              icon="material-symbols:repeat"
              hint="降低高频重复字词的出现概率，推荐 0.2 ~ 1.0"
            />

            <NeuSlider
              v-model="form.llm_presence_penalty"
              :min="-2.0"
              :max="2.0"
              :step="0.01"
              label="存在惩罚"
              icon="material-symbols:topic"
              hint="促使模型引入全新意象与词汇，打破前文意象惯性"
            />

            <NeuSlider
              v-model="form.llm_top_p"
              :min="0.0"
              :max="1.0"
              :step="0.01"
              label="Top P"
              icon="material-symbols:filter-alt"
              hint="限制候选词累积概率阈值，与温度协同微调词汇分布"
            />
          </div>
        </div>

        <!-- 7. 真实时钟演化步长 -->
        <div class="form-group">
          <label>
            <Icon icon="material-symbols:timelapse" class="label-icon" />
            现实同步演化步长 (小时/次)
          </label>
          <input
            type="number"
            v-model.number="form.realtime_tick_hours"
            min="1"
            max="24"
            class="neu-input neu-inset-sm"
            required
          />
        </div>

        <!-- 8. 推演正文流式输出 -->
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

        <!-- 9. 手机与社交网络交互拟真开关 -->
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

        <!-- 底部动作按钮 -->
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

const props = defineProps<{
  isOpen: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const toast = useToast()
const worldStore = useWorldStore()
const config = ref<any>({})
const isSaving = ref(false)
const isFetchingModels = ref(false)
const showKey = ref(false)
const modelsList = ref<string[]>([])
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
  realtime_tick_hours: 1,
  enable_stream_display: true,
  enable_phone_simulation: false,
})

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
    form.realtime_tick_hours = res.data.realtime_tick_hours ?? 1
    form.enable_stream_display =
      res.data.enable_stream_display !== false && res.data.enable_stream_display !== 'false'
    form.enable_phone_simulation =
      res.data.enable_phone_simulation === true || res.data.enable_phone_simulation === 'true'

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
      llm_api_key: form.llm_api_key, // 为空时后端自动使用已存 key
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
      realtime_tick_hours: form.realtime_tick_hours,
      enable_stream_display: form.enable_stream_display,
      enable_phone_simulation: form.enable_phone_simulation,
    })
    worldStore.setEnableStreamDisplay(form.enable_stream_display)
    toast.showSuccess('配置已成功保存', 'LLM 运行期参数、流式开关与采样配置已持久化至数据库并即时生效')
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
.form-group-slider {
  margin-top: 0.5rem;
  margin-bottom: 0.75rem;
}

.sampling-params-card {
  padding: 1.15rem 1.25rem;
  border-radius: 14px;
  background: var(--neu-surface);
  border: 1px solid rgba(255, 255, 255, 0.5);
  margin-bottom: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.sampling-header {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  font-size: 0.9rem;
  font-weight: 700;
  color: var(--neu-text-primary);
  border-bottom: 1px solid rgba(196, 201, 212, 0.4);
  padding-bottom: 0.5rem;
}

.sampling-icon {
  font-size: 1.15rem;
  color: var(--neu-accent);
}

.sampling-sliders-grid {
  display: flex;
  flex-direction: column;
  gap: 1.1rem;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(30, 41, 59, 0.45);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.modal-card {
  width: 100%;
  max-width: 580px;
  background: #f0f3f8;
  max-height: 88vh;
  overflow: hidden; /* 保证圆角完全不受外部滚动条穿透破坏 */
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

.modal-scroll-body {
  overflow-y: auto;
  overflow-x: hidden;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding-right: 0.35rem;
  padding-bottom: 0.5rem;
  /* 柔和精致的内置微型滚动条，绝不外露于 modal 之外 */
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
  gap: 1rem;
}

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

.label-icon {
  font-size: 1rem;
  color: var(--neu-accent);
}

.neu-input,
.neu-select {
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

.neu-select {
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml;charset=UTF-8,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%2364748b'%3e%3cpath d='M7 10l5 5 5-5z'/%3e%3c/svg%3e");
  background-repeat: no-repeat;
  background-position: right 0.75rem center;
  background-size: 1.25rem;
  padding-right: 2.2rem;
}

.neu-select option {
  background: var(--neu-surface);
  color: var(--neu-text-primary);
  padding: 0.5rem;
}

.neu-input:focus,
.neu-select:focus {
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

.stream-toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.85rem 1rem;
  border-radius: var(--neu-radius-sm, 8px);
  gap: 1rem;
  background: var(--neu-surface);
  border: 1px solid rgba(255, 255, 255, 0.4);
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
  background-color: var(--neu-base);
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
  background-color: rgba(59, 130, 246, 0.15);
}

.toggle-switch input:checked + .toggle-slider:before {
  transform: translateX(22px);
  background-color: var(--neu-accent);
  box-shadow: 0 0 6px rgba(59, 130, 246, 0.5);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 0.5rem;
}
</style>
