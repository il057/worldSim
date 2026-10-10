# Living Character World Simulation Engine

> AI 角色自主世界模拟与小说演化系统 (Autonomous Living Character Simulation & Novel Narrative Engine)

---

## 项目简介

**Living Character World Simulation Engine** 是一个由大语言模型（LLM）驱动的纯自主虚拟世界小说演化系统。

系统支持直接导入 SillyTavern（酒馆）角色卡（JSON / PNG）或通过极简表单创建角色。在**完全去除人类玩家即时对话与文本输入**的前提下，系统由内部双轨时钟自主推进角色的日常生活、冒险与危机，持续撰写具备高文学质感的第三人称场景切片长卷。

系统前端采用极简、立体的 **Neumorphic（新拟态）** 视觉设计，界面无任何文本输入框与对话气泡，用户作为“全知旁观者”，通过纯按钮调控时间流速与观察角色演化。

---

## 核心设计特性

### 1. 两步解耦推演管线 (Two-Pass Tick Pipeline)
彻底杜绝传统 AI 模拟器中“单次 Prompt 混合生成导致的数值失真与文风崩塌”：
- **Pass 1: Arbitrator (理性裁决机)**：专职进行世界物理与因果判定。输入当前状态看板、角色作息、精力值与世界书法则，输出纯净的结构化 State Delta（生理属性损益、物品进出、目标转移）以及客观事实骨架（Plot Beat）。
- **Pass 2: Storyteller (文学叙事机)**：以严格的**第三人称有限视角（Third-Person Limited）**，围绕 Pass 1 的事实骨架与感官线索，撰写 300~600 字高质感场景切片小说。正文绝不夹带任何系统状态栏或属性代码块。

### 2. 60k Token 架构下的三层高保真记忆模型
依托现代长上下文能力，系统将推演窗口扩展至 60,000 Tokens，彻底解除对世界书的暴力截断：
- **Tier 1: Living State Sheet**：常驻最新生存状态看板与目标栈（~500 Tokens）；
- **Tier 2: Deep Working Buffer**：保留最近 10~20 轮连续正文，确保文学语调、句式美感与微观环境伏笔高度连贯（~15,000 Tokens）；
- **Tier 3: Timeline Ledger & Full Lorebook**：容纳完整万字世界书与基于 SQLite 的历史因果网络多路召回（~30,000 Tokens）。

### 3. 精力与作息画像驱动的自适应睡眠系统
抛弃机械死板的作息时刻表，系统结合角色的**自适应作息画像（Circadian Profile）**、**即时生理精力条（Stamina）**与**环境可休眠度（Environment Affordance）**动态判定休眠。当精力匮乏且环境适宜（旅舍、自家庭院、载具客舱）时，角色自主就寝恢复精力；在危急险境中则强撑困意，产生心理焦虑。

### 4. 纯按钮交互与自主突发事件
界面彻底摒弃任何对话框或输入框。用户仅通过新拟态纯按钮进行操控：
- `+1h` 单步推进、`+6h` 阶段快进、`+24h` 跨日跃迁；
- **触发突发事件 (Trigger Inciting Incident)**：无需用户输入任何描述，点击后由 AI 结合当前环境与未解执念自主构思一场契合因果逻辑的危机或奇遇。

### 5. 单容器与轻量无依赖架构
- 前端：Vue 3 + Vite + Pinia + Tailwind CSS + Iconify (`material-symbols`)；
- 后端：Python 3.11 + FastAPI + SQLite 3；
- 交付：前端编译产物由 FastAPI 直接静态托管，单容器（Docker）单端口（8080）一体化部署。

---

## 模块规范技术文档

本项目技术设计已按工程模块深度拆分，所有规范文档均采用标准 GitHub 相对路径链接：

| 模块文档 | 核心技术范围与规范指引 |
| :--- | :--- |
| [01_INGESTION_PIPELINE.md](docs/01_INGESTION_PIPELINE.md) | 酒馆卡正则剥离、`{{user}}` 动机转写、世界书完整导入、多人卡 POV 降维与作息画像提取 |
| [02_DUAL_CLOCK_ENGINE.md](docs/02_DUAL_CLOCK_ENGINE.md) | APScheduler 定时调度、精力与作息画像驱动的睡眠决策树、纯按钮沙盒引擎 |
| [03_TWO_PASS_TICK_PIPELINE.md](docs/03_TWO_PASS_TICK_PIPELINE.md) | 双步推演管线架构（Arbitrator 与 Storyteller）、60k Token 预算分配与三层长程记忆 |
| [04_DATA_SCHEMA_AND_API.md](docs/04_DATA_SCHEMA_AND_API.md) | SQLite 核心数据库 DDL、Pydantic 实体模型与纯按钮 RESTful API 契约 |
| [05_UI_UX_NEUMORPHIC_SPEC.md](docs/05_UI_UX_NEUMORPHIC_SPEC.md) | Neumorphic 新拟态双向阴影公式、无 Emoji 铁律、Iconify 纯图标映射与小说长卷布局 |
| [06_DEPLOYMENT_AND_RUNBOOK.md](docs/06_DEPLOYMENT_AND_RUNBOOK.md) | FastAPI 静态托管架构、多阶段 Dockerfile 规范与 Vibe Coding 分阶段实施清单 |

> **提示**：面向 AI 编程助手的专属索引与开发规范入口，请参阅 [AGENTS.md](AGENTS.md) 及 [docs/for-ai.md](docs/for-ai.md)。

---

## 项目结构全景

```
worldSim/
|-- AGENTS.md                         # AI 开发者准则与文档维护铁律
|-- README.md                         # 项目主页与全景介绍 (本文档)
|-- docs/                             # 模块级技术规范集 (GitHub 相对路径)
|   |-- for-ai.md                     # AI 专属任务与规范映射目录
|   |-- 01_INGESTION_PIPELINE.md      # 角色卡清洗与摄入
|   |-- 02_DUAL_CLOCK_ENGINE.md       # 双轨时钟与睡眠机制
|   |-- 03_TWO_PASS_TICK_PIPELINE.md  # 双步推演与长程记忆
|   |-- 04_DATA_SCHEMA_AND_API.md     # 数据库设计与 API 契约
|   |-- 05_UI_UX_NEUMORPHIC_SPEC.md   # 新拟态设计与组件
|   `-- 06_DEPLOYMENT_AND_RUNBOOK.md  # 单容器部署与落地清单
|-- backend/                          # FastAPI 后端服务
|   |-- app/                          # 核心业务逻辑、路由、调度器、持久化
|   `-- requirements.txt
|-- frontend/                         # Vue 3 新拟态单页应用
|   |-- src/                          # 视图、组件、Pinia 状态存储
|   `-- package.json
|-- Dockerfile                        # 多阶段单容器构建清单
`-- docker-compose.yml
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
uvicorn main:app --reload --port 8000
```

#### 前端启动 (Vue 3)
```bash
cd frontend
npm install
npm run dev
```

### 2. 单容器 Docker 部署

```bash
docker build -t world-sim:latest .
docker run -d -p 8080:8080 -v $(pwd)/data:/data world-sim:latest
```
服务启动后，在浏览器访问 `http://localhost:8080` 即可开始虚拟角色世界演化。