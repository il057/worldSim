# 模块 05：UI/UX 新拟态设计与组件架构规范 (Neumorphic Spec)

---

## 1. 视觉设计理念与新拟态规范

新拟态（Neumorphic / Soft UI）的本质是通过模拟单一平行光源在物体表面投射形成的柔和双向阴影（受光高亮与背光暗影），营造出犹如从背景中“挤压浮现”或“内凹压入”的物理质感。

### 1.1 全局色彩与 CSS 变量体系
整体基调采用干净、柔和、低饱和度的冷灰/暖灰色调，严禁刺眼的高饱和对比色。系统支持浅色（Light）、深色（Dark）与跟随系统（Auto）三种模式，并支持 7 款精调强调色及自定义十六进制色彩。

```css
/* 核心设计令牌 (Design Tokens - 浅色模式) */
:root {
  --neu-bg: #e6e9ef;
  --neu-surface: #e6e9ef;
  
  /* 双向阴影基色 (左上方为平行光源: 亮部与暗部) */
  --neu-light: #ffffff;
  --neu-dark: #c4c9d4;
  
  --neu-accent: #5e72e4;
  --neu-accent-hover: #4b5ecc;
  --neu-text-primary: #2d3748;
  --neu-text-secondary: #718096;
  --neu-text-muted: #a0aec0;
  --neu-border: rgba(255, 255, 255, 0.45);

  /* 文学对白与特殊格式自适应设计令牌（随主题色与深浅模式纯动态 HSL 衍生，绝不硬编码） */
  --dialogue-double: var(--neu-accent);       /* 双引号对白（随主题色动态明暗映射） */
  --dialogue-corner: var(--neu-accent-hover); /* 角标引『』「」（主题邻近色阶/层次微光） */
  --dialogue-single: var(--neu-accent);       /* 单引号心理（主题色柔和变体） */

  /* 基础阴影公式 */
  --shadow-flat: 6px 6px 14px var(--neu-dark), -6px -6px 14px var(--neu-light);
  --shadow-flat-sm: 3px 3px 7px var(--neu-dark), -3px -3px 7px var(--neu-light);
  --shadow-hover: 8px 8px 18px var(--neu-dark), -8px -8px 18px var(--neu-light);
  --shadow-active: inset 3px 3px 6px var(--neu-dark), inset -3px -3px 6px var(--neu-light);
  --shadow-inset: inset 5px 5px 10px var(--neu-dark), inset -5px -5px 10px var(--neu-light);
  --shadow-inset-sm: inset 2px 2px 5px var(--neu-dark), inset -2px -2px 5px var(--neu-light);
}

/* 沉浸式新拟态深色模式设计令牌 (Dark Mode) */
[data-theme="dark"] {
  --neu-bg: #1c2027;
  --neu-surface: #1c2027;
  --neu-light: #272d37;
  --neu-dark: #121419;
  
  --neu-text-primary: #e2e8f0;
  --neu-text-secondary: #94a3b8;
  --neu-text-muted: #64748b;
  --neu-border: rgba(255, 255, 255, 0.08);

  /* 文学对白深色高对比微光（随 activeColor 由 useTheme 动态计算注入，默认回退至主题变量） */
  --dialogue-double: var(--neu-accent);
  --dialogue-corner: var(--neu-accent-hover);
  --dialogue-single: var(--neu-accent);

  --shadow-flat: 6px 6px 14px var(--neu-dark), -6px -6px 14px var(--neu-light);
  --shadow-flat-sm: 3px 3px 7px var(--neu-dark), -3px -3px 7px var(--neu-light);
  --shadow-hover: 8px 8px 18px var(--neu-dark), -8px -8px 18px var(--neu-light);
  --shadow-active: inset 3px 3px 6px var(--neu-dark), inset -3px -3px 6px var(--neu-light);
  --shadow-inset: inset 5px 5px 10px var(--neu-dark), inset -5px -5px 10px var(--neu-light);
  --shadow-inset-sm: inset 2px 2px 5px var(--neu-dark), inset -2px -2px 5px var(--neu-light);
}
```

