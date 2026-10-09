<template>
  <div v-if="isOpen" class="modal-backdrop" @click.self="$emit('close')">
    <NeuCard class="modal-card" variant="flat">
      <div class="modal-header">
        <div class="header-title">
          <Icon icon="material-symbols:upload-file" class="title-icon" />
          <h3>酒馆角色卡摄入与全量设定微调</h3>
        </div>
        <button class="close-btn" @click="$emit('close')">
          <Icon icon="material-symbols:close" />
        </button>
      </div>

      <p class="modal-subtitle">
        已自动清洗酒馆 HTML 杂质、剥离前端状态栏宏并解耦 <span v-pre>{{user}}</span> 依赖。在正式落库前，您可自由审查并调整角色人设、生理状态、NPC 关系网及世界书。
      </p>

      <!-- 步骤 1: 上传解析 -->
      <div v-if="!parsedData" class="upload-area">
        <label class="drop-zone neu-inset" :class="{ 'is-loading': isParsing }">
          <Icon
            :icon="isParsing ? 'material-symbols:progress-activity' : 'material-symbols:cloud-upload'"
            class="upload-icon"
            :class="{ spin: isParsing }"
          />
          <span class="upload-text">
            {{ isParsing ? '正在智能解析卡片、提取作息画像与 NPC 关系网...' : '点击选择或拖拽酒馆角色卡 (JSON 或 PNG 角色卡图片)' }}
          </span>
          <span class="upload-subtext">
            支持多人卡自动识别世界书角色；若上传 PNG，将自动提取内嵌数据并保留高清头像
          </span>
          <input
            type="file"
            accept=".json,.png,image/png"
            class="hidden-file-input"
            :disabled="isParsing"
            @change="handleFileUpload"
          />
        </label>
      </div>

      <!-- 步骤 2: 预览与深度可控调整 -->
      <div v-else class="parse-results">
        <!-- 统计摘要与 POV 主角单选 -->
        <div class="pov-section">
          <div class="pov-header">
            <span class="section-label">
              <Icon icon="material-symbols:person-pin" class="label-icon" />
              推演主视角主角 (POV Protagonist)
              <span v-if="parsedData.is_multi_entity" class="multi-tag neu-flat-sm">多人卡已识别</span>
            </span>
            <span class="meta-hint">
              共发现 {{ editableEntities.length }} 个候选主角实体，请单选确立主视角
            </span>
          </div>

          <div class="entities-grid">
            <div
              v-for="ent in editableEntities"
              :key="ent.entity_id"
              :class="['entity-card', 'neu-flat-sm', { 'is-selected': currentEntityId === ent.entity_id }]"
              @click="selectEntity(ent.entity_id)"
            >
              <div class="entity-card-top">
                <input
                  type="radio"
                  :value="ent.entity_id"
                  v-model="currentEntityId"
                  name="pov_selection"
                />
                <img
                  v-if="ent.avatar_url"
                  :src="ent.avatar_url"
                  class="preview-avatar neu-flat-sm"
                  alt="avatar"
                />
                <div class="avatar-placeholder neu-inset-sm" v-else>
                  <Icon icon="material-symbols:account-circle" />
                </div>
                <div class="entity-name-box">
                  <span class="entity-name">{{ ent.name }}</span>
                  <span class="entity-title">{{ ent.title || '漫游者' }}</span>
                </div>
              </div>
              <p class="entity-preview-text">{{ ent.persona_summary.slice(0, 90) }}...</p>
            </div>
          </div>
        </div>

        <!-- 标签页导航栏 -->
        <div class="tabs-nav neu-inset-sm">
          <button
            type="button"
            :class="['tab-btn', { active: activeTab === 'persona' }]"
            @click="activeTab = 'persona'"
          >
            <Icon icon="material-symbols:psychology" class="tab-icon" />
            人设与执念
          </button>
          <button
            type="button"
            :class="['tab-btn', { active: activeTab === 'vitals' }]"
            @click="activeTab = 'vitals'"
          >
            <Icon icon="material-symbols:vital-signs" class="tab-icon" />
            生理与初始状态
          </button>
          <button
            type="button"
            :class="['tab-btn', { active: activeTab === 'relationships' }]"
            @click="activeTab = 'relationships'"
          >
            <Icon icon="material-symbols:group" class="tab-icon" />
            NPC 关系网 ({{ editableRelationships.length }})
          </button>
          <button
            type="button"
            :class="['tab-btn', { active: activeTab === 'lores' }]"
            @click="activeTab = 'lores'"
          >
            <Icon icon="material-symbols:menu-book" class="tab-icon" />
            世界书设定 ({{ editableLores.length }})
          </button>
        </div>

        <!-- 标签页内容 1: 人设与执念 -->
        <div v-show="activeTab === 'persona'" class="tab-content">
          <div v-if="activeEntity" class="form-grid">
            <div class="form-row">
              <div class="form-field">
                <label>角色姓名</label>
                <input v-model="activeEntity.name" class="neu-input" placeholder="角色姓名" />
              </div>
              <div class="form-field">
                <label>身份头衔 / 称号</label>
                <input v-model="activeEntity.title" class="neu-input" placeholder="如：九尾天狐 / 特级荣誉顾问" />
              </div>
            </div>

            <div class="form-field">
              <label>核心内在执念 (Inner Drive)</label>
              <textarea
                v-model="activeEntity.inner_drive"
                class="neu-input drive-textarea"
                rows="2"
                placeholder="角色不可磨灭的深层心理诉求与行动终极目标"
              ></textarea>
            </div>

            <div class="form-field">
              <div class="field-label-group">
                <label>全量人设总述 (Persona Summary)</label>
                <span class="field-hint">已保留卡片全量背景、性格与习惯，无字数截断限制</span>
              </div>
              <textarea
                v-model="activeEntity.persona_summary"
                class="neu-input persona-textarea"
                rows="7"
                placeholder="角色完整人设、外貌特征、行为准则及世界观背景设定"
              ></textarea>
            </div>
          </div>
        </div>

        <!-- 标签页内容 2: 生理与初始状态 -->
        <div v-show="activeTab === 'vitals'" class="tab-content">
          <div v-if="activeEntity" class="form-grid">
            <div class="form-row">
              <div class="form-field">
                <label>开局微观具体地点</label>
                <input
                  v-model="activeEntity.initial_location"
                  class="neu-input"
                  placeholder="如：长宁市古董街老宅正堂"
                />
              </div>
              <div class="form-field">
                <label>开局虚拟时间</label>
                <input
                  v-model="activeEntity.initial_virtual_time"
                  class="neu-input"
                  placeholder="如：深秋月 初九 19:30"
                />
              </div>
            </div>

            <div class="form-row vitals-row">
              <div class="form-field">
                <label>初始健康值 (0-100): {{ activeEntity.initial_health }}%</label>
                <input
                  type="range"
                  min="1"
                  max="100"
                  v-model.number="activeEntity.initial_health"
                  class="neu-range"
                />
              </div>
              <div class="form-field">
                <label>初始精力值 (0-100): {{ activeEntity.initial_stamina }}%</label>
                <input
                  type="range"
                  min="1"
                  max="100"
                  v-model.number="activeEntity.initial_stamina"
                  class="neu-range"
                />
              </div>
              <div class="form-field">
                <label>即时心理情绪</label>
                <input
                  v-model="activeEntity.initial_psychological_state"
                  class="neu-input"
                  placeholder="如：慵懒且警觉"
                />
              </div>
            </div>

            <div class="form-box neu-inset-sm">
              <div class="box-title">
                <Icon icon="material-symbols:bedtime" class="mini-icon" />
                自适应作息画像 (Circadian Profile)
              </div>
              <div class="form-row">
                <div class="form-field">
                  <label>节律倾向</label>
                  <select v-model="activeEntity.circadian_profile.chronotype" class="neu-input">
                    <option value="夜行型">夜行型 (昼伏夜出)</option>
                    <option value="早起型">早起型 (晨昏规律)</option>
                    <option value="昼夜无律型">昼夜无律型 (随性而定)</option>
                    <option value="无休眠体质">无休眠体质 (非人/不死/机械)</option>
                  </select>
                </div>
                <div class="form-field">
                  <label>常规休眠倾向窗口</label>
                  <input
                    v-model="activeEntity.circadian_profile.typical_rest_window"
                    class="neu-input"
                    placeholder="如：05:00 - 13:00"
                  />
                </div>
              </div>
              <div class="form-field">
                <label>环境耐受度与休眠驱动逻辑</label>
                <input
                  v-model="activeEntity.circadian_profile.environment_tolerance"
                  class="neu-input"
                  placeholder="如：私人老宅软榻或安静向阳的躺椅"
                />
              </div>
            </div>

            <!-- 随身背包物品 -->
            <div class="form-box neu-inset-sm">
              <div class="box-title">
                <Icon icon="material-symbols:inventory-2" class="mini-icon" />
                随身背包物品 ({{ (activeEntity.initial_inventory || []).length }})
              </div>
              <div class="tag-cloud">
                <span
                  v-for="(item, idx) in activeEntity.initial_inventory"
                  :key="idx"
                  class="item-tag neu-flat-sm"
                >
                  {{ item }}
                  <button type="button" class="tag-remove" @click="removeItem(idx)">
                    <Icon icon="material-symbols:close" />
                  </button>
                </span>
              </div>
              <div class="add-item-row">
                <input
                  v-model="newItemInput"
                  class="neu-input item-input"
                  placeholder="输入新物品名称按回车添加..."
                  @keyup.enter="addItem"
                />
                <NeuButton type="button" label="添加物品" icon="material-symbols:add" @click="addItem" />
              </div>
            </div>

            <!-- 初始紧迫目标 -->
            <div class="form-box neu-inset-sm">
              <div class="box-title">
                <Icon icon="material-symbols:flag" class="mini-icon" />
                初始紧迫目标 ({{ (activeEntity.initial_goals || []).length }})
              </div>
              <div class="goals-list">
                <div
                  v-for="(_, gIdx) in (activeEntity.initial_goals || [])"
                  :key="gIdx"
                  class="goal-item-row neu-flat-sm"
                >
                  <span class="goal-bullet">{{ gIdx + 1 }}.</span>
                  <input
                    :value="activeEntity.initial_goals?.[gIdx] ?? ''"
                    @input="activeEntity.initial_goals && (activeEntity.initial_goals[gIdx] = ($event.target as HTMLInputElement).value)"
                    class="neu-input-inline"
                  />
                  <button type="button" class="tag-remove" @click="removeGoal(gIdx)">
                    <Icon icon="material-symbols:close" />
                  </button>
                </div>
              </div>
              <div class="add-item-row">
                <input
                  v-model="newGoalInput"
                  class="neu-input item-input"
                  placeholder="输入开局行动目标按回车添加..."
                  @keyup.enter="addGoal"
                />
                <NeuButton type="button" label="添加目标" icon="material-symbols:add" @click="addGoal" />
              </div>
            </div>
          </div>
        </div>

        <!-- 标签页内容 3: NPC 关系网 -->
        <div v-show="activeTab === 'relationships'" class="tab-content">
          <div class="tab-top-actions">
            <span class="tab-summary-hint">
              已从世界书与角色卡自动提取 {{ editableRelationships.length }} 名关联 NPC，落库后注入社交网络
            </span>
            <NeuButton
              type="button"
              label="新增 NPC"
              icon="material-symbols:person-add"
              @click="addNpc"
            />
          </div>

          <div v-if="editableRelationships.length === 0" class="empty-hint neu-inset-sm">
            未在角色卡与世界书中检测到结构化 NPC，可点击右上角手动新增。
          </div>

          <div class="npc-cards-list">
            <div
              v-for="(npc, nIdx) in editableRelationships"
              :key="nIdx"
              class="npc-edit-card neu-flat-sm"
            >
              <div class="npc-row-main">
                <div class="form-field npc-name-field">
                  <label>NPC 姓名</label>
                  <input v-model="npc.npc_name" class="neu-input" placeholder="NPC 姓名" />
                </div>
                <div class="form-field npc-rel-field">
                  <label>社会关系类型</label>
                  <input v-model="npc.relation_type" class="neu-input" placeholder="如：供养者 / 麻烦制造者" />
                </div>
                <div class="form-field npc-affinity-field">
                  <label>初始好感 (0-100)</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    v-model.number="npc.affinity"
                    class="neu-input"
                  />
                </div>
                <button
                  type="button"
                  class="npc-delete-btn"
                  title="移除该 NPC"
                  @click="removeNpc(nIdx)"
                >
                  <Icon icon="material-symbols:delete" />
                </button>
              </div>

              <div class="form-field">
                <label>身份背景与对主角态度</label>
                <textarea
                  v-model="npc.summary"
                  class="neu-input npc-summary-textarea"
                  rows="2"
                  placeholder="NPC 身份特征、外貌特征、性格及与主角的历史羁绊"
                ></textarea>
              </div>
            </div>
          </div>
        </div>

        <!-- 标签页内容 4: 世界书设定 -->
        <div v-show="activeTab === 'lores'" class="tab-content">
          <div class="tab-top-actions">
            <span class="tab-summary-hint">
              已滤除酒馆状态栏与元指令，保留 {{ editableLores.length }} 条世界观法则（可勾选或编辑）
            </span>
            <NeuButton
              type="button"
              label="新增世界书条目"
              icon="material-symbols:post-add"
              @click="addLore"
            />
          </div>

          <div v-if="editableLores.length === 0" class="empty-hint neu-inset-sm">
            本角色卡未挂载独立世界书，或所有前端指令已被清理。可点击上方按钮添加法则。
          </div>

          <div class="lores-list">
            <div
              v-for="(lore, lIdx) in editableLores"
              :key="lIdx"
              class="lore-edit-card neu-flat-sm"
            >
              <div class="lore-header-row">
                <div class="lore-title-group">
                  <input
                    v-model="lore.title"
                    class="neu-input lore-title-input"
                    placeholder="条目标题（如：末法时代）"
                  />
                  <select v-model="lore.category" class="neu-input lore-cat-select">
                    <option value="static">静态常驻世界观</option>
                    <option value="dynamic">动态关键词触发</option>
                  </select>
                </div>
                <button
                  type="button"
                  class="lore-delete-btn"
                  title="删除该世界书条目"
                  @click="removeLore(lIdx)"
                >
                  <Icon icon="material-symbols:delete" />
                </button>
              </div>

              <div v-if="lore.category === 'dynamic'" class="form-field">
                <label>触发关键词 (英文逗号分隔)</label>
                <input
                  v-model="lore.trigger_keys"
                  class="neu-input"
                  placeholder="如：古董街, 灵气, 异管局"
                />
              </div>

              <div class="form-field">
                <label>条目正文设定</label>
                <textarea
                  v-model="lore.content"
                  class="neu-input lore-content-textarea"
                  rows="3"
                  placeholder="世界法则、地理风貌、组织势力或物品设定全文"
                ></textarea>
              </div>
            </div>
          </div>
        </div>

        <!-- 底部落库操作栏 -->
        <div class="modal-actions">
          <NeuButton
            type="button"
            icon="material-symbols:restart-alt"
            label="重新选择文件"
            @click="resetAll"
          />
          <NeuButton
            type="button"
            icon="material-symbols:check-circle"
            label="确认全部设定并落库生成世界"
            variant="accent"
            :loading="isImporting"
            @click="handleImport"
          />
        </div>
      </div>
    </NeuCard>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Icon } from '@iconify/vue'
