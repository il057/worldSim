# AI 导航总目录与技术规范索引 (docs/for-ai.md)

本文档是 AI 开发者（AI Agent）在 `docs/` 目录下的专用索引字典。在执行任何具体的开发任务前，请通过下表定位对应的模块规范文档进行针对性查阅。

---

## 1. 规范文档索引与开发任务映射表

| 序号 | 规范文档路径 | 核心覆盖领域与关键决策点 | 适用开发场景与任务 |
| :---: | :--- | :--- | :--- |
| **01** | [01_INGESTION_PIPELINE.md](01_INGESTION_PIPELINE.md) | - 酒馆卡正则剥离（HTML/CSS/Scripts/宏标记）<br>- `{{user}}` 生态位具象化 NPC 替代与关系网注入<br>- 世界书全量保留与常驻/触发词严格区隔铁律<br>- 多人卡多实体人设/生理/专属 NPC 关系网绝对独立<br>- 角色自适应作息画像（Circadian Profile）提取<br>- 4 维度极简表单 AI 标准化衍生 | 编写卡片解析服务、角色导入逻辑、Prompt 预处理、世界书入库过滤、简易表单创建端点时必读。 |
| **02** | [02_DUAL_CLOCK_ENGINE.md](02_DUAL_CLOCK_ENGINE.md) | - 双轨时钟引擎架构（现实时间同步 vs 沙盒自由推演）<br>- 现实时间同步演化自由启闭与步长控制（防 API 费用冗余）<br>- APScheduler 自动定时器调度与动态热启停<br>- 精力条（Stamina）+ 作息画像 + 环境安全度的三维睡眠裁决树<br>- 离线长跨度两阶段折叠补偿算法<br>- 智能续写（自主研判时间尺度与动态切速）<br>- 纯按钮控制沙盒步进（+1h, +6h, +24h）<br>- 题材自适应突发事件机制（AI 衍生 vs 自定义输入）与并发互斥锁 | 编写后台定时调度器、时钟步进服务、睡眠裁决逻辑、长间隔补偿计算以及并发安全控制时必读。 |
| **03** | [03_TWO_PASS_TICK_PIPELINE.md](03_TWO_PASS_TICK_PIPELINE.md) | - 双步推演管线架构（Pass 1 衡律之神 vs Pass 2 见证之神）<br>- 普适年龄行为认知锚点与未解析周岁兜底规范（Age Behavioral Dynamics）<br>- 社会生态位与日常底噪锚定法则（Ecosystem & Identity Anchoring）<br>- 真实生理精力收支法则与清醒自然回血机制（轻度 2~5/h，正餐/小憩回血，整天收支平衡入夜保有一半精力）<br>- 新结识 NPC 初始好感理性克制（-10~25）与日常互动 ±1~±3 幅度规范（Initial Affinity Clamping & Daily Delta Regulation）<br>- NPC 好感度继承与保护兜底铁律（Affinity Preservation & Fallback Invariant）<br>- 现代/日常题材社会生态破冰与反流水账铁律（Everyday Ecosystem Unfreezing & Anti-Routine）<br>- 全局提示词与文风配置持久化与跨端/CLI 统一继承规范（Global Config Invariant）<br>- SSE 实时推演流与最新楼层神性两步自适应交互规范<br>- 自由续写动态切速与节律准则（完整行动单位尺度）<br>- 在场多角色横向区分与群像共驱法则（独立立场与差异化语言肌理）<br>- 随身行囊物理负重（6~8 件上限）与据点收纳/断舍离规约<br>- NPC 空间常驻地自主裁决与时空隔离铁律（禁止异地凭空在场）<br>- 弱羁绊基于虚拟时空跨度的自然淡出衰退机制（`pruned_npcs` / `is_archived`）<br>- 题材自适应突发事件引擎规范（变数之引杜绝激进杀手出戏）<br>- Pass 1 严格结构化 State Delta JSON 输出规范<br>- Pass 2 第三人称有限视角纯文学规范<br>- 酒馆级 12 种文风框架与 7 组文学技法补丁<br>- 手机与社交网络交互拟真规范（朋友圈/论坛/私信/语音/定位/转账）<br>- 篇幅与字数控制档位（300~1200+字精细控制）<br>- 60k Token 架构下的三层高保真长程记忆模型<br>- Deep Working Buffer 注入规则与倒排索引召回 | 编写推演核心管线、设计 LLM Prompt 提示词、制定 Pydantic 输出契约、实现长程记忆与文风字数调优时必读。 |
| **04** | [04_DATA_SCHEMA_AND_API.md](04_DATA_SCHEMA_AND_API.md) | - SQLite 6 张核心数据表 DDL（含角色社交常驻地、虚拟时间戳与归档字段、系统配置持久化、自适应作息、完整世界书）<br>- 世界书全生命周期管理（CRUD 新增/编辑/删除/查询）<br>- 智能续写接口（`/sim/continue` 与 `/sim/continue-stream`）<br>- 纯按钮控制的 RESTful API 契约（`/api/v1`）<br>- 动态拉取模型接口契约（`/characters/system/fetch-models`）<br>- 状态查询、长卷流水拉取、单步步进与阶段快进接口<br>- 突发事件触发接口（支持 AI 自主衍生或用户自定义输入） | 设计数据库实体模型（SQLAlchemy/SQLModel）、编写 Alembic 迁移脚本、开发 FastAPI 路由端点时必读。 |
| **05** | [05_UI_UX_NEUMORPHIC_SPEC.md](05_UI_UX_NEUMORPHIC_SPEC.md) | - Neumorphic 新拟态双向阴影公式与设计令牌（CSS 变量与深浅双模式）<br>- 主题系统（浅色/深色/跟随系统模式 + 7 色预设与自定义十六进制强调色）<br>- 全局无 Emoji 铁律与 `@iconify/vue`（`material-symbols`）图标规范<br>- 全拟态可复用组件套件（`NeuConfirmModal` + `useConfirm`、`NeuSelect`、`NeuToast`，不使用浏览器原生 `confirm/alert` 及 `<select>`）<br>- 顶栏严格对称网格中轴居中与纯图标化按键规范（`TopNavBar`）<br>- `SystemConfigPanel` 右侧贴顶整块标头架构（无上方圆角，保存纯 SVG 按钮）与零 Overlay 切换<br>- `WorldLoreView`（纯平居中 SVG 箭头，DOM 真实截断检测超 2 行展开，等高响应式搜索栏）与 `PromptEditorView`（首行标题动作平齐，第二行分栏占满全宽）在中间视口原位呈现<br>- 全局统一深浅自适应透明滚动条<br>- 最新楼层自适应推演态（非流式“生成中” vs 流式“衡律之神->见证之神”依次回复，屏幕顶部无悬浮横幅）<br>- 智能续写按钮与突发事件模态弹窗（`IncidentTriggerModal`）<br>- 沉浸式小说长卷阅读流与右侧状态看板双视图<br>- 纯按钮无文本框交互布局<br>- `TimelineLogItem` 混排渲染拟真手机卡片（朋友圈、论坛 BBS、即时私信对话流） | 编写 Vue 3 前端界面、实现新拟态立体阴影与过渡动画、配置 Pinia 状态树、绘制小说阅读器与侧边抽屉时必读。 |
| **06** | [06_DEPLOYMENT_AND_RUNBOOK.md](06_DEPLOYMENT_AND_RUNBOOK.md) | - FastAPI 单端口托管前端静态资源与 SPA 通配路由回退<br>- 多阶段构建 Dockerfile 规范<br>- 生产环境 `.env` 配置变量定义<br>- Vibe Coding 5 阶段落地执行清单（Phase 1 ~ Phase 5） | 配置前后端集成部署、编写 Dockerfile、配置开发环境与按照执行路线图拆解任务时必读。 |
| **07** | [07_EVALUATION_AND_BENCHMARK.md](07_EVALUATION_AND_BENCHMARK.md) | - 100+ 刻长程推演质量验证（四维评估矩阵）<br>- 拟真生活节律与戏剧状态机自动化驱动器（`auto_driver.py`：昼夜白昼防睡死、弹性微步进 30~90m、夜间睡眠动态对齐清晨 07:00）<br>- LLM-as-a-Judge 自动化裁判量化诊断与微观地点智能归类（`evaluator.py`）<br>- 24小时昼夜作息疏密节律与宏观据点足迹折叠的单文件独立 HTML 评测报告器（`report_generator.py`） | 自动化长程推演压测、执行大模型裁判诊断、生成可视化报告时必读。 |
| **附录** | [DEV_NOTES.md](DEV_NOTES.md) | - 独立开发者手记（面向人类视角的真诚复盘）<br>- 双抽屉+常驻看板三栏界面布局记录与零浮层原位工作台重构<br>- 时钟绝对锚定与去噪优化、社交拓扑与新拟态手机组件接入<br>- Pass 1 + Pass 2 两步解耦动因、文风名家标杆注入与二次重构（轻快欢脱与市井烟火）<br>- 为什么后期二三十轮才显现提示词深水区问题<br>- 长程推演实战踩坑手记与提示词六大痛点调优（背包 8 件防囤积爆炸、NPC 住所防瞬移闪现与“大世界形形色色的人”认知注入、年龄行为动作白描与社会生态底噪融合律、反主角光环/八股文与实测生成对比佐证、Gemini 模型针对性说明、脚本时间弹性 30~90m 与清晨晨起对齐、真实生理精力与清醒回血前后波形对比、文风覆盖面扩展）<br>- 自动化驱动器（`auto_driver.py`）与单文件独立 HTML 评测报告（`report_generator.py`）<br>- 长程全 AI 生成文本退化规律反思、Pass 3 质检与大纲设想、独立开发者面对昂贵 API 调用成本的现实妥协与考量<br>- 配套截图资源归档于 `docs/dev_img/` | 回顾系统设计决策起源、界面迭代动机、UI 与底层 Prompt 演化手记时参考。 |

---

## 2. AI 代理工作流指南 (How AI Works Here)

1. **查阅阶段**：在领取任何新任务或提示词时，先比对上表，阅读对应的 md 文件；
2. **编码阶段**：确保代码中严格遵守对应模块的数据契约、命名规范与无 Emoji 铁律；
3. **同步更新阶段**：**任何对业务逻辑、数据字段、API 协议、UI 架构的调整，必须在交付代码的同时，同步更新对应的 `docs/*.md` 规范文件**。