### 1.2 主题色与外观控制架构 (`useTheme.ts`)
- **预设色系 (Presets)**：经典靛蓝 (`#5e72e4`)、极光湖蓝 (`#0ea5e9`)、翡翠青碧 (`#10b981`)、琉璃琥珀 (`#f59e0b`)、绯红蔷薇 (`#f43f5e`)、暮光罗兰 (`#8b5cf6`)、玄石冷墨 (`#64748b`)。
- **自定义拾色**：支持十六进制原生拾色器，动态计算加深悬停色（Hover Color）及 RGB 数组，即时注入 `--neu-accent`、`--neu-accent-hover` 与 `--neu-accent-rgb`。
- **DiceBear 头像联动**：`useTheme` 提供统一的 `getDicebearAvatarUrl`，DiceBear Slice 的背景色 (`backgroundColor`) 随深浅模式动态适配，人像点缀色 (`bodyColor`) 动态同步当前主题主色调。
- **顶部微光进度条联动**：演化长卷标头进度槽使用 `linear-gradient(90deg, var(--neu-accent) 0%, var(--neu-accent-hover) 100%)`。
- **紧凑折叠与右栏看板原位切换**：系统设置与主题调整采用右栏原位面板 `SystemConfigPanel`（零 Overlay、零全屏遮罩），点击顶栏「设置」时直接占用右侧看板区域；在调换浅色/深色/跟随系统模式及 7 款强调色（Accent Color）时，左侧导航与中间演化长卷毫无阻挡、实时响应并一览无余；推演采样参数（温度、Top P、存在/频率惩罚、上下文上限、同步步长）提供轻量级 Neumorphic 折叠手风琴卡片，默认收起并展示参数摘要，防止菜单纵向过长。

---

## 2. 全局图标规范（Strict Iconify Rules）

**铁律：全工程绝对禁止使用任何 Emoji 图标。**
所有图标统一使用 `@iconify/vue` 组件，且图标集锁定为 `material-symbols`（线性/圆润规范）。

### 常用核心图标规范

| 业务含义 | 规定图标标识 |
| :--- | :--- |
| **世界时钟 / 时间推进** | `material-symbols:schedule` / `material-symbols:timelapse` |
| **小说时间轴 / 故事切片** | `material-symbols:history` / `material-symbols:timeline` |
| **角色 / 身份信息** | `material-symbols:account-circle` / `material-symbols:badge` |
| **背包 / 物品清单** | `material-symbols:inventory-2` |
| **健康 / 精力体能** | `material-symbols:vital-signs` / `material-symbols:bolt` |
| **休眠 / 就寝状态** | `material-symbols:bedtime` / `material-symbols:nightlight` |
| **心理情绪 / 精神** | `material-symbols:psychology` |
| **智能续写按钮 (续写)** | `material-symbols:auto-stories` |
| **推进步进按钮 (+1h)** | `line-md:chevron-right` |
| **阶段快进按钮 (+6h)** | `line-md:chevron-double-right` |
| **跨日跃迁按钮 (+24h)** | `line-md:chevron-triple-right` |
| **突发事件触发按钮** | `material-symbols:crisis-alert` / `material-symbols:bolt` |
| **重置 / 回滚** | `material-symbols:restart-alt` |

---

## 3. 类似 SillyTavern 架构的双抽屉式沉浸式 UI 布局规范

系统采用“顶部全局功能条 + 左侧目录抽屉 + 中间小说正文长卷 + 右侧常驻看板”的三栏架构，并实现深度移动端自适应。