import NeuCard from './NeuCard.vue'
import NeuButton from './NeuButton.vue'
import { apiClient } from '../api/client'
import type {
  CardParseResponse,
  DetectedEntity,
  DetectedRelationship,
  WorldLoreInput,
} from '../api/client'

const props = defineProps<{
  isOpen: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'imported', characterId: string): void
}>()

const isParsing = ref(false)
const isImporting = ref(false)
const parsedData = ref<CardParseResponse | null>(null)
const currentEntityId = ref<string>('')
const activeTab = ref<'persona' | 'vitals' | 'relationships' | 'lores'>('persona')

// 可编辑的数据副本
const editableEntities = ref<DetectedEntity[]>([])
const editableRelationships = ref<DetectedRelationship[]>([])
const editableLores = ref<WorldLoreInput[]>([])

const newItemInput = ref('')
const newGoalInput = ref('')

const activeEntity = computed(() => {
  return editableEntities.value.find((e) => e.entity_id === currentEntityId.value)
})

const selectEntity = (id: string) => {
  currentEntityId.value = id
}

const handleFileUpload = async (e: Event) => {
  const target = e.target as HTMLInputElement
  if (!target.files || target.files.length === 0) return

  const file = target.files[0]
  isParsing.value = true
  try {
    const res = await apiClient.parseCard(file)
    parsedData.value = res.data
    editableEntities.value = JSON.parse(JSON.stringify(res.data.detected_entities || []))
    editableRelationships.value = JSON.parse(JSON.stringify(res.data.detected_relationships || []))
    editableLores.value = JSON.parse(JSON.stringify(res.data.lores || []))

    if (editableEntities.value.length > 0) {
      currentEntityId.value = editableEntities.value[0].entity_id
    }
    activeTab.value = 'persona'
  } catch (err: any) {
    alert(`解析失败: ${err.response?.data?.detail || err.message}`)
  } finally {
    isParsing.value = false
  }
}

