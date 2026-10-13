# Living Character World Simulation Engine

> AI 角色自主世界模拟与小说演化系统 (Autonomous Living Character Simulation & Novel Narrative Engine)

---

## 项目简介

**Living Character World Simulation Engine** 是一个由大语言模型（LLM）驱动的纯自主虚拟世界小说演化系统。

系统支持直接导入 SillyTavern（酒馆）角色卡（JSON / PNG）或通过 4 维度极简表单创建角色。在**完全去除人类玩家即时对话与文本输入**的前提下，系统由内部双轨时钟与理性裁决机自主推进角色的日常生活、冒险、人际羁绊与突发危机，持续撰写具备高文学质感的第三人称场景切片长卷。

系统前端采用极简、立体的 **Neumorphic（新拟态）** 视觉体系与**零浮层（Zero Overlay）原位工作台**设计，全站遵循严格的**无 Emoji 规范**。用户作为“全知旁观者”，通过纯按钮调控时间尺度与观察角色演化，体验真正自运转的沙盒世界。

---

## 核心设计特性

### 1. 两步解耦推演管线 (Two-Pass Tick Pipeline)
彻底杜绝传统 AI 模拟器中“单次 Prompt 混合生成导致的数值失真与文风崩塌”：
- **Pass 1: Arbitrator (衡律之神 · 理性裁决机)**：专职物理法则、因果推演与生理状态判定。输入最新看板、角色作息画像、精力值、背包状态、空间常驻地及世界书法则，输出纯净严格的结构化 State Delta JSON（生理损益、物品进出、目标转移、NPC 好感度与新角色沉淀）以及客观事实骨架（Plot Beat）。
- **Pass 2: Storyteller (见证之神 · 文学叙事机)**：以严格的**第三人称有限视角（Third-Person Limited）**，依托 Pass 1 的事实骨架与感官线索，撰写高质感文学切片小说。正文绝不夹带任何系统状态栏或属性代码块，并支持 SSE 实时推演流分阶段交互呈现。

### 2. 拟真生理精力与自适应作息系统
抛弃机械死板的作息时刻表与单向跳崖式精力扣减：
- **真实生理精力收支法则**：日常听课、阅读、散步等轻度活动每小时仅平缓消耗 2~5 点精力；引入清醒状态下的自然回血机制（用餐回血 +5~15，静坐发呆 +3~8，午间小憩 +10~20）；角色健康入睡时保留 35~50 点精力，整天收支平衡。
- **作息画像与晨起对齐**：结合角色**自适应作息画像（Circadian Profile）**与**环境可休眠度（Environment Affordance）**判定休眠；睡眠推进时根据世界观与角色作息自适应对齐至合理晨间时刻（06:30~07:30），消灭凌晨五点半强行早起的荒谬情节。

### 3. 社会生态底噪与真实世界法则
经过数十轮长程推演实战打磨，系统内置了针对长程生成退化的六大调优机制：
- **随身行囊物理负重（6~8 件上限）**：强制锁定随身有效槽位上限，引入据点收纳与断舍离规约，严禁无意义生活垃圾与一次性杂物侵占背包，根除 AI“囤积癖”。
- **NPC 物理常驻地与时空隔离**：为所有次要角色显式绑定常驻物理据点（Residence），严格校验地理距离，严禁跨区域幽灵瞬移闪现；同时注入“大世界多元人群”认知，打破只有开局两三人的封闭社交茧房。
- **普适年龄行为认知锚点**：分阶段引导 AI 把握幼少期、青年前期与成熟期心智特征，贯彻“Show, Don't Tell”白描神态动作，严禁报年龄生硬旁白。
- **社会生态位日常底噪融合**：学生必须上课听讲、学徒必须工坊劳作、职员必须打卡；核心剧情有机嵌套在日常生活底噪中插缝推进，拒绝脱产特工化。
- **反主角光环与代价守恒**：强制引入非致命挫败，NPC 具备独立意志与合理警惕心；文学技法补丁全面查杀动物化套路比喻与段尾强行鸡汤升华。