```
+---------------------------------------------------------------------------------------------------------------+
| TOP NAV BAR (新拟态全局核心控制条):                                                                           |
| [左抽屉开关] [时钟: 霜降月 14日 22:00] [清醒/休眠] | [推进: 续写 | +1h | +6h | +24h | 突发事件] | [提示词] [世界书] [设置] [重置] |
+-----------------------------------+-------------------------------------------+-------------------------------+
| LEFT DRAWER (左侧菜单抽屉):       | CENTER: 场景小说时间轴阅读长卷 (Novel Stream)| RIGHT DASHBOARD (右侧常驻看板):|
| [标签 1: 故事编年索引]            | - 沉浸式第三人称小说长卷                  | - PC 端始终常驻显示，无多余标签|
|   - 每一刻的时空/事实骨架锚点列表 | - 凸起新拟态卡片，舒适字号与行间距        | - 头像/核心执念/生理与即时节律 |
|   - 点击快速平滑滚动定位到该切片  | - 可折叠 Pass 1 裁决骨架与 Delta 检视器   | - 随身背包物品/当前推进目标栈  |
| [标签 2: 角色名录与切换]          | - 手机拟真卡片（私信/朋友圈/论坛 BBS）    | - 移动端在屏幕窄小时滑出展示   |
|   - 角色头像/头衔/姓名卡片        |                                           |                               |
|   - [新建] / [导入]     |                                           | (提示词/世界书/突发事件通过   |
|   - 一键切换当前观察视角          |                                           |  Header 呼出弹窗，不挤占看板) |
+-----------------------------------+-------------------------------------------+-------------------------------+
| MOBILE BOTTOM BAR (移动端底部浮动控制栏, 仅在屏幕宽度 < 1024px 时呈现):                                       |
| [续写]       [+1h 步进]       [+6h 快进]       [+24h 跨日]       [突发事件]       [角色看板]                  |
+---------------------------------------------------------------------------------------------------------------+
```

### 3.1 界面去冗余与交互分层原则
1. **Header 职责纯粹化**：Header 仅承载全局环境控制（时钟、推进、提示词、世界书、系统设置、重置）；角色新建/导入归入左侧“角色菜单”，右侧看板常驻显示；
2. **看板常驻化 (Permanent Dashboard)**：PC 端右侧 Living State 看板常驻展现，不设置标签切换与关闭按钮；
3. **分层工作区与原位视口切换 (In-place Views & Right Panel Integration)**：
   - **设置右栏原位化 (`SystemConfigPanel`)**：点击 Header 的 [设置] 按钮时，右侧常驻面板平滑切换为系统设置与外观（右上角提供关闭返回按键），不创建浮层遮罩（Overlay），中间长卷与左侧角色列表保持可见与交互，改色与深浅切换所见即所得；
   - **工作台原位切换 (`WorldLoreView` & `PromptEditorView`)**：点击 Header 的 [世界书] 或 [文风与设定] 按钮时，在中间主视口区域（`center-novel-stream`）以原位工作台方式平滑切换展示；世界书条目采用单列全宽自适应，正文长设定支持 2 行折叠与平滑展开，顶栏状态联动控制关闭；使用 `v-show` 保持长卷阅读滚动位置无损保留；
4. **桌面端视口三栏常驻贴底与长卷沉浸无界阅读 (Desktop Viewport App Layout & Immersive Stream)**：
   - PC 宽屏端采用应用级视口全屏布局（`height: 100vh; overflow: hidden;`），顶部导航栏固定，工作区（`workspace-container`）占据视口剩余空间，解除静态 `max-width` 限制以全宽充满（`width: 100%`），使左右抽屉在大屏（1920px+）下像素级紧贴屏幕左右边缘，与顶部 Header 两端严密垂直对齐；
   - 左侧角色目录抽屉与右侧看板抽屉高度撑满工作区（`height: 100%;`），始终紧贴屏幕底部，两栏内部各自独立滚动；
   - **材质底色严格统一（Single Neumorphic Surface）**：全站卡片（包括中间 `TimelineLogItem` 与两侧抽屉、顶栏）底色严格统一继承全局 CSS 变量 `--neu-surface`（`#e6e9ef`），严禁在正文卡片中私自硬编码覆盖泛白底色（如 `#f0f3f8`），确保“同一块物理材质由光影浮起”的正统新拟态质感；
   - **中间长卷沉浸化与悬空滚动条去噪**：中间小说正文流（`center-novel-stream`）自包含独立平滑滚动，并隐藏原生外部悬空滚动条（`scrollbar-width: none; ::-webkit-scrollbar: none;`），保持视觉纯净；
   - **标头与微光阅读进度条常驻顶端**：演化长卷标头（`stream-top-bar`）作为中间栏的固定顶层结构（`flex-shrink: 0; z-index: 10;`），与下方正文切片可滚动视口（`stream-scroll-viewport`）解耦。标头底部的 2.5px 微光渐变阅读进度条始终稳固常驻在顶部，向下滚动时随阅读深度平滑生长，绝不随正文滚出视口；正文卡片平滑从标头下方穿过；