const addItem = () => {
  if (!newItemInput.value.trim() || !activeEntity.value) return
  if (!activeEntity.value.initial_inventory) {
    activeEntity.value.initial_inventory = []
  }
  activeEntity.value.initial_inventory.push(newItemInput.value.trim())
  newItemInput.value = ''
}

const removeItem = (index: number) => {
  if (activeEntity.value && activeEntity.value.initial_inventory) {
    activeEntity.value.initial_inventory.splice(index, 1)
  }
}

const addGoal = () => {
  if (!newGoalInput.value.trim() || !activeEntity.value) return
  if (!activeEntity.value.initial_goals) {
    activeEntity.value.initial_goals = []
  }
  activeEntity.value.initial_goals.push(newGoalInput.value.trim())
  newGoalInput.value = ''
}

const removeGoal = (index: number) => {
  if (activeEntity.value && activeEntity.value.initial_goals) {
    activeEntity.value.initial_goals.splice(index, 1)
  }
}

const addNpc = () => {
  editableRelationships.value.unshift({
    npc_name: '新人物',
    relation_type: '同行者',
    affinity: 50,
    summary: '与主角有所交集的关键角色。',
  })
}

const removeNpc = (index: number) => {
  editableRelationships.value.splice(index, 1)
}

const addLore = () => {
  editableLores.value.unshift({
    title: '新世界法则',
    category: 'static',
    trigger_keys: '',
    content: '世界观背景设定描述...',
  })
}

