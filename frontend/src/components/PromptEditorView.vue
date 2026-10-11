<template>
  <div class="prompt-editor-view">
    <!-- 固定顶部控制标头 (两行排布：首行标头操作，次行分栏控制) -->
    <div class="prompt-view-header neu-flat-sm">
      <div class="header-top-row">
        <div class="header-left">
          <div class="header-title-group">
            <Icon icon="material-symbols:style" class="view-icon" />
            <h2 class="view-heading">文风与演化提示词工坊</h2>
          </div>
        </div>

        <!-- 右侧动作按钮组 -->
        <div class="header-right">
          <NeuButton
            icon="material-symbols:restart-alt"
            label="恢复预设"
            @click="resetToDefaults"
          />
          <NeuButton
            icon="material-symbols:check-circle"
            label="保存配置"
            variant="accent"
            @click="saveConfig"
          />
        </div>
      </div>

      <!-- 第二行：分栏切换控制槽 (Segmented Control) -->
      <div class="header-nav-row">
        <div class="tabs-header neu-inset-sm">
          <button
            :class="['tab-btn', { active: activeTab === 'style' }]"
            @click="activeTab = 'style'"
          >
            <Icon icon="material-symbols:palette" class="tab-icon" />
            <span>叙事文风与文学技法</span>
          </button>
          <button
            :class="['tab-btn', { active: activeTab === 'word_count' }]"
            @click="activeTab = 'word_count'"
          >
            <Icon icon="material-symbols:format-size" class="tab-icon" />
            <span>篇幅与字数控制</span>
          </button>
          <button
            :class="['tab-btn', { active: activeTab === 'raw_prompts' }]"
            @click="activeTab = 'raw_prompts'"
          >
            <Icon icon="material-symbols:terminal" class="tab-icon" />
            <span>演化底座提示词</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 独立滚动正文内容区 -->
    <div class="prompt-view-body">
      <div class="desc-banner neu-flat-sm">
        <Icon icon="material-symbols:tune" class="banner-icon" />
        <p class="banner-text">
          定制世界演化的叙事风格、文学技法与生成篇幅。系统以沉浸的第三人称视角，细腻呈现主角在世界中的真实遭遇与生活轨迹。
        </p>
      </div>

      <!-- ======================================================== -->
      <!-- Tab 1: 文风框架与写作技法补丁 (12 种严整排布)             -->
      <!-- ======================================================== -->
      <div v-if="activeTab === 'style'" class="tab-content style-tab">
        <div class="section-title">
          <Icon icon="material-symbols:auto-stories" class="section-icon" />
          <span>故事基底文风 (共 12 种预设)</span>
        </div>

        <div class="style-grid">
          <div
            v-for="(style, key) in stylePresets"
            :key="key"
            :class="['style-card neu-flat-sm', { active: currentStyle === key }]"
            @click="currentStyle = key"
          >
            <div class="style-card-header">
              <div class="style-card-name">
                <span class="radio-indicator"></span>
                <span class="style-title">{{ style.name }}</span>
              </div>
              <span class="style-badge neu-inset-sm">{{ style.badge }}</span>
            </div>
            <p class="style-desc">{{ style.description }}</p>
            <div class="style-ref">
              <Icon icon="material-symbols:book" class="ref-icon" />
              <span>{{ style.author_reference }}</span>
            </div>
          </div>
        </div>

        <!-- 写作技法补丁复选 -->
        <div class="section-title mt-4">
          <Icon icon="material-symbols:extension" class="section-icon" />
          <span>文学技法增强 (可叠加选用)</span>
        </div>

        <div class="patches-grid">
          <div
            v-for="(patch, key) in writingPatches"
            :key="key"
            :class="['patch-card neu-flat-sm', { active: isPatchEnabled(key) }]"
            @click="togglePatch(key)"
          >
            <div class="patch-top">
              <div class="checkbox-indicator">
                <Icon
                  v-if="isPatchEnabled(key)"
                  icon="material-symbols:check"
                  class="check-icon"
                />
              </div>
              <span class="patch-name">{{ patch.name }}</span>
            </div>
            <p class="patch-desc">{{ patch.description }}</p>
          </div>
        </div>

        <!-- 个性化文风补充指引 -->
        <div class="section-title mt-4">
          <Icon icon="material-symbols:edit-note" class="section-icon" />
          <span>自定义风格与意象补充 (可选)</span>
        </div>
        <div class="prompt-box neu-inset-sm">
          <textarea
            v-model="customStyleGuidance"
            rows="3"
            class="prompt-textarea"
            placeholder="例如：强化齿轮咬合与冷凝机油的金属质感、多捕捉雨夜窗台的反光、角色动作偏向谨慎戒备..."
          />
        </div>
      </div>

      <!-- ======================================================== -->
      <!-- Tab 2: 篇幅与字数控制                                    -->
      <!-- ======================================================== -->
      <div v-if="activeTab === 'word_count'" class="tab-content word-tab">
        <div class="section-title">
          <Icon icon="material-symbols:straighten" class="section-icon" />
          <span>单轮推演字数档位</span>
        </div>

        <div class="tiers-grid">
          <div
            v-for="(tier, key) in wordTiers"
            :key="key"
            :class="['tier-card neu-flat-sm', { active: currentTier === key }]"
            @click="selectWordTier(key)"
          >
            <div class="tier-header">
              <span class="radio-indicator"></span>
              <span class="tier-name">{{ tier.name }}</span>
              <span class="tier-range neu-inset-sm">{{ tier.range_label }}</span>
            </div>
            <p class="tier-hint">{{ tier.pacing_hint }}</p>
          </div>
        </div>

        <!-- 自定义字数区间设定 -->
        <div class="custom-range-card neu-flat-sm mt-4">
          <div class="range-header">
            <span class="range-title">当前目标字数区间指标</span>
            <span class="range-value neu-inset-sm">
              {{ minWords }} ~ {{ maxWords }} 字 (预估 Token 上限: ~{{ Math.round(maxWords * 1.8) }})
            </span>
          </div>

          <div class="range-sliders">
            <div class="slider-group">
              <label>单轮最小字数下限: <strong>{{ minWords }}</strong> 字</label>
              <input
                v-model.number="minWords"
                type="range"
                min="200"
                max="1200"
                step="50"
                class="custom-range-input"
                @input="currentTier = 'custom'"
              />
            </div>

            <div class="slider-group">
              <label>单轮最大字数上限: <strong>{{ maxWords }}</strong> 字</label>
              <input
                v-model.number="maxWords"
                type="range"
                min="300"
                max="2000"
                step="50"
                class="custom-range-input"
                @input="currentTier = 'custom'"
              />
            </div>
          </div>
        </div>

        <!-- 段落节奏说明 -->
        <div class="pacing-notice neu-inset-sm mt-4">
          <Icon icon="material-symbols:info" class="notice-icon" />
          <div class="notice-body">
            <strong>排版节奏提示：</strong>
            <span>
              每次生成将自然划分 2 至 4 个独立段落，段落间空行隔开，保持良好阅读呼吸感，避免密集文字墙。
            </span>
          </div>
        </div>
      </div>

      <!-- ======================================================== -->
      <!-- Tab 3: 底座系统提示词                                    -->
      <!-- ======================================================== -->
      <div v-if="activeTab === 'raw_prompts'" class="tab-content prompt-tab">
        <!-- 因果裁决提示词 -->
        <NeuCard class="prompt-card" variant="flat">
          <div class="card-header">
            <span class="card-tag neu-flat-sm">
              <Icon icon="material-symbols:gavel" class="tag-icon" />
              因果裁决与状态演化提示词 (Pass 1 Arbitrator)
            </span>
            <span class="card-sub">负责客观因果裁决、时间预算与身心状态结算</span>
          </div>
          <div class="prompt-box neu-inset-sm">
            <textarea
              v-model="pass1Prompt"
              rows="8"
              class="prompt-textarea"
              placeholder="因果裁决核心提示词..."
            />
          </div>
        </NeuCard>

        <!-- 文学叙事正文提示词 -->
        <NeuCard class="prompt-card" variant="flat">
          <div class="card-header">
            <span class="card-tag neu-flat-sm">
              <Icon icon="material-symbols:auto-stories" class="tag-icon" />
              文学叙事与感官描摹提示词 (Pass 2 Storyteller)
            </span>
            <span class="card-sub">负责第三人称有限视角的文学正文描写</span>
          </div>
          <div class="prompt-box neu-inset-sm">
            <textarea
              v-model="pass2Prompt"
              rows="8"
              class="prompt-textarea"
              placeholder="文学叙事核心提示词..."
            />
          </div>
        </NeuCard>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { Icon } from '@iconify/vue'