5. **移动端深度自适应 (Mobile Responsive Adaptation)**：
   - 在移动端或窄屏设备（宽度 < 1024px）下，左侧菜单与右侧看板自动转换为滑出式覆盖抽屉（Overlay Drawer），带有毛玻璃背板遮罩（Backdrop）；
   - 移动端顶部仅保留精简时钟、左侧抽屉开关与右侧多功能图标，步进按钮与看板按钮自动收纳至移动端专用的底部拇指操作栏（Bottom Floating Bar），避免按钮换行溢出；
   - 支持在角色卡片、名录以及看板中以微凸外圈无损展示酒馆 PNG 角色头像。

### 3.2 左侧目录抽屉 (`CharacterDrawer`) 与头像降级规范
1. **分段切换槽与操作按钮层级解耦**：
   - 头部标签页切换（`drawer-tabs`）统一采用物理内凹槽位规范（`neu-inset-sm`），激活标签呈现轻拟态凸起滑块（`neu-flat-sm`），与操作类独立按钮严格区分，杜绝外观重叠与视觉竞争；
   - 角色名录操作栏（`roster-actions`）采用严格全宽双列等宽网格（`grid-template-columns: 1fr 1fr; gap: 0.6rem;`），消除右侧留白错位，与下方角色卡片边距像素级对齐；
   - 主次操作触感分层：「新建」赋予主操作微渐变背景与微光边框，「导入」采用高光次操作拟态。
2. **头像三级优雅降级管道 (3-Tier Avatar Pipeline)**：
   - 第一级（自定义/酒馆卡）：优先渲染角色原生 `avatar_url`；
   - 第二级（DiceBear Slice）：若 `avatar_url` 缺省或图片加载损坏（`@error`），自动调用贴合项目冷灰低饱和调性的 DiceBear Slice 接口（`https://api.dicebear.com/10.x/slice/svg?seed=...`），根据角色姓名生成独一无二的高审美矢量头像；
   - 第三级（SVG 最终兜底）：若在离线网络环境下 DiceBear 亦加载失败，无缝切入 `@iconify/vue` 的 `material-symbols:account-circle` 矢量图标兜底，杜绝破图、杜绝 Emoji。

---

## 4. 前端组件开发指南与架构模式

AI 开发者在实现前端组件时，应当采用组合式 API 与高复用模式：

1. **`NeuCard`（新拟态卡片）**：
   - 支持 `raised`（凸起，用于小说正文章节与独立面板）和 `inset`（内凹，用于指标背景与槽位）；
   - 内置平滑的过渡动画，提供悬浮立体微位移。
2. **`NeuButton`（纯图标与纯按钮）及核心推演按键群规范**：
   - 必须强制接收 `material-symbols` 标识作为 Iconify 来源；
   - 封装加载状态（Loading）与激活状态（Active Inset Shadow）；
   - **核心沙盒推进按键槽（`stepper-controls neu-inset-sm`）**：
     * 容器采用物理内凹槽位（`--shadow-inset-sm`），各按钮如同精密仪器按键嵌于槽中；
     * **常规步进按钮（+1h / +6h / +24h）**：统一采用微凸物理按键（`var(--shadow-flat-sm)` 与 `1px solid var(--neu-border)`），悬停轻微浮起（`-1px` 与 `--shadow-hover`），点击物理下沉（`+0.5px` 与 `--shadow-active`）；
     * **智能续写按钮（`continue-btn`）**：作为主推进核心，采用光感微弧切面（`linear-gradient` 柔和叠加主题色微光）、物理双向阴影（`--shadow-flat-sm`）、顶部受光倒角高光（`inset 1px 1px 1.5px var(--neu-light)`）与背向暗倒角，悬停伴随主题光晕扩散与图标微倾旋转；
     * **突发事件按键（`incident-btn`）**：作为变数干预按键，采用 3D 立体微拟态材质，受光面由左上平行光源投射出顶角高光（`inset 1px 1px 1.5px rgba(255,255,255,0.45)`），右下背光面形成实体倒角厚度暗影（`inset -1px -1px 2px rgba(0,0,0,0.22)`），外部继承全局双向阴影公式（`--shadow-flat-sm`）并辅以主题辉光，点击时内凹陷入槽中。
