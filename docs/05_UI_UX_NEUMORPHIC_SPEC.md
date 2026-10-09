# 模块 05：UI/UX 新拟态设计与组件架构规范 (Neumorphic Spec)

---

## 1. 视觉设计理念与新拟态规范

新拟态（Neumorphic / Soft UI）的本质是通过模拟单一平行光源在物体表面投射形成的柔和双向阴影（受光高亮与背光暗影），营造出犹如从背景中“挤压浮现”或“内凹压入”的物理质感。

### 1.1 全局色彩与 CSS 变量体系
整体基调采用干净、柔和、低饱和度的冷灰/暖灰色调，严禁刺眼的高饱和对比色。

```css
/* 核心设计令牌 (Design Tokens) */
:root {
  --neu-bg: #e6e9ef;
  --neu-surface: #e6e9ef;
  
  /* 双向阴影基色 (左上方为平行光源: 亮部与暗部) */
  --neu-light: #ffffff;
  --neu-dark: #c4c9d4;
  
  --neu-accent: #5e72e4;
  --neu-text-primary: #2d3748;
  --neu-text-secondary: #718096;

  /* 基础阴影公式 */
  --shadow-flat: 6px 6px 14px var(--neu-dark), -6px -6px 14px var(--neu-light);
  --shadow-hover: 8px 8px 18px var(--neu-dark), -8px -8px 18px var(--neu-light);
  --shadow-active: inset 3px 3px 6px var(--neu-dark), inset -3px -3px 6px var(--neu-light);
  --shadow-inset: inset 5px 5px 10px var(--neu-dark), inset -5px -5px 10px var(--neu-light);
}
```

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
| **推进步进按钮 (+1h)** | `material-symbols:step-forward` |
| **阶段快进按钮 (+6h)** | `material-symbols:fast-forward` |
| **跨日跃迁按钮 (+24h)** | `material-symbols:skip-next` |
| **突发事件触发按钮** | `material-symbols:crisis-alert` / `material-symbols:bolt` |
| **重置 / 回滚** | `material-symbols:restart-alt` |

---

## 3. 类似 SillyTavern 架构的双抽屉式沉浸式 UI 布局规范

系统借鉴 SillyTavern 高度专业且紧凑的经典工作区布局，重构为“顶部全局功能条 + 左侧目录抽屉 + 中间小说正文长卷 + 右侧常驻看板”的三栏架构，并实现深度移动端自适应。

```
+---------------------------------------------------------------------------------------------------------------+
| TOP NAV BAR (新拟态全局核心控制条):                                                                           |
| [左抽屉开关] [时钟: 霜降月 14日 22:00] [清醒/休眠] | [步进: +1h | +6h | +24h | 突发事件] | [提示词] [世界书] [设置] [重置] |
+-----------------------------------+-------------------------------------------+-------------------------------+
| LEFT DRAWER (左侧菜单抽屉):       | CENTER: 场景小说时间轴阅读长卷 (Novel Stream)| RIGHT DASHBOARD (右侧常驻看板):|
| [标签 1: 故事编年索引]            | - 沉浸式第三人称小说长卷                  | - PC 端始终常驻显示，无多余标签|
|   - 每一刻的时空/事实骨架锚点列表 | - 凸起新拟态卡片，舒适字号与行间距        | - 头像/核心执念/生理与即时节律 |
|   - 点击快速平滑滚动定位到该切片  | - 可折叠 Pass 1 裁决骨架与 Delta 检视器   | - 随身背包物品/当前推进目标栈  |
| [标签 2: 角色名录与切换]          | - 彻底无任何用户文本输入框与对话气泡      | - 移动端在屏幕窄小时滑出展示   |
|   - 角色头像/头衔/姓名卡片        |                                           |                               |
|   - [快速新建] / [导入酒馆卡]     |                                           | (提示词/世界书/设置通过 Header|
|   - 一键切换当前观察视角          |                                           |  呼出独立弹窗，不挤占常驻看板)|
+-----------------------------------+-------------------------------------------+-------------------------------+
| MOBILE BOTTOM BAR (移动端底部浮动控制栏, 仅在屏幕宽度 < 1024px 时呈现):                                       |
| [+1h 步进]           [+6h 快进]           [+24h 跨日]           [触发突发事件]           [角色看板]            |
+---------------------------------------------------------------------------------------------------------------+
```