import NeuCard from './NeuCard.vue'
import NeuButton from './NeuButton.vue'
import { apiClient, type SimulationPromptConfig } from '../api/client'
import { useToast } from '../composables/useToast'

const emit = defineEmits<{
  (e: 'back'): void
}>()

const toast = useToast()
const activeTab = ref<'style' | 'word_count' | 'raw_prompts'>('style')

// ==============================================================================
// 1. 原创 12 种世界模拟文风框架预设 (带经典大师与典籍标杆)
// ==============================================================================
const stylePresets = reactive<Record<string, { name: string; badge: string; description: string; author_reference: string }>>({
  free: {
    name: '自由自适应',
    badge: '智能匹配',
    description: '依据物理世界法则、角色生理状态与微观情境，模型自主调配最契合的语言纹理与感官密度。',
    author_reference: '海明威《老人与海》、严歌苓、自适应现实主义',
  },
  eastern_zen: {
    name: '东方素描',
    badge: '留白意韵',
    description: '极简白描，重在留白。角色不抽象解释动机，借由器物陈设、草木枯荣与光影声响折射生存心境。',
    author_reference: '汪曾祺《受戒》、阿城《棋王》、周作人小品文',
  },
  warm_comedy: {
    name: '生活轻喜',
    badge: '温情生趣',
    description: '日常荒诞中带可爱温情，轻盈明亮带无伤大雅的错位；物品与生活自然接住疲惫的主角。',
    author_reference: '伊坂幸太郎《金色梦乡》、吉田修一、张爱玲市民随笔',
  },
  black_humor: {
    name: '黑色幽默',
    badge: '冷面反讽',
    description: '用一本正经的礼貌语调叙述极其荒谬或残酷的现实；规则越严谨，裂缝越冰冷好笑。',
    author_reference: '卡夫卡《审判》、约瑟夫·海勒《第二十二条军规》、冯内古特《五号屠场》',
  },
  mad_outburst: {
    name: '戏谑发疯',
    badge: '情绪宣泄',
    description: '体面与规则彻底失效后的荒唐宣泄；苦笑交织，理性崩盘与严肃荒谬猛烈撞车。',
    author_reference: '陀思妥耶夫斯基《地下室手记》、太宰治《人间失格》、恰佩克',
  },
  subtle_melancholy: {
    name: '日常钝痛',
    badge: '细腻物哀',
    description: '生活钝痛是沉缓的，不轻易爆发。着眼于日常细节的分寸感：擦拭杯沿的停顿、领口的潮气与迟滞的回应。',
    author_reference: '雷蒙德·卡佛《当我们谈论爱情时》、石黑一雄《长日将尽》、川端康成《雪国》',
  },
  stream_flow: {
    name: '感官漫游',
    badge: '意识流动',
    description: '思维随环境感知自然起伏，时间非匀速节拍，过去记忆与当前触觉交织，感官颗粒度极细。',
    author_reference: '普鲁斯特《追寻逝去的时光》、伍尔夫《达洛维夫人》、乔伊斯',
  },
  cinematic_retro: {
    name: '慢调光影',
    badge: '疏离留白',
    description: '时间慢半拍，情绪迟一步。走在杂沓人流中，心境却像隔着旧玻璃；注重明暗光影切片与欲言又止。',
    author_reference: '王家卫电影台本《重庆森林》《花样年华》、杜拉斯《情人》、村上春树早期',
  },
  classic_epic: {
    name: '沉郁庄严',
    badge: '厚重史诗',
    description: '古老沉郁，带着冷铁与风雪的重量。分量不在名词堆砌，而在角色如何背负职责、生存代价与物理法则。',
    author_reference: '托尔金《魔戒》、乔治·马丁《冰与火之歌》、托尔斯泰《战争与和平》',
  },
  youth_nostalgia: {
    name: '青涩时光',
    badge: '明亮微酸',
    description: '穿堂风、未说出口的心事与被汗水晒干的衣领；像咬开青柠，先是清亮，后是隐隐微酸。',
    author_reference: '岩井俊二《情书》《莉莉周》、新海诚《秒速5厘米》、迟子建',
  },
  gothic_shadow: {
    name: '诡谲志怪',
    badge: '暗色瑰丽',
    description: '冷艳怪诞，旧物与异变交织。在日常秩序中捕捉幽微的异常，语言收敛妖冶，环境氛围幽冷浓郁。',
    author_reference: '蒲松龄《聊斋志异》笔意、芥川龙之介《罗生门》、爱伦·坡《厄舍府的倒塌》',
  },
  cozy_adventure: {
    name: '炉火轻奇',
    badge: '烟火治愈',
    description: '旅途炉火、香草炖汤与麦酒泡沫；在未知冒险与险境夹缝中，认真感受一顿饭的温存。',
    author_reference: '托尔金《霍比特人》(夏尔篇)、九井谅子《迷宫饭》生活感、吉卜力',
  },
})