3. **`NeuMeter`（新拟态生理指标槽）**：
   - 采用外凹槽内微凸渐变填充的形式，直观反映健康值（Health）与精力值（Stamina）。
4. **`TimelineLogItem`（故事切片组件与神性两步楼层交互）**：
   - 专注于展现文学正文与拟真手机卡片，正文支持将普通段落与手机交互组件混排；
   - **推演交互无顶栏干扰**：屏幕顶部不设置推演状态横幅，推演触发时在长卷底部挂载最新楼层卡片并平滑滚动到视口；
   - **非流式推演态**：在最新楼层展示优雅旋转动效的“生成中...”，不暴露底层细节；
   - **流式推演神性两步态**：
     * 阶段一：展示【衡律之神】（或【变数之引】）权衡因果中；
     * 阶段二：衡律之神裁决完成后，率先在楼层上方以优雅边框卡片展现【衡律之神·因果裁决】的客观骨架回复；
     * 阶段三：紧接着展现【见证之神】正在编织，并逐字打字机流式输出纯文学正文；
   - **定稿检视器**：已落库楼层默认折叠因果裁决与状态详情，点击展开检视客观事实经过与生理/环境增量；
   - **Header 结构与操作栏规范（两行式排版与三点 SVG 交互）**：
     * **两行式统一排版**：切片头部统一采用结构分明的两行式排版。第一行居左展示刻度徽章（第 X 刻）与虚拟时间（10:00），居右承载推演状态指示与三点操作栏；第二行靠左独立展示完整地点信息（material-symbols:location-on + 地点全称，word-break: break-word），支持完整地点换行展示，保持楼层卡片排版规范；
     * 避免将所有操作按钮常驻平铺在右上角，采用优雅微小的三点 SVG 图标按钮（`material-symbols:more-horiz`）作为触发器；
     * 点击后**直接在切片 Header 右侧内联平滑水平展开**操作栏（`inline-action-bar`），杜绝使用遮挡正文的浮层 Dropdown；
     * 离开视口或点击页面外部时自动收起操作栏（Click-Outside 侦测）；
     * **编辑功能**：点击展开原位内联文本编辑器（`prose-inline-editor`），支持直接校订文学正文与字数统计，保存后原子同步后端；
     * **重写功能（Rewrite）**：仅在最新楼层展示。点击二次确认后自动撤销最新切片并调用续写接口重新推演生成；
     * **级联删除（Cascading Delete）**：删除任意历史切片时，自动级联删除该切片及其后续的所有故事切片（如删除第 2 条会自动清退 2、3、4、5 条），并自动将角色生理看板、随身物品与 NPC 关系网回滚至该时刻之前；
   - **多层次对白与引用色彩高亮**：正文段落中由双引号 `“...”`、角标引 `「...」` 与 `『...』`、单引号 `‘...’` 包裹的内容自动解析并渲染为差异化雅致色彩（深靛蓝、琥珀赭石、松石绿），提升小说对白的可读性与呼吸感；
   - **手机与社交网络拟真组件套件 (`src/components/phone/`)**：
     - `PhoneMomentsCard`：新拟态社交动态/朋友圈卡片，不展示模拟手机状态栏（无假电量/WiFi图标），采用去设备化的原生新拟态嵌入卡片，自然融入叙事长河。严格遵循纯观察者视角（无交互按钮），展示点赞与评论；
     - `PhoneForumCard`：新拟态网络论坛与社区热帖卡片（社区论坛 / 热帖讨论），展示板块徽章、发帖人、热度数据只读指示、锁定横幅与楼层回帖讨论；
     - `PhoneChatGroup`：自然融入正文流的即时通讯对话流（无外部笨重设备框，穿插于小说段落间极度轻盈流畅），左右分边新拟态气泡、语音波形卡片、定位分享与转账卡片。转账卡片备注栏精准展示附言用途（如“首期调查勘察经费”）；
     - `AvatarBadge`：采用贴合项目冷灰新拟态低饱和调性的 DiceBear Slice 风格接口生成头像，内置离线色相梯度渐变保底，绝对无 Emoji。
