# AGENTS.md

## AI 代理工作规范与执行准则 (Agent Entrypoint)

本文档是供所有在此代码库中执行任务的 AI 编程助手（AI Agents / AI Developers / Vibe Coding Assistants）阅读的最高指令入口。

---

## 1. 核心指令：查阅文档与目录重定向

所有 AI 代理在进行任何功能规划、架构设计、代码编写或缺陷修复前，必须先查阅 `docs/` 目录下的技术规范文档。

**AI 专属导航总目录文件位于：**
[docs/for-ai.md](docs/for-ai.md)

请务必先读取 [docs/for-ai.md](docs/for-ai.md)，根据你当前所负责的具体子模块（如角色卡摄入、时钟调度、双步推演、数据库设计、UI 组件开发等），跳转至对应的专业规范文档进行深度对齐。

---

## 2. 架构同步维护铁律 (Synchronous Documentation Invariant)

在项目开发、重构或演进过程中，AI 代理必须严格遵守以下规范维护铁律：

> **凡发生项目架构演进、技术栈调整、数据表 DDL 变更、API 接口协议改动、Prompt 结构修改或业务逻辑优化时，AI 代理必须在提交或交付代码的同时，同步更新 `docs/` 目录中对应的规范 Markdown 文件以及 [docs/for-ai.md](docs/for-ai.md)。**
>
> 严禁出现“代码已改动但技术规范文档依然停留在旧版本”的文档脱节现象。规范文档即为系统的第一真理源（Single Source of Truth）。

---

## 3. 全局技术与代码生成铁律

在编写任何文件或代码时，AI 代理必须无条件遵循以下红线约束：

1. **绝对无 Emoji 规范**：严禁在 UI 界面、系统日志、正文生成、代码注释或 Mock 数据中使用任何 Emoji 图标。所有图标一律采用 `@iconify/vue` 搭配 `material-symbols` 图标集。
2. **两步解耦原则（Two-Pass Pipeline）**：推演必须解耦为 Pass 1（Arbitrator 纯理性逻辑裁决）与 Pass 2（Storyteller 纯文学第三人称有限视角撰写），严禁单次 Prompt 混合生成。
3. **纯按钮无文本框交互**：虚拟世界推演界面彻底去除用户文本输入框，用户仅作为旁观者通过纯按钮（步进、快进、触发突发事件）进行观察，突发事件由 AI 自主构思衍生。
4. **单容器与单端口交付**：采用 FastAPI + SQLite 3，前端构建产物由后端直接静态托管，统一通过 8080 单端口向外提供服务。