const removeLore = (index: number) => {
  editableLores.value.splice(index, 1)
}

const resetAll = () => {
  parsedData.value = null
  editableEntities.value = []
  editableRelationships.value = []
  editableLores.value = []
  currentEntityId.value = ''
}

const handleImport = async () => {
  if (!activeEntity.value || isImporting.value) return

  isImporting.value = true
  try {
    const res = await apiClient.importCard({
      selected_entity: activeEntity.value,
      all_entities: editableEntities.value,
      lores: editableLores.value,
      relationships: editableRelationships.value,
      initial_location: activeEntity.value.initial_location,
      initial_virtual_time: activeEntity.value.initial_virtual_time,
      initial_health: activeEntity.value.initial_health,
      initial_stamina: activeEntity.value.initial_stamina,
      initial_psychological_state: activeEntity.value.initial_psychological_state,
      initial_inventory: activeEntity.value.initial_inventory,
      initial_goals: activeEntity.value.initial_goals,
    })
    emit('imported', res.data.character_id)
    emit('close')
    resetAll()
  } catch (err: any) {
    alert(`导入落库失败: ${err.response?.data?.detail || err.message}`)
  } finally {
    isImporting.value = false
  }
}
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(45, 55, 72, 0.55);
  backdrop-filter: blur(5px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1.25rem;
}