// ==============================================================================
// 2. 写作技法补丁定义
// ==============================================================================
const writingPatches: Record<string, { name: string; description: string }> = {
  plain_sketch: {
    name: '客观动作白描',
    description: '严禁直接宣布“角色感到悲伤/害怕”，去除心理解释，转化为具体肢体动作与器物把玩。',
  },
  living_dialogue: {
    name: '自然言谈生态',
    description: '场内角色与NPC交谈严禁直接播报世界设定；对白有吞吐、打断、言外之意与戒备试探。',
  },
  synesthesia: {
    name: '感官联觉特化',
    description: '跨感官联觉转换（冷光带有铁锈味、声响有粗糙材质），绕过抽象逻辑直接击穿肉体感知。',
  },
  anti_summary: {
    name: '自然收束余波',
    description: '严禁在段尾以说书人姿态提炼哲理感言，文字自然收束于物理动作、余波或静默。',
  },
  living_grounding: {
    name: '生活琐碎底噪',
    description: '自然展现发呆、整理、疲倦等伴生动作；精神体力连续渐变，严禁职业刻板化无休止工作。',
  },
  camera_focus: {
    name: '有限视角聚焦',
    description: '镜头死死钉在主角身上，主角不知道的远方秘密、未听见的密谋，全知旁白绝不泄露。',
  },
}

