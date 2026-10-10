# AI 导航总目录与技术规范索引 (docs/for-ai.md)

本文档是 AI 开发者（AI Agent）在 `docs/` 目录下的专用索引字典。在执行任何具体的开发任务前，请通过下表定位对应的模块规范文档进行针对性查阅。

---

## 1. 规范文档索引与开发任务映射表

| 序号 | 规范文档路径 | 核心覆盖领域与关键决策点 | 适用开发场景与任务 |
| :---: | :--- | :--- | :--- |
| **01** | [01_INGESTION_PIPELINE.md](01_INGESTION_PIPELINE.md) | - 酒馆卡正则剥离（HTML/CSS/Scripts/宏标记）<br>- `{{user}}` 生态位具象化 NPC 替代与关系网注入<br>- 世界书全量保留与常驻/触发词严格区隔铁律<br>- 多人卡多实体人设/生理/专属 NPC 关系网绝对独立<br>- 角色自适应作息画像（Circadian Profile）提取<br>- 4 维度极简表单 AI 标准化衍生 | 编写卡片解析服务、角色导入逻辑、Prompt 预处理、世界书入库过滤、简易表单创建端点时必读。 |
| **02** | [02_DUAL_CLOCK_ENGINE.md](02_DUAL_CLOCK_ENGINE.md) | - 双轨时钟引擎架构（现实时间同步 vs 沙盒自由推演）<br>- 现实时间同步演化自由启闭与步长控制（防 API 费用冗余）<br>- APScheduler 自动定时器调度与动态热启停<br>- 精力条（Stamina）+ 作息画像 + 环境安全度的三维睡眠裁决树<br>- 离线长跨度两阶段折叠补偿算法<br>- 智能续写（自主研判时间尺度与动态切速）<br>- 纯按钮控制沙盒步进（+1h, +6h, +24h）<br>- 题材自适应突发事件机制（AI 衍生 vs 自定义输入）与并发互斥锁 | 编写后台定时调度器、时钟步进服务、睡眠裁决逻辑、长间隔补偿计算以及并发安全控制时必读。 |
| **03** | [03_TWO_PASS_TICK_PIPELINE.md](03_TWO_PASS_TICK_PIPELINE.md) | - 双步推演管线架构（Pass 1 衡律之神 vs Pass 2 见证之神）<br>- SSE 实时推演流与最新楼层神性两步自适应交互规范<br>- 自由续写动态切速与节律准则（完整行动单位尺度）<br>- 在场多角色横向区分与群像共驱法则（独立立场与差异化语言肌理）<br>- 题材自适应突发事件引擎规范（变数之引杜绝激进杀手出戏）<br>- Pass 1 严格结构化 State Delta JSON 输出规范<br>- Pass 2 第三人称有限视角纯文学规范<br>- 酒馆级 12 种文风框架与 7 组文学技法补丁<br>- 手机与社交网络交互拟真规范（朋友圈/论坛/私信/语音/定位/转账）<br>- 篇幅与字数控制档位（300~1200+字精细控制）<br>- 60k Token 架构下的三层高保真长程记忆模型<br>- Deep Working Buffer 注入规则与倒排索引召回 | 编写推演核心管线、设计 LLM Prompt 提示词、制定 Pydantic 输出契约、实现长程记忆与文风字数调优时必读。 |
| **04** | [04_DATA_SCHEMA_AND_API.md](04_DATA_SCHEMA_AND_API.md) | - SQLite 6 张核心数据表 DDL（含系统配置持久化、自适应作息、完整世界书）<br>- 世界书全生命周期管理（CRUD 新增/编辑/删除/查询）<br>- 智能续写接口（`/sim/continue` 与 `/sim/continue-stream`）<br>- 纯按钮控制的 RESTful API 契约（`/api/v1`）<br>- 动态拉取模型接口契约（`/characters/system/fetch-models`）<br>- 状态查询、长卷流水拉取、单步步进与阶段快进接口<br>- 突发事件触发接口（支持 AI 自主衍生或用户自定义输入） | 设计数据库实体模型（SQLAlchemy/SQLModel）、编写 Alembic 迁移脚本、开发 FastAPI 路由端点时必读。 |
| **05** | [05_UI_UX_NEUMORPHIC_SPEC.md](05_UI_UX_NEUMORPHIC_SPEC.md) | - Neumorphic 新拟态双向阴影公式与设计令牌（CSS 变量与深浅双模式）<br>- 主题系统（浅色/深色/跟随系统模式 + 7 色预设与自定义十六进制强调色）<br>- 全局无 Emoji 铁律与 `@iconify/vue`（`material-symbols`）图标规范<br>- 全拟态可复用组件套件（`NeuConfirmModal` + `useConfirm`、`NeuSelect`、`NeuToast` 彻底替代浏览器原生 `confirm/alert` 及 `<select>`）<br>- `SystemConfigModal` 现实同步演化开关与步长控制、采样高级参数折叠手风琴卡片防过长<br>- 移除全屏顶部状态横幅，最新楼层自适应推演态（非流式“生成中” vs 流式“衡律之神->见证之神”依次回复）<br>- 智能续写按钮与突发事件模态弹窗（`IncidentTriggerModal`）<br>- 沉浸式小说长卷阅读流与右侧状态看板双视图<br>- 纯按钮无文本框交互布局<br>- `TimelineLogItem` 混排渲染拟真手机卡片（朋友圈、论坛 BBS、即时私信对话流） | 编写 Vue 3 前端界面、实现新拟态立体阴影与过渡动画、配置 Pinia 状态树、绘制小说阅读器与侧边抽屉时必读。 |
| **06** | [06_DEPLOYMENT_AND_RUNBOOK.md](06_DEPLOYMENT_AND_RUNBOOK.md) | - FastAPI 单端口托管前端静态资源与 SPA 通配路由回退<br>- 多阶段构建 Dockerfile 规范<br>- 生产环境 `.env` 配置变量定义<br>- Vibe Coding 5 阶段落地执行清单（Phase 1 ~ Phase 5） | 配置前后端集成部署、编写 Dockerfile、配置开发环境与按照执行路线图拆解任务时必读。 |
| **附录** | [DEV_NOTES.md](DEV_NOTES.md) | - 项目演进随笔与进行中开发手记<br>- 界面布局从顶栏平铺到双抽屉+常驻看板的重构记录<br>- 时钟绝对锚定与去噪优化、社交拓扑与新拟态手机组件接入<br>- Pass 1 + Pass 2 两步解耦动因、文风技法补丁与字数弹性指引<br>- 在场 NPC 群像共驱、动态认知新 NPC 沉淀机制<br>- 自由续写与真实时间尺度约束、突发事件自适应去极端化（杜绝校园杀手）<br>- 配套截图资源归档于 `docs/dev_img/` | 回顾系统设计决策起源、界面迭代动机、UI 与底层 Prompt 演化手记时参考。 |

---

## 2. AI 代理工作流指南 (How AI Works Here)

1. **查阅阶段**：在领取任何新任务或提示词时，先比对上表，阅读对应的 md 文件；
2. **编码阶段**：确保代码中严格遵守对应模块的数据契约、命名规范与无 Emoji 铁律；
3. **同步更新阶段**：**任何对业务逻辑、数据字段、API 协议、UI 架构的调整，必须在交付代码的同时，同步更新对应的 `docs/*.md` 规范文件**。