.modal-card {
  width: 100%;
  max-width: 860px;
  background: #f0f3f8;
  max-height: 92vh;
  display: flex;
  flex-direction: column;
  padding: 1.5rem;
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.35rem;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.title-icon {
  font-size: 1.4rem;
  color: var(--neu-accent);
}

.header-title h3 {
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--neu-text-primary);
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.35rem;
  color: var(--neu-text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  padding: 4px;
  transition: all 0.2s;
}

.close-btn:hover {
  color: var(--neu-danger);
}

.modal-subtitle {
  font-size: 0.8rem;
  color: var(--neu-text-secondary);
  margin-bottom: 1rem;
  line-height: 1.45;
}

.upload-area {
  padding: 1.5rem 0;
}

.drop-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 3rem 1.5rem;
  cursor: pointer;
  border: 1px dashed var(--neu-dark);
  text-align: center;
  border-radius: 14px;
}

.upload-icon {
  font-size: 3rem;
  color: var(--neu-accent);
}

.upload-text {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--neu-text-primary);
}

.upload-subtext {
  font-size: 0.75rem;
  color: var(--neu-accent);
  max-width: 480px;
}

.hidden-file-input {
  display: none;
}

.spin {
  animation: spin-anim 1s linear infinite;
}

@keyframes spin-anim {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.parse-results {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  overflow-y: auto;
  padding-right: 4px;
}

/* POV 主角区域 */
.pov-section {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  background: rgba(255, 255, 255, 0.4);
  padding: 0.85rem;
  border-radius: 12px;
}

.pov-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-label {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--neu-text-primary);
}