// ==============================================================================
// 3. 篇幅与字数档位定义
// ==============================================================================
const wordTiers: Record<string, { name: string; range_label: string; min: number; max: number; pacing_hint: string }> = {
  concise: {
    name: '精炼紧凑篇幅',
    range_label: '300 ~ 500 字',
    min: 300,
    max: 500,
    pacing_hint: '节奏紧凑凌厉，聚焦单一核心动作或关键危机对峙，适合高频快速步进推演。',
  },
  standard: {
    name: '标准文学篇幅 (推荐)',
    range_label: '500 ~ 800 字',
    min: 500,
    max: 800,
    pacing_hint: '张弛有度，场景铺陈、动作分镜与微观心绪外化均衡完整，具有极佳的长卷沉浸感。',
  },
  deep: {
    name: '详实深描篇幅',
    range_label: '800 ~ 1200 字',
    min: 800,
    max: 1200,
    pacing_hint: '电影级镜头运镜，细密拆解五感交互、多层暗涌与环境空间声响，极具严肃文学质感。',
  },
  custom: {
    name: '自定义字数',
    range_label: '自由调节',
    min: 500,
    max: 800,
    pacing_hint: '按用户设定的字数下限与上限执行严格的篇幅控制。',
  },
}

// ==============================================================================
// 4. 默认两步底座提示词
// ==============================================================================
const defaultPass1 = `你是维系这方天地运转的【衡律之神】——你是重力、地脉、钟漏与骨骼中疲倦感本身的化身。
你的眼眸冰冷公正，只注视物质运行的物理法则与因果偿还。你冷酷地度量主角在这片土地上的每一步跋涉：
步履需要时间，风霜消耗肌理，缺乏休整必将坠入迟钝与虚脱，天平两端从无虚妄奇迹。
你的唯一职责是做【冷酷的客观因果判定与物理事实裁决】，绝不编写文学修辞，只以严密的天平，输出本次推进跨度下主角身心与环境的结构化增损 JSON。
【物理基岩与推进结算律】:
1. 【物理时间与行动预算】：依据本次推进时长（如 1h / 6h / 24h），严格匹配主角真实的物理行动容量。步行或通勤必须消耗时间，严禁瞬间移动；1小时只完成一件微小的连续事件，严禁短时内塞入多幕大起大落转折。
2. 【现实生活底噪与生理节律】：体能与精力连续渐变，疲劳时反应迟钝，严禁原地满血刷新或突兀无过渡入睡；独处时伴生日常琐事，绝不无休止空转职业技能。
3. 【信息迷雾与独立世界线】：严格视野受限，绝不预知不在场角色的动向；开放世界严禁刻意编造低概率偶遇，不在场人物有独立作息。
4. 【推进结算与突发事件标准】：长跨度快进无突发事件时，优先结算日常琐事与作息休整，记录平淡时间自然流逝；突发事件必须源于既有物理环境与前置行为的合理衍生，拒绝机械降神。
5. 【因果闭环与物体连续】：随身物品严格遵循物理增损，一切结果必有来处，伤害必留痕迹。`