### 4. 12 种名家标杆文风与文学技法补丁
- **名家笔法标杆注入**：系统预设涵盖轻快欢脱（对标碟形世界）、市井烟火（对标茶馆、繁花）、冷调光影（对标雷蒙德·卡佛）、东方素描（对标汪曾祺）、戏谑发疯（对标地下室手记）、诡谲志怪（对标聊斋志异、罗生门）等 12 种风格，并支持自定义自由匹配。
- **文学技法补丁库**：内置 7 组文学技法补丁（抗空心发呆、抗机械报菜名、生活化机锋对白、客观白描、拒绝段尾总结等），并提供 300~1200+ 字篇幅档位精细引导。

### 5. 拟真沙盒生态与自转节律
- **智能续写 / 自由续写**：允许用户在不强行跳转时间的前提下继续展开当前焦点事件，由 AI 自主研判推进 0.5h ~ 1.5h 的完整行动闭环，铺垫时放慢展开细节，交锋时紧扣危机。
- **拟真手机与社交网络**：在长卷混排中原生渲染拟真手机卡片，包含朋友圈动态（Moments）、匿名论坛发帖（Forum BBS）、即时私信群聊（Chat）以及定位与转账流水。
- **题材自适应突发事件**：用户点击纯按钮触发后，由 AI 紧密契合当前题材（日常校园、工坊学徒、科幻都市、奇幻探险等）与微观处境自主构思变数，杜绝激进杀手出戏情节。

### 6. 60k Token 预算下的三层高保真记忆模型
- **Tier 1: Living State Sheet**：常驻最新生存状态看板与目标栈（~500 Tokens）；
- **Tier 2: Deep Working Buffer**：保留最近 10~20 轮连续小说正文，保障文学语调、句式美感与微观环境伏笔高度连贯（~15,000 Tokens）；
- **Tier 3: Timeline Ledger & Full Lorebook**：容纳完整万字世界书与基于 SQLite 的实体关键词倒排索引召回（~30,000 Tokens）。

### 7. 零浮层原位工作台与新拟态美学
- **零浮层原位架构 (Zero Overlay)**：彻底废除 Modal 弹窗暗色遮罩对沉浸感的阻断，世界书条目管理（WorldLoreView）与文风提示词工坊（PromptEditorView）在主视口原位展开；系统设置面板（SystemConfigPanel）在右侧看板原地无缝平滑切替。
- **深浅双模与强调色系统**：浅色/深色/跟随系统模式，提供 7 款预设强调色与自定义十六进制拾色器，修改主题即时感知。
- **全拟态纯图标套件**：纯原生 Vanilla CSS 双向阴影设计令牌（`--shadow-flat`、`--shadow-inset`），全站统一使用 `@iconify/vue` 搭配 `material-symbols` 纯矢量图标，彻底摒弃 Emoji 与浏览器原生生硬弹窗。

### 8. 长程推演评测与基准套件 (Evaluation & Benchmark)
- **自动化推演驱动器 (`auto_driver.py`)**：模拟现实生活节律状态机，支持 50~100 刻无人值守压测与断点元数据无损继承。
- **LLM-as-a-Judge 自动化裁判 (`evaluator.py`)**：四维量化评估矩阵（连续一致性、叙事观赏性、社交生态活性、角色成长弧光）。
- **单文件独立 HTML 评测报告 (`report_generator.py`)**：零依赖可离线双击打开的深色新拟态报告，具备等比疏密映射竖向时间轴、精力心电连续波形图、宏观据点足迹与里程碑流。

### 9. 单容器与轻量无依赖架构
- 前端：Vue 3 + Vite + TypeScript + Pinia + 原生 Vanilla CSS + Iconify；
- 后端：Python 3.11 + FastAPI + SQLite 3 + SQLAlchemy；
- 交付：前端编译产物由 FastAPI 直接静态托管，单容器（Docker）单端口（8080）一体化部署；LLM 连接参数通过 Web UI 在线配置并持久化于 SQLite。