.label-icon {
  font-size: 1.1rem;
  color: var(--neu-accent);
}

.multi-tag {
  font-size: 0.7rem;
  padding: 0.1rem 0.4rem;
  color: var(--neu-accent);
  font-weight: 600;
  border-radius: 4px;
}

.meta-hint {
  font-size: 0.75rem;
  color: var(--neu-text-secondary);
}

.entities-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 0.75rem;
}

.entity-card {
  padding: 0.75rem;
  cursor: pointer;
  border-left: 3px solid transparent;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  border-radius: 10px;
  transition: all 0.2s;
}

.entity-card.is-selected {
  border-left-color: var(--neu-accent);
  box-shadow: var(--shadow-inset-sm);
  background: rgba(230, 238, 250, 0.6);
}

.entity-card-top {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.preview-avatar,
.avatar-placeholder {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  color: var(--neu-accent);
}

.entity-name-box {
  display: flex;
  flex-direction: column;
}

.entity-name {
  font-size: 0.875rem;
  font-weight: 700;
  color: var(--neu-text-primary);
}

.entity-title {
  font-size: 0.7rem;
  color: var(--neu-text-secondary);
}

.entity-preview-text {
  font-size: 0.725rem;
  color: var(--neu-text-secondary);
  line-height: 1.35;
}

/* 标签页导航 */
.tabs-nav {
  display: flex;
  gap: 0.4rem;
  padding: 0.35rem;
  border-radius: 10px;
}

.tab-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  padding: 0.5rem 0.75rem;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--neu-text-secondary);
  background: transparent;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-btn.active {
  color: var(--neu-accent);
  background: #f0f3f8;
  box-shadow: var(--shadow-sm);
}