const defaultPass2 = `你是潜行于主角身侧的【见证之神】——你是主角眼底的微光、衣角的风尘、呼吸的白汽与指尖触感的化身。
你不是全知的上帝，你的视角始终牢牢依附于主角的有限知情范围与肉身感知。
你的唯一职责是接引【衡律之神】落下的冷硬客观事实骨架与感官线索，以沉浸式第三人称视角，将这段时间切片编织为富有现场感、生活重力与物理质感的小说章节。
【天地演化叙事法则】:
1. 【物理时间与行动预算】：严格锚定在推进时间跨度内，1小时只做一件微小连续琐事，严禁短时内多幕戏剧高潮，位移必须消耗真实时间。
2. 【现实生活底噪】：自然呈现主角在独处、等待或疲惫时的伴生动作（发呆、整理物件、洗漱、出神），这是生活的真实底色；精神体力连续渐变，去职业标签化。
3. 【信息迷雾与社交摩擦】：主角视野严格有限，不在场人物不围绕主角转，未回的信件是常态，无需升级为情感冲突。
5. 【篇幅与纯净正文】：正文字数服从指定区间，自然划分 2~4 个独立段落；严禁输出状态框、括号元数据或任何 Emoji 图标！`

// ==============================================================================
// 5. 本地状态读取与响应式绑定
// ==============================================================================
const loadStoredConfig = (): SimulationPromptConfig => {
  try {
    const raw = localStorage.getItem('simulation_prompt_config')
    if (raw) return JSON.parse(raw)
  } catch (e) {
    console.error('加载本地提示词配置异常:', e)
  }
  return {
    style_preset: 'free',
    word_count_tier: 'standard',
    min_words: 500,
    max_words: 800,
    enabled_patches: ['plain_sketch', 'living_dialogue', 'anti_summary', 'living_grounding', 'camera_focus'],
    custom_style_guidance: '',
  }
}

