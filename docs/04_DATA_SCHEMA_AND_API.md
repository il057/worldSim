# 模块 04：数据表结构与纯按钮交互 API 契约规范 (Data Schema & API)

---

## 1. SQLite 核心表结构设计 (DDL)

系统采用轻量单文件 SQLite 3 作为全局存储引擎。表结构必须完整承载角色自适应作息、完整世界书、长程历史切片与降维社交关系。

### 1.1 核心数据表设计一览

```sql
-- 1. 角色核心表 (characters)
CREATE TABLE IF NOT EXISTS characters (
    id TEXT PRIMARY KEY,                       -- UUID 字符串 (如 c-9a4f-4b10)
    name TEXT NOT NULL,                        -- 角色姓名
    title TEXT,                                -- 头衔或职业定义
    avatar_url TEXT,                           -- 头像静态路径或 Base64
    persona_summary TEXT NOT NULL,             -- 核心性格底色与行为原则
    inner_drive TEXT NOT NULL,                 -- 内在终极心理动机与不可磨灭的执念
    circadian_profile_json TEXT NOT NULL,      -- JSON: 角色自适应作息画像 (节律倾向、休眠敏感度等)
    initial_snapshot_json TEXT,                -- JSON: 开局全量初始设置快照 (时间、地点、健康、精力、心理、背包、目标、初始NPC)
    is_active INTEGER DEFAULT 1,               -- 1=激活, 0=封存
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 角色即时生存状态看板表 (character_states)
CREATE TABLE IF NOT EXISTS character_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id TEXT NOT NULL UNIQUE,         -- 关联 characters.id
    virtual_time TEXT NOT NULL,                -- 虚拟世界时间字符串 (如 "霜降月 14日 22:00")
    location TEXT NOT NULL,                    -- 当前微观物理场景位置
    health INTEGER DEFAULT 100,                -- 生理健康值 (0 - 100)
    stamina INTEGER DEFAULT 100,               -- 体能/精力值 (0 - 100)，睡眠机制的核心驱动源
    is_sleeping INTEGER DEFAULT 0,             -- 当前是否处于休眠状态 (1=熟睡中, 0=清醒)
    psychological_state TEXT NOT NULL,         -- 情绪/心理状态短述
    inventory_json TEXT NOT NULL,              -- JSON Array: 随身物品列表
    active_goals_json TEXT NOT NULL,           -- JSON Array: 正在推进的目标列表
    completed_goals_json TEXT DEFAULT '[]',    -- JSON Array: 历史已达成目标列表
    total_ticks INTEGER DEFAULT 0,             -- 累计推进 Tick 计数
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
);

-- 3. 历史故事切片与推演流水表 (story_logs)
CREATE TABLE IF NOT EXISTS story_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id TEXT NOT NULL,
    tick_index INTEGER NOT NULL,               -- 递增步进序号
    virtual_time TEXT NOT NULL,                -- 故事切片发生时的虚拟时间
    location TEXT NOT NULL,                    -- 发生地点
    plot_beat TEXT NOT NULL,                   -- Pass 1 裁决出的客观事实骨架
    narrative_prose TEXT NOT NULL,             -- Pass 2 生成的 300~600 字文学正文
    delta_snapshot_json TEXT NOT NULL,         -- Pass 1 输出的状态增量完整快照 JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_story_logs_char_tick ON story_logs(character_id, tick_index);

-- 4. 完整世界书与背景条目表 (world_lores)
-- 允许容纳完整酒馆世界书，无字数压榨截断
CREATE TABLE IF NOT EXISTS world_lores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id TEXT,                         -- NULL 表示全局通用世界书，否则为角色特有
    category TEXT NOT NULL,                    -- 'static' (全局静态规则) | 'dynamic' (触发式条目)
    trigger_keys TEXT,                         -- 逗号分隔的触发词列表 (如 "旧铁道,动力核心,巡逻队")
    title TEXT NOT NULL,                       -- 条目标题
    content TEXT NOT NULL,                     -- 完整背景设定文本 (支持上万字无损存储)
    is_active INTEGER DEFAULT 1,
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
);

-- 5. 降维社交 NPC 关系表 (character_relationships)
CREATE TABLE IF NOT EXISTS character_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id TEXT NOT NULL,                -- 主角 POV ID
    npc_name TEXT NOT NULL,                    -- 次要角色姓名
    relation_type TEXT NOT NULL,               -- 关系性质: '同行者' | '契约者' | '故人' | '敌对'
    affinity INTEGER DEFAULT 50,               -- 好感/羁绊数值 (-100 ~ 100)
    summary TEXT NOT NULL,                     -- 关系渊源与 NPC 特征简述
    is_present INTEGER DEFAULT 0,              -- 1=在同场景, 0=未在场
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (character_id) REFERENCES characters(id) ON DELETE CASCADE
);

-- 6. 系统运行期配置与 LLM 连接参数表 (system_configs)
-- 替代 .env 敏感与动态配置，实现 Web UI 在线配置与持久化
CREATE TABLE IF NOT EXISTS system_configs (
    key TEXT PRIMARY KEY,                      -- 配置键 (如 'llm_base_url', 'llm_api_key', 'llm_model_name', 'llm_context_window', 'realtime_tick_hours', 'enable_stream_display', 'enable_phone_simulation')
    value TEXT NOT NULL,                       -- 配置值文本
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 2. 纯按钮交互 RESTful API 契约设计

为保障“用户仅作为旁观者，界面无任何文本输入框”的原则，所有运行期推进接口均设计为纯信号触发。统一前缀为 `/api/v1`。

### 2.1 摄入与 POV 实体解析
 
#### POST `/api/v1/cards/parse`
- **功能**：上传酒馆角色卡文件（JSON / PNG），后端完成正则清洗、世界书状态栏过滤、多实体识别（含世界书人物）、NPC 关系提取与全量人设保留。
- **响应契约（Response 200）**：
  返回 `is_multi_entity` 布尔值、`detected_entities` 候选实体列表（包含全量人设、作息画像与建议初始状态）、`detected_relationships`（识别到的社交 NPC 列表）、`total_lore_entries` 及清洗后的世界书条目列表 `lores`。

#### POST `/api/v1/cards/import`
- **功能**：用户在前端全维度审查并微调后，确定 POV 主角并提交落库初始化。
- **请求体（Request Body）**：
  ```json
  {
    "selected_entity": {
      "entity_id": "ent_1",
      "name": "白昱",
      "title": "九尾天狐",
      "persona_summary": "...",
      "inner_drive": "...",
      "circadian_profile": { ... },
      "initial_location": "长宁市古董街老宅正堂",
      "initial_virtual_time": "深秋月 初九 19:30",
      "initial_health": 100,
      "initial_stamina": 90,
      "initial_psychological_state": "慵懒且警觉",
      "initial_inventory": ["云雷纹旧玉烟杆", "泛黄的晚唐地志手抄本"],
      "initial_goals": ["审视古董街周围灵气异动"]
    },
    "all_entities": [ ... ],
    "lores": [ ... ],
    "relationships": [
      {
        "npc_name": "李震 (Li Zhen)",
        "relation_type": "供养者 / 麻烦制造者",
        "affinity": 50,
        "summary": "异管局局长。做事谨小慎微..."
      }
    ],
    "initial_location": "长宁市古董街老宅正堂",
    "initial_virtual_time": "深秋月 初九 19:30"
  }
  ```
- **响应契约（Response 201）**：
  返回创建完成的 `character_id`、`name` 以及提示信息。

#### POST `/api/v1/characters/generate-quick`
- **功能**：由极简表单（4 维度）通过 AI 一键衍生全套标准化角色实体与作息画像。

---

### 2.2 纯按钮推进与沙盒控制接口

#### POST `/api/v1/sim/step`
- **功能**：单步微步进。用户点击界面 `[+1h]` 按钮时触发。
- **请求体（Request Body）**：
```json
{
  "character_id": "c-9a4f-4b10",
  "hours": 1
}
```
- **内部流转**：获取异步并发锁 -> 检查当前精力值与作息画像 -> Pass 1 裁决 -> 更新状态看板 -> Pass 2 撰写正文 -> 写入 `story_logs` -> 释放锁。
- **响应体（Response 200）**：返回新增的故事切片与最新的看板数值。

#### POST `/api/v1/sim/continue` 与 `/api/v1/sim/continue-stream`
- **功能**：智能自由续写（单次请求或 SSE 流式）。用户点击界面 `[续写]` 按钮时触发。
- **请求体（Request Body）**：
```json
{
  "character_id": "c-9a4f-4b10",
  "config": { ... }
}
```
- **核心契约**：不限定死板推进小时数，由 AI 裁决机结合当前场景目标、未完成互动与戏剧压力，自主研判本次演化跨越的合理时间尺度（输出至 `ArbitratorDelta.simulated_hours_passed: float`），维持“起—扬—收”呼吸感并产出无缝接力的小说正文。

#### POST `/api/v1/sim/fast-forward`
- **功能**：阶段快进或跨日跃迁。用户点击界面 `[+6h]` 或 `[+24h]` 按钮时触发。
- **请求体（Request Body）**：
```json
{
  "character_id": "c-9a4f-4b10",
  "step_type": "hour_6" // 可选: "hour_6" | "day_1"
}
```
- **内部流转**：执行大颗粒度作息折叠推进，最后 1 小时产出代表性切片正文。

#### POST `/api/v1/sim/trigger-incident` 与 `/api/v1/sim/trigger-incident-stream`
- **功能**：触发突发事件。用户在弹窗中选择“由 AI 决定”或输入“自定义事件”时触发。
- **请求体（Request Body）**：
```json
{
  "character_id": "c-9a4f-4b10",
  "incident_description": "走廊广播突然播放紧急集合通知" // 可选，留空则由 AI 结合世界观自主衍生
}
```
- **核心契约约束**：
  - 若 `incident_description` 留空/未传：启动题材自适应构思引擎，结合当前题材画风（校园、都市、奇幻等）构思自然变故，坚决杜绝生搬硬套脱节的激进仇杀；
  - 若 `incident_description` 有值：直接将用户指定的事件作为最高主导因注入 Pass 1 裁决。

---

### 2.3 状态查询与历史长卷接口

#### GET `/api/v1/characters/{character_id}/state`
- **功能**：查询当前角色的 Living State 看板（含生命、精力、休眠中状态、随身物品、当前目标）。

#### GET `/api/v1/characters/{character_id}/timeline`
- **功能**：分页拉取小说正文切片流水。
- **查询参数**：`page=1&page_size=20`
- **响应内容**：返回按 `tick_index` 正序排列的高精小说切片数组，包含文学正文、客观事实骨架及对应的状态增量快照。

#### POST `/api/v1/characters/{character_id}/reset`
- **功能**：重置当前角色世界。清空全部 `story_logs`，将状态回滚至初始状态（开局处境）。

#### DELETE `/api/v1/characters/{character_id}`
- **功能**：彻底删除角色及其全部关联数据。级联清理 `character_states`、`story_logs`、专属 `world_lores` 以及 `character_relationships`。

---

### 2.4 世界书管理与系统配置接口

#### GET `/api/v1/characters/{character_id}/lores`
- **功能**：获取角色关联的世界书条目列表（包括全局常驻与动态触发）。

#### POST `/api/v1/characters/{character_id}/lores`
- **功能**：录入自定义世界书条目（分类、触发词、标题与完整内容）。

#### PUT `/api/v1/characters/{character_id}/lores/{lore_id}`
- **功能**：编辑与更新指定世界书条目（可修改分类、触发词、标题、设定正文及激活状态）。
- **请求体（Request Body）**：
```json
{
  "category": "static", // 或 "dynamic"
  "trigger_keys": "核心,工坊", // 动态关键词
  "title": "更新后的条目标题",
  "content": "更新后的完整世界观背景正文...",
  "is_active": 1
}
```

#### DELETE `/api/v1/characters/{character_id}/lores/{lore_id}`
- **功能**：删除指定世界书条目。

#### GET `/api/v1/characters/system/config`
- **功能**：获取系统当前 LLM Base URL、模型名称、API Key 状态与真实时钟调度步长（从 SQLite 数据库持久化读取）。

#### POST `/api/v1/characters/system/config`
- **功能**：在线修改并热更新 LLM API 配置与沙盒推演参数，持久化至 SQLite 数据库 `system_configs` 表。

#### POST `/api/v1/characters/system/fetch-models`
- **功能**：根据填入或已保存的 Base URL 与 API Key，向兼容 OpenAI 规范的 `/models` 接口发送探测请求并拉取返回可用模型标识列表。
- **请求体（Request Body）**：
```json
{
  "llm_base_url": "https://api.openai.com/v1",
  "llm_api_key": "sk-xxxx" // 可选，若为空则自动取数据库已存配置
}
```
- **响应体（Response 200）**：
```json
{
  "models": ["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet-20241022"]
}
```

---

### 3.4 推演异常标准化错误协议与错误码字典 (Error Code Specification)

当推演过程（Pass 1 裁决或 Pass 2 叙事）发生异常时，接口返回 `HTTP 4xx / 5xx`，并在响应体 `detail` 中封装结构化对象，保障事务已自动回滚且数据库未被污染：

```json
{
  "detail": {
    "error_code": "AUTH_FAILED",
    "message": "API Key 鉴权失败或无权限"
  }
}
```

| 错误代码 (error_code) | 产生阶段与触发条件 | 客户端 (前端) 针对性指引建议 |
| :--- | :--- | :--- |
| `AUTH_FAILED` | HTTP 401 / 403 鉴权失败 | 提示打开右上角设置，检查 API Key 拼写与访问权限。 |
| `RATE_LIMIT_OR_QUOTA` | HTTP 429 频次受限或欠费 | 提示稍后重试，或检查第三方模型账户剩余额度。 |
| `MODEL_NOT_FOUND` | HTTP 404 模型标识不存在 | 提示检查当前选中的模型标识，建议重新探测模型。 |
| `NETWORK_TIMEOUT` | 网络请求超时 (180s) | 提示检查网络环境或中转服务状态，并引导用户点击重试。 |
| `NETWORK_ERROR` | 连接建立失败 (ECONNREFUSED) | 提示检查 Base URL 地址及代理网络配置。 |
| `PASS1_FAILED` | Pass 1 裁决输出解析失败 | 提示已保护数据并回滚，引导用户直接点击重试。 |
| `PASS2_FAILED` | Pass 2 场景正文生成中断 | 提示已保护数据并回滚，引导用户直接点击重试。 |
| `EMPTY_RESPONSE` | 模型响应内容为空白 | 提示正文生成未完成，引导用户点击重试或调整参数。 |
| `SIM_INTERNAL_ERROR` | 服务端未捕获的其它异常 | 提示推演引擎暂时异常，事务已回滚，稍后重试。 |