.tab-icon {
  font-size: 1rem;
}

/* 标签页内容 */
.tab-content {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.form-grid {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}

.vitals-row {
  grid-template-columns: 1fr 1fr 1fr;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.form-field label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--neu-text-primary);
}

.field-label-group {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.field-hint {
  font-size: 0.7rem;
  color: var(--neu-text-secondary);
}

.neu-input {
  padding: 0.55rem 0.75rem;
  font-size: 0.825rem;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  background: #f0f3f8;
  box-shadow: var(--shadow-inset-sm);
  color: var(--neu-text-primary);
  outline: none;
  font-family: inherit;
  transition: all 0.2s;
}

.neu-input:focus {
  border-color: var(--neu-accent);
}

.drive-textarea {
  resize: vertical;
}

.persona-textarea {
  resize: vertical;
  line-height: 1.5;
  font-size: 0.8rem;
}

.neu-range {
  accent-color: var(--neu-accent);
  cursor: pointer;
}

.form-box {
  padding: 0.75rem;
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}

.box-title {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--neu-accent);
}

.mini-icon {
  font-size: 0.95rem;
}

/* 物品标签与目标 */
.tag-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.item-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
  color: var(--neu-text-primary);
  border-radius: 6px;
}

.tag-remove {
  background: none;
  border: none;
  color: var(--neu-text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  padding: 0;
  font-size: 0.85rem;
}

.tag-remove:hover {
  color: var(--neu-danger);
}

.add-item-row {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.item-input {
  flex: 1;
}

.goals-list {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.goal-item-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.35rem 0.6rem;
  border-radius: 6px;
}

.goal-bullet {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--neu-accent);
}

.neu-input-inline {
  flex: 1;
  background: transparent;
  border: none;
  font-size: 0.8rem;
  color: var(--neu-text-primary);
  outline: none;
  font-family: inherit;
}

/* NPC 列表与世界书 */
.tab-top-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.tab-summary-hint {
  font-size: 0.75rem;
  color: var(--neu-text-secondary);
}

.empty-hint {
  padding: 1.5rem;
  text-align: center;
  font-size: 0.8rem;
  color: var(--neu-text-secondary);
  border-radius: 8px;
}

.npc-cards-list,
.lores-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  max-height: 380px;
  overflow-y: auto;
  padding-right: 4px;
}

.npc-edit-card,
.lore-edit-card {
  padding: 0.85rem;
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}

.npc-row-main {
  display: grid;
  grid-template-columns: 1fr 1fr 100px 36px;
  gap: 0.65rem;
  align-items: flex-end;
}

.npc-delete-btn,
.lore-delete-btn {
  height: 36px;
  background: none;
  border: none;
  color: var(--neu-text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  font-size: 1.2rem;
  transition: all 0.2s;
}

.npc-delete-btn:hover,
.lore-delete-btn:hover {
  color: var(--neu-danger);
  background: rgba(239, 68, 68, 0.1);
}

.npc-summary-textarea,
.lore-content-textarea {
  resize: vertical;
  line-height: 1.45;
  font-size: 0.8rem;
}

.lore-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
}

.lore-title-group {
  display: flex;
  gap: 0.65rem;
  flex: 1;
}

.lore-title-input {
  flex: 1;
  font-weight: 700;
}

.lore-cat-select {
  width: 170px;
}

/* 底部操作 */
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.85rem;
  margin-top: 0.5rem;
  padding-top: 0.75rem;
  border-top: 1px solid rgba(0, 0, 0, 0.05);
}
</style>