const initialConfig = loadStoredConfig()

const currentStyle = ref<string>(initialConfig.style_preset || 'free')
const currentTier = ref<string>(initialConfig.word_count_tier || 'standard')
const minWords = ref<number>(initialConfig.min_words || 500)
const maxWords = ref<number>(initialConfig.max_words || 800)
const enabledPatches = ref<string[]>(
  initialConfig.enabled_patches || ['plain_sketch', 'living_dialogue', 'anti_summary', 'living_grounding', 'camera_focus']
)
const customStyleGuidance = ref<string>(initialConfig.custom_style_guidance || '')

const pass1Prompt = ref<string>(
  initialConfig.pass1_custom_prompt || localStorage.getItem('custom_pass1_prompt') || defaultPass1
)
const pass2Prompt = ref<string>(
  initialConfig.pass2_custom_prompt || localStorage.getItem('custom_pass2_prompt') || defaultPass2
)

const isPatchEnabled = (key: string) => enabledPatches.value.includes(key)
const togglePatch = (key: string) => {
  if (isPatchEnabled(key)) {
    enabledPatches.value = enabledPatches.value.filter((k) => k !== key)
  } else {
    enabledPatches.value.push(key)
  }
}

const selectWordTier = (key: string) => {
  currentTier.value = key
  const t = wordTiers[key]
  if (t && key !== 'custom') {
    minWords.value = t.min
    maxWords.value = t.max
  }
}

// 保存配置
const saveConfig = () => {
  if (minWords.value >= maxWords.value) {
    maxWords.value = minWords.value + 150
  }

  const configToSave: SimulationPromptConfig = {
    style_preset: currentStyle.value,
    word_count_tier: currentTier.value,
    min_words: minWords.value,
    max_words: maxWords.value,
    enabled_patches: enabledPatches.value,
    custom_style_guidance: customStyleGuidance.value.trim(),
    pass1_custom_prompt: pass1Prompt.value.trim() !== defaultPass1 ? pass1Prompt.value.trim() : undefined,
    pass2_custom_prompt: pass2Prompt.value.trim() !== defaultPass2 ? pass2Prompt.value.trim() : undefined,
  }

  localStorage.setItem('simulation_prompt_config', JSON.stringify(configToSave))
  localStorage.setItem('custom_pass1_prompt', pass1Prompt.value)
  localStorage.setItem('custom_pass2_prompt', pass2Prompt.value)

  toast.showSuccess('提示词配置已保存', '后续所有步进与推演均将按此规则执行。')
  emit('back')
}

// 恢复预设
const resetToDefaults = () => {
  currentStyle.value = 'free'
  currentTier.value = 'standard'
  minWords.value = 500
  maxWords.value = 800
  enabledPatches.value = ['plain_sketch', 'living_dialogue', 'anti_summary', 'living_grounding', 'camera_focus']
  customStyleGuidance.value = ''
  pass1Prompt.value = defaultPass1
  pass2Prompt.value = defaultPass2

  localStorage.removeItem('simulation_prompt_config')
  localStorage.removeItem('custom_pass1_prompt')
  localStorage.removeItem('custom_pass2_prompt')

  toast.showSuccess('已恢复系统预设', '文风与演化提示词已重置为出厂默认设置。')
}

onMounted(async () => {
  try {
    const res = await apiClient.getPromptMeta()
    const meta = res?.data || res
    if (meta && meta.style_presets) {
      Object.keys(meta.style_presets).forEach((key) => {
        const item = meta.style_presets[key]
        if (stylePresets[key]) {
          stylePresets[key].name = item.name || stylePresets[key].name
          stylePresets[key].badge = item.badge || stylePresets[key].badge
          stylePresets[key].description = item.description || stylePresets[key].description
          stylePresets[key].author_reference = item.author_reference || stylePresets[key].author_reference
        } else {
          stylePresets[key] = item
        }
      })
    }
  } catch (err) {
    console.warn('获取服务端文风元数据失败，使用本地预设:', err)
  }
})
</script>