---

## 模块规范技术文档

本项目技术设计已按工程模块深度拆分，所有规范文档均采用标准 GitHub 相对路径链接：

| 模块文档 | 核心技术范围与规范指引 |
| :--- | :--- |
| [01_INGESTION_PIPELINE.md](docs/01_INGESTION_PIPELINE.md) | 酒馆卡正则剥离、`{{user}}` 动机转写、世界书完整导入、多人卡 POV 降维与自适应作息画像提取 |
| [02_DUAL_CLOCK_ENGINE.md](docs/02_DUAL_CLOCK_ENGINE.md) | 双轨时钟引擎（现实同步 vs 沙盒自由推演）、精力与作息画像驱动的自适应睡眠树、长跨度补偿算法、纯按钮沙盒引擎 |
| [03_TWO_PASS_TICK_PIPELINE.md](docs/03_TWO_PASS_TICK_PIPELINE.md) | 双步推演管线架构、60k Token 三层长程记忆、六大长程痛点优化、12 种名家标杆文风与 7 组文学技法补丁、拟真手机交互 |
| [04_DATA_SCHEMA_AND_API.md](docs/04_DATA_SCHEMA_AND_API.md) | SQLite 6 张核心数据表 DDL、Pydantic 实体契约、运行期配置持久化与纯按钮 RESTful API 契约 |
| [05_UI_UX_NEUMORPHIC_SPEC.md](docs/05_UI_UX_NEUMORPHIC_SPEC.md) | Neumorphic 新拟态双向阴影公式、无 Emoji 铁律、原位工作台架构、全拟态组件库与长卷小说阅读流 |
| [06_DEPLOYMENT_AND_RUNBOOK.md](docs/06_DEPLOYMENT_AND_RUNBOOK.md) | FastAPI 单端口托管前端静态资源与 SPA 路由兜底、多阶段 Dockerfile 规范与 Vibe Coding 实施清单 |
| [07_EVALUATION_AND_BENCHMARK.md](docs/07_EVALUATION_AND_BENCHMARK.md) | 100 刻长程推演质量验证、自动化驱动器（`auto_driver.py`）、LLM 裁判诊断（`evaluator.py`）与单文件 HTML 可视化报告（`report_generator.py`） |
| [DEV_NOTES.md](docs/DEV_NOTES.md) | 独立开发者演进手记、前后端零浮层重构、长程推演实战踩坑手记与生成对比佐证、Pass 3 质检设想与现实成本反思 |

> **提示**：面向 AI 编程助手的专属索引与开发规范入口，请参阅 [AGENTS.md](AGENTS.md) 及 [docs/for-ai.md](docs/for-ai.md)。

---

## 项目结构全景