### 3.1 界面去冗余与交互分层原则
1. **Header 职责纯粹化**：Header 不保留角色新建/导入按钮（统一归入左侧“角色菜单”内管理），不保留看板折叠按钮（看板常驻）。仅作为全局环境控制（时钟、推进、提示词、世界书、系统设置、重置）；
2. **看板常驻化 (Permanent Dashboard)**：PC 端右侧 Living State 看板常驻展现，去除所有多余的标签切换和关闭按钮；
3. **工具与法则弹窗化 (Modals)**：点击 Header 的 [提示词]、[世界书]、[设置] 时，分别呼出专用的大尺寸新拟态模态弹窗，操作完毕即可关闭，完全不破坏小说长卷与右侧常驻角色状态的对照体验；
4. **移动端深度自适应 (Mobile Responsive Adaptation)**：
   - 在移动端或窄屏设备（宽度 < 1024px）下，左侧菜单与右侧看板自动转换为滑出式覆盖抽屉（Overlay Drawer），带有毛玻璃背板遮罩（Backdrop）；
   - 移动端顶部仅保留精简时钟、左侧抽屉开关与右侧多功能图标，步进按钮与看板按钮自动收纳至移动端专用的底部拇指操作栏（Bottom Floating Bar），彻底解决按钮换行溢出的问题；
   - 支持在角色卡片、名录以及看板中以微凸外圈无损展示酒馆 PNG 角色头像。

---

## 4. 前端组件开发指南与架构模式

AI 开发者在实现前端组件时，应当采用组合式 API 与高复用模式：

1. **`NeuCard`（新拟态卡片）**：
   - 支持 `raised`（凸起，用于小说正文章节与独立面板）和 `inset`（内凹，用于指标背景与槽位）；
   - 内置平滑的过渡动画，提供悬浮立体微位移。
2. **`NeuButton`（纯图标与纯按钮）**：
   - 必须强制接收 `material-symbols` 标识作为 Iconify 来源；
   - 封装加载状态（Loading）与激活状态（Active Inset Shadow）。
3. **`NeuMeter`（新拟态生理指标槽）**：
   - 采用外凹槽内微凸渐变填充的形式，直观反映健康值（Health）与精力值（Stamina）。
4. **`TimelineLogItem`（故事切片组件）**：
   - 专注于展现文学正文，正文必须通过 `v-for` 配合换行符自动切分为独立的自然段落（`<p class="prose-paragraph">`），每个段落具有 2em 首行缩进与独立段距（`margin-bottom: 0.85rem`），保留 `white-space: pre-wrap`，杜绝无换行文字墙；
   - 默认折叠 Pass 1 裁决出的客观事实骨架（Plot Beat）与物品增减增量，点击可展开供查看或调试。
5. **`NeuToast`（全局新拟态通知与错误指引组件）**：
   - 遵循绝对无 Emoji 规范，所有状态指示均基于 `@iconify/vue`（`material-symbols` 图标）；
   - 采用右上方浮动式立体新拟态阴影卡片（`border-radius: 14px; box-shadow: 8px 8px 18px ...`）；
   - 根据推演引擎抛出的结构化 `error_code`（如 `AUTH_FAILED`, `RATE_LIMIT_OR_QUOTA`, `MODEL_NOT_FOUND`, `NETWORK_TIMEOUT`, `PASS1_FAILED`, `PASS2_FAILED` 等），向用户提供面向操作的清晰指引（如“检查 API 设置”、“点击重试”），隐藏底层晦涩堆栈，提升用户体验。