5. **`LivingStateSheet` 角色看板与社交关系 (NPC) 结构化展示规范**：
   - **头部主角信息区**：
     * 头像容器严格锁定正圆（`aspect-ratio: 1/1; flex-shrink: 0;`），杜绝因长身份导致的头像挤压变形；
     * 主角头衔与定位支持多标签流式拆解与弹性换行（`char-titles-wrap`），长字符串自适应包裹，绝不溢出卡片；
   - **社交关系网 (NPC)**：
     * 第一行（姓名与即时状态）：NPC 姓名设置 `white-space: nowrap; flex-shrink: 0;` 确保绝不折行被挤压；右侧支持在场标记（`在场`）及最新互动指示（`本次交集` / `新结识`）；
     * 第二行（身份定位流式区）：NPC 身份标签（`npc-relation-badge`）支持多标签自适应流式排布与换行（`npc-tags-row`），规避超长身份溢出卡片右边界；
     * 第三行（好感度与增减量）：好感度为正或零时不展示 `+` 号（直接呈现 `50 / 100`，负数保留负号）；当最新一刻推演产生好感变动时，数值左侧伴随微拟物动效增减量徽章（`+10` / `-5`）；进度条根据好感分值自适应色彩（负数警示红、低值琥珀、高值蓝绿）；
     * 第四行（人设与羁绊）：客观人设背景与特殊样式的【对该角色的态度与羁绊】独立高亮内嵌卡（`npc-attitude-card`）；
   - **生理与即时心理看板**：
     * **生理仪表盘**：健康值与精力值（`NeuMeter`）联动展示具备双向柔和立体阴影（`box-shadow: 2px 2px 5px var(--neu-dark), -2px -2px 5px var(--neu-light)`）的物理质感胶囊，杜绝扁平色块贴纸；
     * **即时心理与心境（`mood-card neu-inset-sm`）**：采用与核心内在执念一致的新拟态内凹槽位（`neu-inset-sm`）结构，顶部左侧为单行图标与标题（锁定不折行），下方展开舒适的多行正文段落（`word-break: break-word`），承载长文本叙述；
   - **正文推演增量（Delta Snapshot）全拟态微质感映射**：
     * **随身背包**：最新推演获得的物品包裹立体微凸光晕与微凹状态胶囊（`box-shadow: inset 1px 1px 2px ...`）；消耗失去物品在内凹托盘（`inventory-removed-section neu-inset-sm`）中以微浮雕删除线小卡片呈现；
     * **行动目标**：最新达成的目标以内凹槽位（`neu-inset-sm`）与微凸实体标签呈现；新增目标赋予立体微凸浮动与柔和环境光，所有微型徽章一律遵循双向光影规范，拒绝无阴影的扁平化样式。
6. **`NeuToast`（全局新拟态通知与错误指引组件）**：
   - 遵循绝对无 Emoji 规范，所有状态指示均基于 `@iconify/vue`（`material-symbols` 图标）；
   - 采用右上方浮动式立体新拟态阴影卡片（`border-radius: 14px; box-shadow: 8px 8px 18px ...`）；
   - 根据推演引擎抛出的结构化 `error_code`（如 `AUTH_FAILED`, `RATE_LIMIT_OR_QUOTA`, `MODEL_NOT_FOUND`, `NETWORK_TIMEOUT`, `PASS1_FAILED`, `PASS2_FAILED` 等），向用户提供面向操作的清晰指引（如“检查 API 设置”、“点击重试”），隐藏底层晦涩堆栈，提升用户体验。
7. **`IncidentTriggerModal`（突发事件注入模态规范）**：
   - 与全局其他模态弹窗（世界书、系统配置、AI创建角色）完全对齐设计语言：采用 `#f0f3f8` 纯净新拟态底色、顶部左侧内联 `title-icon` 与 `h3` 标题、右侧关闭按钮；
   - 保持极简沉浸，严禁在前端 UI 中向用户展示内部 Prompt 规则说明提示（如“避免违和暴力”等教条文本）；
   - 提供当前时空境遇卡片（主角、时间、地点）与可选自定义突发事件输入框，右下方统一配置“取消”与“由 AI 决定衍生 / 注入该事件”操作按钮组。
