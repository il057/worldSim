# AI 导航总目录与技术规范索引 (docs/for-ai.md)

本文档是 AI 开发者（AI Agent）在 `docs/` 目录下的专用索引字典。在执行任何具体的开发任务前，请通过下表定位对应的模块规范文档进行针对性查阅。

---

## 1. 规范文档索引与开发任务映射表

| 序号 | 规范文档路径 | 核心覆盖领域与关键决策点 | 适用开发场景与任务 |
| :---: | :--- | :--- | :--- |
| **01** | [01_INGESTION_PIPELINE.md](01_INGESTION_PIPELINE.md) | - 酒馆卡正则剥离（HTML/CSS/Scripts/宏标记）<br>- `{{user}}` 交互依赖解耦为内在执念<br>- 世界书全量保留与动态分类规则<br>- 多人卡 POV 主角单选与 NPC 关系降维<br>- 角色自适应作息画像（Circadian Profile）提取<br>- 4 维度极简表单 AI 标准化衍生 | 编写卡片解析服务、角色导入逻辑、Prompt 预处理、世界书入库过滤、简易表单创建端点时必读。 |
| **02** | [02_DUAL_CLOCK_ENGINE.md](02_DUAL_CLOCK_ENGINE.md) | - 双轨时钟引擎架构（现实时间同步 vs 沙盒自由推演）<br>- APScheduler 1 小时自动定时器调度<br>- 精力条（Stamina）+ 作息画像 + 环境安全度的三维睡眠裁决树<br>- 离线长跨度两阶段折叠补偿算法<br>- 纯按钮控制沙盒步进（+1h, +6h, +24h）<br>- AI 自主构思突发事件机制与并发互斥锁 | 编写后台定时调度器、时钟步进服务、睡眠裁决逻辑、长间隔补偿计算以及并发安全控制时必读。 |
| **03** | [03_TWO_PASS_TICK_PIPELINE.md](03_TWO_PASS_TICK_PIPELINE.md) | - 双步推演管线架构（Pass 1 裁决机 vs Pass 2 叙事机）<br>- Pass 1 严格结构化 State Delta JSON 输出规范<br>- Pass 2 第三人称有限视角纯文学规范<br>- 酒馆级 11 种文风框架（东方留白/冷峻白描/意识流/王家卫/奇幻等）<br>- 6 组文学技法补丁（白描特化/活人对话/通感/反总结抒情等）<br>- 篇幅与字数控制档位（300~1200+字精细控制）<br>- 60k Token 架构下的三层高保真长程记忆模型<br>- Deep Working Buffer 注入规则与倒排索引召回 | 编写推演核心管线、设计 LLM Prompt 提示词、制定 Pydantic 输出契约、实现长程记忆与文风字数调优时必读。 |
| **04** | [04_DATA_SCHEMA_AND_API.md](04_DATA_SCHEMA_AND_API.md) | - SQLite 6 张核心数据表 DDL（含系统配置持久化、自适应作息、完整世界书）<br>- 纯按钮控制的 RESTful API 契约（`/api/v1`）<br>- 动态拉取模型接口契约（`/characters/system/fetch-models`）<br>- 状态查询、长卷流水拉取、单步步进与阶段快进接口<br>- AI 自主突发事件触发接口（无用户文本输入） | 设计数据库实体模型（SQLAlchemy/SQLModel）、编写 Alembic 迁移脚本、开发 FastAPI 路由端点时必读。 |
| **05** | [05_UI_UX_NEUMORPHIC_SPEC.md](05_UI_UX_NEUMORPHIC_SPEC.md) | - Neumorphic 新拟态双向阴影公式与设计令牌（CSS 变量）<br>- 全局无 Emoji 铁律与 `@iconify/vue`（`material-symbols`）图标规范<br>- 沉浸式小说长卷阅读流与右侧状态看板双视图<br>- 纯按钮无文本框交互布局<br>- `NeuCard`, `NeuButton`, `NeuMeter`, `TimelineLogItem` 实现指南 | 编写 Vue 3 前端界面、实现新拟态立体阴影与过渡动画、配置 Pinia 状态树、绘制小说阅读器与侧边抽屉时必读。 |
| **06** | [06_DEPLOYMENT_AND_RUNBOOK.md](06_DEPLOYMENT_AND_RUNBOOK.md) | - FastAPI 单端口托管前端静态资源与 SPA 通配路由回退<br>- 多阶段构建 Dockerfile 规范<br>- 生产环境 `.env` 配置变量定义<br>- Vibe Coding 5 阶段落地执行清单（Phase 1 ~ Phase 5） | 配置前后端集成部署、编写 Dockerfile、配置开发环境与按照执行路线图拆解任务时必读。 |

---

## 2. AI 代理工作流指南 (How AI Works Here)

1. **查阅阶段**：在领取任何新任务或提示词时，先比对上表，阅读对应的 md 文件；
2. **编码阶段**：确保代码中严格遵守对应模块的数据契约、命名规范与无 Emoji 铁律；
3. **同步更新阶段**：**任何对业务逻辑、数据字段、API 协议、UI 架构的调整，必须在交付代码的同时，同步更新对应的 `docs/*.md` 规范文件**。