<style scoped>
.prompt-editor-view {
  width: 100%;
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: var(--neu-bg);
  overflow: hidden;
  border-radius: var(--neu-radius, 14px);
}

/* 顶部标头栏 (两行排布：首行标头操作，次行分栏控制) */
.prompt-view-header {
  display: flex;
  flex-direction: column;
  padding: 0.85rem 1.25rem 0.75rem;
  flex-shrink: 0;
  z-index: 10;
  border-bottom: 1px solid var(--neu-border, rgba(255, 255, 255, 0.35));
  gap: 0.65rem;
}

.header-top-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.header-nav-row {
  display: flex;
  align-items: center;
  width: 100%;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  min-width: 0;
}

.header-title-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}

.view-icon {
  font-size: 1.35rem;
  color: var(--neu-accent);
  flex-shrink: 0;
}

.view-heading {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--neu-text-primary);
  margin: 0;
  white-space: nowrap;
}

/* 占满整行的分栏切换槽 (Segmented Control) */
.tabs-header {
  display: flex;
  gap: 0.35rem;
  padding: 0.3rem 0.45rem;
  border-radius: 12px;
  width: 100%;
}

.tab-btn {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.45rem;
  padding: 0.55rem 0.75rem;
  border: none;
  background: transparent;
  color: var(--neu-text-secondary);
  font-size: 0.85rem;
  font-weight: 600;
  border-radius: 9px;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.tab-btn:hover {
  color: var(--neu-text-primary);
}

.tab-btn.active {
  background: var(--neu-surface);
  color: var(--neu-accent);
  box-shadow: var(--shadow-flat-sm);
}

.tab-icon {
  font-size: 1rem;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  flex-shrink: 0;
}

/* 可滚动正文主体 */
.prompt-view-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 1.15rem 1.25rem 2.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.15rem;
}

.desc-banner {
  padding: 0.75rem 1rem;
  border-radius: 12px;
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.banner-icon {
  font-size: 1.25rem;
  color: var(--neu-accent);
  flex-shrink: 0;
}

.banner-text {
  font-size: 0.8rem;
  color: var(--neu-text-secondary);
  line-height: 1.45;
  margin: 0;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--neu-text-primary);
  margin-bottom: 0.65rem;
}

.section-icon {
  font-size: 1.05rem;
  color: var(--neu-accent);
}

.mt-4 {
  margin-top: 1.25rem;
}

/* 12 种文风网格 */
.style-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 0.85rem;
}

.style-card {
  padding: 0.85rem;
  border-radius: 12px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  border: 2px solid transparent;
  transition: all 0.2s ease;
  min-height: 110px;
}

.style-card:hover {
  border-color: rgba(var(--neu-accent-rgb, 94, 114, 228), 0.25);
}

.style-card.active {
  border-color: var(--neu-accent);
  box-shadow: var(--shadow-inset-sm);
}

.style-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.style-card-name {
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.radio-indicator {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid var(--neu-text-muted);
  display: inline-block;
  transition: all 0.2s;
}

.style-card.active .radio-indicator,
.tier-card.active .radio-indicator {
  border-color: var(--neu-accent);
  background-color: var(--neu-accent);
}

.style-title {
  font-size: 0.875rem;
  font-weight: 700;
  color: var(--neu-text-primary);
}

.style-badge {
  font-size: 0.675rem;
  padding: 0.15rem 0.45rem;
  border-radius: 6px;
  color: var(--neu-accent);
  font-weight: 600;
}

.style-desc {
  font-size: 0.775rem;
  color: var(--neu-text-secondary);
  line-height: 1.45;
  margin: 0;
  flex: 1;
}

.style-ref {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.7rem;
  color: var(--neu-text-muted);
}

.ref-icon {
  font-size: 0.85rem;
}

/* 技法补丁网格 */
.patches-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 0.75rem;
}