8. **`NeuConfirmModal` 与 `useConfirm`（可复用模态二次确认弹窗套件）**：
   - 统一使用模态弹窗，不使用浏览器原生 `window.confirm()` 与 `window.alert()`；
   - 基于 Promise 异步调用机制，提供 `confirm({ title, message, confirmText, cancelText, variant, icon })`，调用处无需繁复的局部状态变量；
   - 包含毛玻璃遮罩（Backdrop Blur）、平滑渐变显隐动画、支持多种操作语义徽章（危险删除 `danger`、操作警告 `warning`、常规提示 `primary`）、支持富文本/多行分段说明；支持键盘 `Escape` 快捷键退出与遮罩点击防击穿；
9. **`NeuSelect`（全功能新拟态下拉选择器组件）**：
   - 统一使用新拟态下拉组件，不使用原生 `<select>` 标签；
   - 深度贴合新拟态设计系统，收起态呈现微内凹槽位质感（`--shadow-inset`），展开态为立体浮动面板（`--shadow-flat`）；
   - 支持即时搜索过滤选项（`searchable`）、支持选项图标（`icon`）与徽章（`badge`）、自适应全宽或指定宽度、Click-Outside 自动失焦收起，并在列表容器内部采用透明导轨与胶囊滚动条，杜绝滚动条溢出容器破环外观。
10. **`TopNavBar` 顶栏三段式绝对居中与纯图标化规范**：
   - 桌面端采用 CSS Grid 三列严格对称网格布局（`grid-template-columns: 1fr auto 1fr;`），中间推演步进控制组（`.nav-section-center`）通过 `justify-self: center;` 严格锚定于屏幕中轴线，无论左右两侧元素数量和字长如何变化均不受推挤；
   - 右侧功能菜单组（文风工坊、世界书、系统设置、重置）统一采用纯图标化 38x38px 正方圆角新拟态按钮（`icon-action-btn neu-flat-sm`）搭配清晰完整的 `title` 提示框，不使用汉字文字标签；移动端自适应回退为弹性 Flex 双端对齐。
11. **原位内嵌工坊与面板交互细节优化规范**：
   - **`PromptEditorView` 文风工坊标头两行式排布**：第一行居左展示工坊标题、居右承载“恢复预设”与“保存配置”动作按钮；第二行三段式分栏控制器（Segmented Control）横向平分整行（`width: 100%`，每项 `flex: 1`），整齐大气且绝不挤压；
   - **`WorldLoreView` 世界书展开折叠纯平居中与响应式标头**：展开按钮位于卡片正中间，采用纯平透明背景与紧凑的 SVG 箭头图标；采用 DOM `scrollHeight > clientHeight + 1` 物理高度结合 `ResizeObserver` 实时检测是否被 `-webkit-line-clamp: 2` 截断超过 2 行；标头搜索框与“新增条目”按钮锁定等高 38px，窄屏下自动下沉为第二行并将新增条目文字折叠为纯 `+` 图标方圆按键；
   - **`RightPanel` 与设置面板固顶架构**：右侧抽屉采用与文风工坊一致的固顶单块标头（`right-panel-header`，上方无 border-radius，固定在面板顶部）；保存配置采用 34x34px SVG 强调色图标按钮，不设置冗余文字；设置表单在固顶标头下方独立平滑滚动。
12. **全局统一新拟态滚动条规范（全域深浅自适应）**：
   - 全局基于 CSS 变量 `--scrollbar-thumb` 与 `--scrollbar-thumb-hover` 实现胶囊滑块样式；
   - 浅色模式采用极简冷灰透明度胶囊（`rgba(160, 174, 192, 0.45)`）；深色模式切换为超低对比柔和暗调胶囊（`rgba(255, 255, 255, 0.16)`），杜绝突兀的高亮白边或反差刺眼；
   - 全局统一新拟态滚动条宽度与颜色样式，不在各子组件内部单独覆盖，保证全站滚动交互手感与视觉一致性。


