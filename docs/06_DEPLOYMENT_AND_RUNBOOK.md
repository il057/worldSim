# 模块 06：部署架构、静态托管与实施路线图 (Deployment & Runbook)

---

## 1. 单容器一体化部署架构

系统采用现代化轻量交付模型：前端 Vue 3 工程打包生成的 `dist` 静态资源直接由后端 FastAPI 应用挂载，通过单进程、单端口（默认 8080）统一向外提供服务。所有数据存储于单文件 SQLite（`world_sim.db`），零外部依赖，极度适合个人部署与 Docker 快速交付。

```
+-------------------------------------------------------------------------+
|                    Docker 容器 (统一监听 8080 端口)                       |
|                                                                         |
|                     Uvicorn (FastAPI Application)                       |
|                                  |                                      |
|          +-----------------------+-----------------------+              |
|          |                                               |              |
|          v                                               v              |
|   /api/v1/* (REST API)                    /* (静态资源托管 StaticFiles)    |
|   - 业务控制器                             - index.html                   |
|   - LLM 调用适配器                         - assets/ (*.js, *.css)        |
|   - SQLite 读写引擎                        - SPA 客户端路由回退兜底        |
|                                                          |              |
|   +--------------------------------                      |              |
|   | SQLite 文件: /data/world_sim.db                      |              |
|   +------------------------------------------------------+              |
+-------------------------------------------------------------------------+
```

---

## 2. FastAPI 静态托管与 SPA 路由架构设计

在单页应用（SPA）中，当用户刷新前端深层路由时，后端必须正确重定向回 `index.html`，而不是返回 404。
核心实现模式指南：
1. **静态挂载**：使用 `FastAPI.mount("/assets", StaticFiles(directory=".../assets"), name="assets")` 托管构建生成的打包资源；
2. **通配路由回退**：定义通配 GET 路由（例如 `/{full_path:path}`），排除 `/api/` 开头的请求，其余均以 `FileResponse("index.html")` 响应，交由 Vue Router 客户端接管。

---

## 3. 多阶段构建 Dockerfile 规范

采用 Docker 多阶段构建（Multi-Stage Build）：
- **构建阶段（Node.js 20）**：拉取前端依赖并执行 `npm run build` 生成 `dist` 产物；
- **运行阶段（Python 3.11-slim）**：安装 `requirements.txt`，将前端构建产物复制到 `/app/static`，挂载数据卷 `/data` 用于 SQLite 持久化；
- **暴露与启动**：暴露 8080 单端口，通过 `uvicorn main:app --host 0.0.0.0 --port 8080` 启动。

---

## 4. 环境变量与配置规范 (`.env`)

```ini
# 数据库存储路径 (单容器持久化卷或本地 SQLite)
DATABASE_URL=sqlite:////data/world_sim.db

# 服务端配置 (LLM Base URL、API Key 与模型名称通过 Web UI 系统配置面板设置并持久化存储于 SQLite)
PORT=8080
LOG_LEVEL=INFO
REALTIME_TICK_HOURS=1
```


---

## 5. Vibe Coding 实施路线图 (Task Checklist)

供 AI 开发者自身执行任务时勾选的自洽实施步骤：

### Phase 1: 基础设施与数据层搭建
- [x] 创建后端虚拟环境，安装 FastAPI, uvicorn, sqlalchemy, pydantic, apscheduler, httpx, jieba。
- [x] 按照 [04_DATA_SCHEMA_AND_API.md](04_DATA_SCHEMA_AND_API.md) 编写 SQLite 实体模型与数据库初始化脚本。
- [x] 编写角色卡摄入服务，实现正则剔除 HTML、`{{user}}` 动机转写、世界书完整导入、多人卡 POV 单选与角色自适应作息画像生成。

### Phase 2: 双步推演核心引擎 (Pass 1 & Pass 2)
- [x] 实现 `Arbitrator` 裁决服务，集成精力条（Stamina）与环境判定驱动的自适应睡眠机制，输出严格结构化增量。
- [x] 实现 `Storyteller` 文学切片撰写服务，在 60k Token 预算内注入 Deep Working Buffer（10~20 轮上下文），以第三人称有限视角生成 300~600 字正文。
- [x] 编写三层高保真记忆管理服务，实现基于 SQLite 的实体关键词倒排索引与因果长程网召回。

### Phase 3: 时钟调度、突发事件与纯信号 API
- [x] 实现 APScheduler 1 小时自动定时器，编写长间隔作息补偿机制。
- [x] 实现纯按钮沙盒步进 API（+1h, +6h, +24h），加入 `asyncio.Lock` 并发保护。
- [x] 实现 AI 自主构思的突发事件触发接口（无用户文本输入）。
- [x] 完成卡片解析导入与极简表单 AI 生成端点。

### Phase 4: 前端新拟态组件与交互实现
- [x] 初始化 Vite + Vue 3 + Pinia + Tailwind 项目，引入 `@iconify/vue`（指定 `material-symbols`）。
- [x] 按照 [05_UI_UX_NEUMORPHIC_SPEC.md](05_UI_UX_NEUMORPHIC_SPEC.md) 注入 CSS 变量与双向阴影系统，开发 `NeuCard`、`NeuButton`、`NeuMeter`。
- [x] 绘制沉浸式小说长卷阅读流与右侧角色状态看板（无文本框与评论区）。

### Phase 5: 联调、容器化与交付验证
- [x] 前端打包产物接入 FastAPI 静态托管与 SPA 回退，验证单端口无 404。
- [x] 编写多阶段 Dockerfile，执行容器构建与端到端推演冒烟测试。