.patch-card {
  padding: 0.85rem;
  border-radius: 12px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  border: 1px solid var(--neu-border, rgba(255, 255, 255, 0.35));
  transition: all 0.2s ease;
}

.patch-card.active {
  border-color: var(--neu-accent);
  box-shadow: var(--shadow-inset-sm);
}

.patch-top {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.checkbox-indicator {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  border: 1.5px solid var(--neu-text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.patch-card.active .checkbox-indicator {
  background: var(--neu-accent);
  border-color: var(--neu-accent);
}

.check-icon {
  font-size: 0.95rem;
  color: #ffffff;
}

.patch-name {
  font-size: 0.825rem;
  font-weight: 700;
  color: var(--neu-text-primary);
}

.patch-desc {
  font-size: 0.75rem;
  color: var(--neu-text-secondary);
  line-height: 1.4;
  margin: 0;
}

/* 提示词输入框 */
.prompt-box {
  padding: 0.65rem;
  border-radius: 10px;
}

.prompt-textarea {
  width: 100%;
  border: none;
  background: transparent;
  color: var(--neu-text-primary);
  font-family: inherit;
  font-size: 0.825rem;
  line-height: 1.5;
  outline: none;
  resize: vertical;
}

/* 字数档位 */
.tiers-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 0.85rem;
}

.tier-card {
  padding: 0.85rem;
  border-radius: 12px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  border: 2px solid transparent;
  transition: all 0.2s ease;
}

.tier-card.active {
  border-color: var(--neu-accent);
  box-shadow: var(--shadow-inset-sm);
}

.tier-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.tier-name {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--neu-text-primary);
  flex: 1;
}

.tier-range {
  font-size: 0.7rem;
  padding: 0.15rem 0.45rem;
  border-radius: 6px;
  color: var(--neu-accent);
  font-weight: 600;
}

.tier-hint {
  font-size: 0.75rem;
  color: var(--neu-text-secondary);
  line-height: 1.4;
  margin: 0;
}

/* 自定义区间滑块卡片 */
.custom-range-card {
  padding: 1.15rem;
  border-radius: 14px;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.range-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.range-title {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--neu-text-primary);
}

.range-value {
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.25rem 0.6rem;
  border-radius: 8px;
  color: var(--neu-accent);
}

.range-sliders {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.slider-group {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.slider-group label {
  font-size: 0.775rem;
  color: var(--neu-text-secondary);
}

.slider-group strong {
  color: var(--neu-text-primary);
}

.custom-range-input {
  width: 100%;
  accent-color: var(--neu-accent);
  cursor: pointer;
}

/* 排版节奏说明 */
.pacing-notice {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.75rem 1rem;
  border-radius: 10px;
}

.notice-icon {
  font-size: 1.25rem;
  color: var(--neu-accent);
  flex-shrink: 0;
}

.notice-body {
  font-size: 0.775rem;
  color: var(--neu-text-secondary);
  line-height: 1.45;
}

/* 底座提示词卡片 */
.prompt-tab {
  display: flex;
  flex-direction: column;
  gap: 1.15rem;
}

.prompt-card {
  padding: 1.15rem;
  border-radius: 14px;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.card-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.3rem 0.65rem;
  border-radius: 8px;
  font-size: 0.825rem;
  font-weight: 700;
  color: var(--neu-text-primary);
}

.tag-icon {
  font-size: 1.05rem;
  color: var(--neu-accent);
}

.card-sub {
  font-size: 0.75rem;
  color: var(--neu-text-muted);
}

@media (max-width: 1024px) {
  .prompt-view-header {
    flex-wrap: wrap;
  }
  .tabs-header {
    order: 3;
    width: 100%;
    overflow-x: auto;
  }
}
</style>