```
worldSim/
|-- AGENTS.md                         # AI 开发者准则与文档维护铁律
|-- README.md                         # 项目主页与全景介绍 (本文档)
|-- Dockerfile                        # 多阶段单容器构建清单
|-- docker-compose.yml                # Docker Compose 服务编排
|-- .env.example                      # 环境变量示例文件
|-- docs/                             # 模块级技术规范集 (GitHub 相对路径)
|   |-- for-ai.md                     # AI 专属任务与规范映射目录
|   |-- 01_INGESTION_PIPELINE.md      # 角色卡清洗与摄入
|   |-- 02_DUAL_CLOCK_ENGINE.md       # 双轨时钟与睡眠机制
|   |-- 03_TWO_PASS_TICK_PIPELINE.md  # 双步推演与长程记忆
|   |-- 04_DATA_SCHEMA_AND_API.md     # 数据库设计与 API 契约
|   |-- 05_UI_UX_NEUMORPHIC_SPEC.md   # 新拟态设计与组件
|   |-- 06_DEPLOYMENT_AND_RUNBOOK.md  # 单容器部署与落地清单
|   |-- 07_EVALUATION_AND_BENCHMARK.md# 长程推演质量评估与基准报告
|   |-- DEV_NOTES.md                  # 独立开发者演进手记与实测复盘
|   `-- dev_img/                      # 开发演进与对比佐证图片库
|-- backend/                          # FastAPI 后端服务
|   |-- app/
|   |   |-- config.py                 # 服务端环境配置
|   |   |-- database.py               # SQLite 连接与 Session 管理
|   |   |-- main.py                   # FastAPI 应用入口与静态托管
|   |   |-- models.py                 # SQLAlchemy 数据库模型 (6 张核心表)
|   |   |-- schemas.py                # Pydantic 请求与响应契约模型
|   |   |-- routers/                  # API 路由层 (cards, characters, simulation)
|   |   `-- services/                 # 业务逻辑层 (双步管线, 记忆, 调度, 提示词工坊)
|   |-- scripts/                      # 长程推演与评测脚本套件
|   |   |-- auto_driver.py            # 拟真节律自动化推演驱动器
|   |   |-- evaluator.py              # LLM-as-a-Judge 自动化评测诊断
|   |   `-- report_generator.py       # 单文件独立 HTML 评测可视化报告器
|   |-- logs/                         # 角色长程推演全量日志目录
|   |-- reports/                      # 离线 HTML 评测报告生成输出目录
|   `-- requirements.txt              # 后端 Python 依赖清单
|-- frontend/                         # Vue 3 新拟态单页应用
|   |-- src/
|   |   |-- api/                      # Axios API 客户端封装
|   |   |-- components/               # 原位工作台视图、拟态组件库与手机组件
|   |   |-- composables/              # Vue 组合式函数 (如 useConfirm)
|   |   |-- stores/                   # Pinia 状态树 (角色, 推演, 配置, 主题)
|   |   |-- style.css                 # 全局 Neumorphic 纯原生 CSS 设计令牌
|   |   |-- App.vue                   # 主工作台视口布局与三栏联动
|   |   `-- main.ts                   # 前端应用入口
|   `-- package.json                  # 前端依赖与构建脚本
`-- world_sim.db                      # SQLite 本地数据文件
```

---

## 快速上手与运行

### 1. 本地开发环境准备

#### 后端启动 (FastAPI)
```bash
cd backend
python -m venv venv

# Windows:
venv\Scripts\activate
# Linux/macOS:
# source venv/bin/activate

pip install -r requirements.txt

# 启动后端服务 (统一监听 8080 端口)
uvicorn app.main:app --reload --port 8080
```

#### 前端启动 (Vue 3)
```bash
cd frontend
npm install
npm run dev
```

启动后：
- 前端开发服务器默认运行在 `http://localhost:5173`（自动代理 API 请求至后端的 8080 端口）；
- 后端 API 文档可通过 `http://localhost:8080/docs` 访问；
- 首次进入系统后，点击右上角设置图标打开**系统设置面板**，填入你的 LLM API Key、Base URL 并选择模型即可开始推演。

---

### 2. 单容器 Docker 部署

系统支持通过 Docker 多阶段构建实现单容器单端口交付：

```bash
# 1. 构建镜像
docker build -t world-sim:latest .

# 2. 运行容器 (映射 8080 端口并持久化数据卷)
docker run -d -p 8080:8080 -v $(pwd)/data:/data world-sim:latest
```

或使用 Docker Compose：
```bash
docker compose up -d
```

服务启动后，在浏览器访问 `http://localhost:8080` 即可获得完整的前后端一体化推演体验。

---

### 3. 长程推演与评测套件使用

若需进行 50~100 刻的长篇无人值守压测或生成离线 HTML 评测报告：

```bash
cd backend

# 运行自动化节律驱动器进行连续推演 (例如推进 30 刻)
python scripts/auto_driver.py --name "格温·艾尔斯" --ticks 30

# 执行大模型裁判评估诊断
python scripts/evaluator.py --name "格温·艾尔斯"

# 生成单文件深色新拟态可视化 HTML 报告
python scripts/report_generator.py --name "格温·艾尔斯"
```

生成的报告将保存在 `backend/reports/` 目录下，双击即可在任意现代浏览器中离线查验。