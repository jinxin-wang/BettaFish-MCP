# BettaFish MCP 改造方案

## 一、概述

本文档描述如何将 BettaFish（微舆）项目改造为 MCP（Model Context Protocol）服务。

### 1.1 项目现状

BettaFish 是一个多智能体舆情分析系统，包含以下核心模块：

| 模块 | 路径 | 功能 |
|-----|------|------|
| QueryEngine | `QueryEngine/` | 国内外新闻广度搜索 |
| MediaEngine | `MediaEngine/` | 多模态内容分析 |
| InsightEngine | `InsightEngine/` | 私有数据库挖掘 |
| ReportEngine | `ReportEngine/` | 智能报告生成 |
| ForumEngine | `ForumEngine/` | Agent 协作论坛 |
| MindSpider | `MindSpider/` | 社交媒体爬虫 |

### 1.2 改造目标

1. **保留现有 Flask 前端** - 不改变现有 Web 界面（:5000）
2. **HTTP/SSE 传输** - MCP 服务通过 HTTP/SSE 提供
3. **远程可访问** - MCP 服务可被远程客户端调用
4. **全功能暴露** - 搜索、媒体分析、舆情查询、报告生成完整链路
5. **异步任务支持** - 长时任务不阻塞客户端，支持实时进度推送

---

## 二、MCP 工具三层架构

MCP 工具按功能深度分为三个层级，模拟主应用的完整分析流程：

### 2.1 三层工具概览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MCP 工具三层架构                                      │
└─────────────────────────────────────────────────────────────────────────────┘

Level 1: 单次搜索查询 (单次工具调用，返回原始搜索结果)
├── search_news              # QueryEngine 单次新闻搜索
├── analyze_media           # MediaEngine 单次多模态搜索
├── query_sentiment         # InsightEngine 单次数据库查询
├── crawl_data              # MindSpider 单次数据爬取
├── crawl_topics            # MindSpider 热点话题提取
├── check_spider_status     # 爬虫系统状态检查
├── analyze_sentiment_texts # 独立文本情感分析
└── query_trending          # 热门内容查询

Level 2: 单Agent完整分析流程 (模拟单个Streamlit应用的完整流程，异步执行)
├── start_search_full       # 启动 QueryEngine 完整分析 (异步)
├── get_search_full_status  # 查询分析进度 (轮询)
├── get_search_full_result  # 获取分析结果
├── subscribe_search_full   # 订阅实时进度 (SSE)
├── start_media_full        # 启动 MediaEngine 完整分析 (异步)
├── get_media_full_status   # 查询分析进度
├── get_media_full_result   # 获取分析结果
├── subscribe_media_full    # 订阅实时进度 (SSE)
├── start_sentiment_full    # 启动 InsightEngine 完整分析 (异步)
├── get_sentiment_full_status
├── get_sentiment_full_result
├── subscribe_sentiment_full
└── crawl_data_full         # MindSpider 完整爬取+分析流程 (异步)

Level 3: 多Agent协作+报告生成 (模拟主应用ForumEngine协作+ReportEngine，异步执行)
├── start_forum_research    # 启动ForumEngine + 3个Agent并行研究 (异步)
├── get_forum_progress      # 查询论坛研究进度 (轮询)
├── get_forum_result        # 获取论坛研究结果
├── subscribe_forum         # 订阅论坛实时进度 (SSE)
├── stop_forum_research     # 停止论坛研究
├── get_forum_discussion    # 获取论坛讨论内容
├── start_report            # 启动最终报告生成 (异步)
├── get_report_status       # 查询报告生成进度
├── get_report_result       # 获取报告结果
└── subscribe_report        # 订阅报告生成进度 (SSE)
```

### 2.2 三层流程对比

| 特性 | Level 1 | Level 2 | Level 3 |
|------|---------|---------|---------|
| **工具调用次数** | 1次 | 2-3次 (提交+查询) | 3-4次 (提交+查询+获取) |
| **执行时间** | 秒级 | 分钟级 | 十分钟级 |
| **输出内容** | 原始搜索结果 | 单Agent完整报告 | 多Agent综合报告 |
| **内部流程** | 单次 `execute_search_tool()` | `agent.research()` | ForumEngine + 3x Agent + ReportEngine |
| **异步模式** | ❌ (同步) | ✅ (异步) | ✅ (异步) |
| **SSE 实时推送** | ❌ | ✅ (可选) | ✅ (可选) |
| **ForumEngine协作** | ❌ | ❌ | ✅ |
| **多轮反思循环** | ❌ | ✅ | ✅ |
| **报告生成** | ❌ | ✅ (单Agent) | ✅ (综合) |
| **适用场景** | 快速查询 | 深度单领域分析 | 全面舆情分析 |

### 2.3 完整分析流程参考

主应用"一次完整分析流程"（来自 README.md）：

| 步骤 | 阶段名称 | 主要操作 | 参与组件 | 循环特性 |
|------|----------|----------|----------|----------|
| 1 | 用户提问 | Flask主应用接收查询 | Flask主应用 | - |
| 2 | 并行启动 | 三个Agent同时开始工作 | Query/Media/Insight Agent | - |
| 3 | 初步分析 | 各Agent使用专属工具进行概览搜索 | 各Agent + 专属工具集 | - |
| 4 | 策略制定 | 基于初步结果制定分块研究策略 | 各Agent内部决策模块 | - |
| 5-N | **循环阶段** | **论坛协作 + 深度研究** | **ForumEngine + 所有Agent** | **多轮循环** |
| 5.1 | 深度研究 | 各Agent基于论坛主持人引导进行专项搜索 | 各Agent + 反思机制 + 论坛引导 | 每轮循环 |
| 5.2 | 论坛协作 | ForumEngine监控Agent发言并生成主持人引导 | ForumEngine + LLM主持人 | 每轮循环 |
| 5.3 | 交流融合 | 各Agent根据讨论调整研究方向 | 各Agent + forum_reader工具 | 每轮循环 |
| N+1 | 结果整合 | Report Agent收集所有分析结果和论坛内容 | Report Agent | - |
| N+2 | IR中间表示 | 动态选择模板和样式，多轮生成元数据，装订为IR中间表示 | Report Agent + 模板引擎 | - |
| N+3 | 报告生成 | 分块进行质量检测，基于IR渲染成交互式 HTML 报告 | Report Agent + 装订引擎 | - |

---

## 三、架构设计

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                     Flask App (:5000)                       │
│                                                             │
│   ┌──────────────┐   ┌──────────────┐   ┌───────────────┐   │
│   │ Report BP    │   │ MCP BP       │   │   Web UI     │   │
│   │ /api/report  │   │   /mcp/*     │   │   /           │   │
│   └──────────────┘   └──────────────┘   └───────────────┘   │
│                              │                              │
│                              ▼                              │
│                    ┌────────────────┐                      │
│                    │ MCP Server     │                      │
│                    │  (HTTP/SSE)   │                      │
│                    └────────────────┘                      │
│                              │                              │
│                              ▼                              │
│                    ┌────────────────┐                      │
│                    │ TaskRegistry   │                      │
│                    │ (异步任务管理)  │                      │
│                    └────────────────┘                      │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────┼─────────────────────────────┐
│                             │                              │
│   Level 1/2 Tools           │   Level 3 Tools              │
│   (直接调用Agent)            │   (ForumEngine协作)          │
│                             │                              │
│   ┌─────────┐ ┌─────────┐   │   ┌──────────────────────┐  │
│   │Query    │ │Media    │   │   │   ForumEngine         │  │
│   │Engine   │ │Engine   │   │   │   LogMonitor         │  │
│   └─────────┘ └─────────┘   │   │   ForumHost (LLM)     │  │
│                             │   └──────────────────────┘  │
│   ┌─────────┐ ┌─────────┐   │              │              │
│   │Insight  │ │Mind     │   │   ┌──────────┴──────────┐   │
│   │Engine   │ │Spider   │   │   ▼                   ▼   │
│   └─────────┘ └─────────┘   │   3x Agent 并行         Report│
│                             │   (Query/Media/Insight)  Engine│
└─────────────────────────────────────────────────────────────┘
```

### 3.2 部署拓扑

| 模式 | 启动方式 | MCP 端点 | 说明 |
|-----|---------|---------|------|
| **嵌入 Flask** | `python app.py` | `http://localhost:5000/mcp` | 推荐：统一进程管理 |
| **独立服务** | `python mcp_server.py` | `http://localhost:5100/mcp` | 可选：独立进程 |

### 3.3 异步任务架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         异步任务架构 (方案C: 混合模式)                         │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│           MCP Client (LLM Agent)        │
└─────────────────┬───────────────────────┘
                  │
                  │ 1. 提交任务
                  ▼
┌─────────────────────────────────────────┐
│           TaskRegistry                  │
│  ┌───────────────────────────────────┐  │
│  │ task_id: "xxx"                     │  │
│  │ status: "pending" → "running" →    │  │
│  │           "completed"/"failed"      │  │
│  │ progress: 0-100%                   │  │
│  │ stage: "initial" → "research" →... │  │
│  │ result: {...}                      │  │
│  │ error: "..."                        │  │
│  │ created_at: "..."                  │  │
│  │ started_at: "..."                 │  │
│  │ completed_at: "..."               │  │
│  └───────────────────────────────────┘  │
└─────────────────┬───────────────────────┘
                  │
      ┌───────────┼───────────┐
      │           │           │
      ▼           ▼           ▼
  ┌────────┐  ┌────────┐  ┌────────┐
  │轮询模式│  │SSE模式 │  │文件持久化│
  │        │  │        │  │        │
  │ GET    │  │ GET    │  │ logs/  │
  │ /status│  │ /stream│  │ mcp_   │
  │        │  │        │  │ tasks/ │
  └────────┘  └────────┘  └────────┘
```

---

## 四、异步任务支持

### 4.1 设计目标

1. **支持长时任务** - Level 2/3 工具执行时间可达分钟级到小时级
2. **不阻塞客户端** - MCP 客户端提交任务后立即返回，不等待完成
3. **实时进度反馈** - 支持轮询和 SSE 实时推送两种模式
4. **任务持久化** - 任务状态和结果持久化到文件系统
5. **资源管理** - 限制并发任务数，自动清理过期任务

### 4.2 混合模式设计

**轮询模式（基础）**：
```python
# 1. 提交任务
result = start_search_full(query="研究主题")
# 返回: {"success": true, "task_id": "xxx", "status": "pending"}

# 2. 轮询状态
status = get_search_full_status(task_id="xxx")
# 返回: {"success": true, "status": "running", "progress": 45, "stage": "research"}

# 3. 获取结果
result = get_search_full_result(task_id="xxx")
# 返回: {"success": true, "status": "completed", "result": {...}}
```

**SSE 模式（可选，实时性好）**：
```python
# 1. 提交任务
result = start_search_full(query="研究主题")

# 2. 订阅 SSE 流
sse_response = subscribe_search_full(task_id="xxx")
# SSE 实时推送: {"event": "progress", "progress": 10, "stage": "initial"}
# SSE 实时推送: {"event": "progress", "progress": 50, "stage": "research"}
# SSE 实时推送: {"event": "completed", "result": {...}}
```

### 4.3 任务状态机

```
┌──────────┐     submit      ┌──────────┐
│  TASK    │ ──────────────► │  PENDING │
│  CREATED │                 │          │ ◄── 等待调度
└──────────┘                 └─────┬────┘
                                  │ start
                                  ▼
                           ┌────────────┐
                           │  RUNNING   │
                           │            │
                           │ ┌────────┐ │
                           │ │progress│ │ ◄── 实时更新 0-100%
                           │ │ stage  │ │
                           │ └────────┘ │
                           └─────┬──────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
                    ▼            │            ▼
            ┌────────────┐       │     ┌────────────┐
            │ COMPLETED  │       │     │   FAILED   │
            │            │       │     │            │
            │ result: {} │       │     │ error: ... │
            └────────────┘       │     └────────────┘
                                 │
                                 ▼
                          ┌────────────┐
                          │ CANCELLED  │ ◄── 用户主动取消
                          │            │
                          └────────────┘
```

### 4.4 TaskRegistry 核心功能

| 方法 | 说明 |
|------|------|
| `create_task(task_type, params)` | 创建新任务，返回 task_id |
| `get_task(task_id)` | 获取任务详情 |
| `get_task_status(task_id)` | 获取任务状态和进度 |
| `get_task_result(task_id)` | 获取任务结果 |
| `update_progress(task_id, progress, stage)` | 更新任务进度 |
| `complete_task(task_id, result)` | 标记任务完成 |
| `fail_task(task_id, error)` | 标记任务失败 |
| `cancel_task(task_id)` | 取消任务 |
| `list_tasks(task_type, status)` | 列出任务 |
| `cleanup_expired()` | 清理过期任务 |

### 4.5 任务存储设计

**内存存储**（保证速度）：
```python
_task_store = {}  # {task_id: TaskInfo}
```

**文件持久化**（重启不丢失）：
```
logs/
└── mcp_tasks/
    ├── tasks.json          # 任务索引
    └── results/
        ├── {task_id}.json  # 任务结果
        └── {task_id}.error # 错误信息
```

### 4.6 任务过期与清理

| 任务状态 | TTL | 说明 |
|---------|-----|------|
| `completed` | 1小时 | 成功后保留1小时供查询 |
| `failed` | 24小时 | 失败保留24小时供调试 |
| `running` | 永不过期 | 运行中任务不清理 |
| `pending` | 1小时 | 等待中任务超时取消 |

### 4.7 并发控制

| 配置项 | 值 | 说明 |
|--------|-----|------|
| 最大并发任务数 | 3 | 每种类型最多同时运行3个任务 |
| 任务队列大小 | 10 | 超出后拒绝新任务 |
| 单任务超时 | 可配置 | 默认 600秒 (Level 2) / 1800秒 (Level 3) |

---

## 五、文件清单

### 5.1 新增文件

```
BettaFish-MCP/
├── mcp/                              # MCP 模块目录
│   ├── __init__.py                   # 模块初始化
│   ├── blueprint.py                  # Flask Blueprint 定义
│   ├── server.py                     # MCP Server 封装
│   ├── task_registry.py              # 异步任务注册中心 (NEW)
│   ├── resources.py                  # Resources 定义
│   ├── prompts.py                    # Prompts 定义
│   └── tools/                        # Tools 目录
│       ├── __init__.py
│       ├── search.py                 # Level 1: search_news
│       │                             # Level 2: start_search_full + get_search_full_status + get_search_full_result
│       ├── media.py                  # Level 1: analyze_media
│       │                             # Level 2: start_media_full + get_media_full_status + get_media_full_result
│       ├── sentiment.py              # Level 1: query_sentiment
│       │                             # Level 2: start_sentiment_full + get_sentiment_full_status + get_sentiment_full_result
│       ├── report.py                 # Level 3: start_report + get_report_status + get_report_result
│       ├── crawl.py                  # Level 1/2: crawl_data + crawl_data_full
│       └── forum.py                  # Level 3: ForumEngine协作工具 (NEW)
├── logs/
│   └── mcp_tasks/                    # 任务持久化目录 (NEW)
│       ├── tasks.json
│       └── results/
├── mcp_server.py                     # 独立运行入口
└── (现有文件保持不变)
```

### 5.2 修改文件

| 文件路径 | 修改内容 | 复杂度 |
|---------|---------|-------|
| `mcp/blueprint.py` | 注册 Level 2/3 新工具 + 任务管理端点 | ⭐⭐ |
| `mcp/resources.py` | 添加 Level 2/3 相关资源 + 任务状态资源 | ⭐ |
| `mcp/prompts.py` | 添加 Level 2/3 相关提示词 | ⭐ |

---

## 六、Tools 详细设计

### 6.1 Level 1 工具 (已有，同步模式)

#### search_news
- **文件**: `mcp/tools/search.py`
- **模式**: 同步（秒级完成）
- **内部调用**: `DeepSearchAgent.execute_search_tool()`
- **返回**: 原始搜索结果列表

#### analyze_media
- **文件**: `mcp/tools/media.py`
- **模式**: 同步
- **内部调用**: `DeepSearchAgent.execute_search_tool()`
- **返回**: 原始多模态搜索结果

#### query_sentiment
- **文件**: `mcp/tools/sentiment.py`
- **模式**: 同步
- **内部调用**: `DeepSearchAgent.execute_search_tool()`
- **返回**: 原始舆情数据列表

### 6.2 Level 2 工具 (异步模式)

#### start_search_full / get_search_full_status / get_search_full_result
- **文件**: `mcp/tools/search.py`
- **模式**: 异步（分钟级）
- **内部调用**: `DeepSearchAgent().research()`
- **提交参数**:
  - `query`: 研究主题
  - `max_reflections`: 反思轮数 (默认3)
  - `save_report`: 是否保存报告文件 (默认True)
  - `timeout`: 超时时间 (秒, 默认600)
- **提交返回**:
  ```json
  {
    "success": true,
    "task_id": "search_full_xxx",
    "status": "pending",
    "message": "分析任务已提交"
  }
  ```
- **状态返回**:
  ```json
  {
    "success": true,
    "task_id": "search_full_xxx",
    "status": "running",
    "progress": 45,
    "stage": "reflection_loop",
    "stage_detail": "正在处理段落 3/6",
    "message": "分析进行中"
  }
  ```
- **结果返回**:
  ```json
  {
    "success": true,
    "task_id": "search_full_xxx",
    "status": "completed",
    "query": "研究主题",
    "report_content": "# Markdown报告内容",
    "report_file": "query_engine_streamlit_reports/deep_search_report_xxx.md",
    "paragraphs_count": 6,
    "reflections_per_paragraph": 3,
    "total_searches": 24,
    "execution_time_seconds": 180,
    "message": "分析完成"
  }
  ```

#### start_media_full / get_media_full_status / get_media_full_result
- **文件**: `mcp/tools/media.py`
- **模式**: 异步
- **参数/返回**: 同 `start_search_full` 系列

#### start_sentiment_full / get_sentiment_full_status / get_sentiment_full_result
- **文件**: `mcp/tools/sentiment.py`
- **模式**: 异步
- **参数/返回**: 同 `start_search_full` 系列

#### crawl_data_full
- **文件**: `mcp/tools/crawl.py`
- **模式**: 异步
- **提交参数**:
  - `keywords`: 关键词列表
  - `platforms`: 平台列表
  - `crawl_then_analyze`: 爬取后是否分析 (默认True)
  - `max_keywords`: 最大关键词数
  - `max_notes`: 每关键词最大条数
  - `timeout`: 超时时间 (秒, 默认3600)

### 6.3 Level 3 工具 (异步模式)

#### start_forum_research / get_forum_progress / get_forum_result / subscribe_forum
- **文件**: `mcp/tools/forum.py`
- **模式**: 异步（十分钟级）
- **内部调用**: `ForumEngine/monitor.py` + 3x `DeepSearchAgent().research()`
- **提交参数**:
  - `topic`: 研究主题
  - `engines`: 启用的引擎列表 ["query", "media", "insight"] (默认全部)
  - `timeout`: 超时时间 (秒, 默认1800)
- **提交返回**:
  ```json
  {
    "success": true,
    "task_id": "forum_xxx",
    "status": "pending",
    "message": "ForumEngine研究任务已提交"
  }
  ```
- **状态返回**:
  ```json
  {
    "success": true,
    "task_id": "forum_xxx",
    "status": "running",
    "progress": 45,
    "engines": {
      "query": {"progress": 60, "stage": "reflection_loop", "paragraphs": "4/6"},
      "media": {"progress": 40, "stage": "initial_search", "paragraphs": "2/6"},
      "insight": {"progress": 100, "stage": "completed", "paragraphs": "6/6"}
    },
    "host_speeches_count": 3,
    "total_speeches": 18,
    "message": "研究进行中"
  }
  ```
- **结果返回**:
  ```json
  {
    "success": true,
    "task_id": "forum_xxx",
    "status": "completed",
    "topic": "研究主题",
    "reports": {
      "query": {"file": "query_engine_streamlit_reports/xxx.md"},
      "media": {"file": "media_engine_streamlit_reports/xxx.md"},
      "insight": {"file": "insight_engine_streamlit_reports/xxx.md"}
    },
    "total_speeches": 25,
    "host_speeches": [{"timestamp": "...", "content": "..."}],
    "execution_time_seconds": 600,
    "message": "ForumEngine研究完成"
  }
  ```

#### stop_forum_research
- **文件**: `mcp/tools/forum.py`
- **功能**: 停止正在运行的论坛研究任务

#### get_forum_discussion
- **文件**: `mcp/tools/forum.py`
- **功能**: 获取论坛讨论内容
- **参数**:
  - `task_id`: 任务ID
  - `limit`: 返回最近N条 (默认50)
  - `include_host`: 是否包含主持人发言 (默认True)
- **返回**:
  ```json
  {
    "success": true,
    "task_id": "forum_xxx",
    "discussions": [
      {"timestamp": "10:30:15", "source": "QUERY", "content": "..."},
      {"timestamp": "10:31:20", "source": "MEDIA", "content": "..."},
      {"timestamp": "10:32:00", "source": "HOST", "content": "..."}
    ],
    "count": 10
  }
  ```

#### start_report / get_report_status / get_report_result
- **文件**: `mcp/tools/report.py`
- **模式**: 异步
- **内部调用**: `ReportEngine.flask_interface`
- **提交参数**:
  - `topic`: 报告主题
  - `template`: 模板名称 (可选)
  - `timeout`: 超时时间 (秒, 默认600)

### 6.4 SSE 实时推送

所有 Level 2/3 工具支持可选的 SSE 订阅：

**订阅端点**: `/mcp/task/<task_id>/stream`

**SSE 事件格式**:
```
event: progress
data: {"progress": 10, "stage": "initial", "message": "任务已启动"}

event: progress
data: {"progress": 30, "stage": "research", "message": "正在搜索..."}

event: progress
data: {"progress": 60, "stage": "reflection", "message": "正在进行反思..."}

event: completed
data: {"task_id": "xxx", "result": {...}}

event: failed
data: {"task_id": "xxx", "error": "超时错误"}
```

---

## 七、Resources 设计

### 7.1 Level 1/2 相关资源

| Resource URI | 说明 |
|-------------|------|
| `bettafish://server/info` | MCP服务器信息 |
| `bettafish://engines/list` | 可用分析引擎列表 |
| `bettafish://platforms/supported` | 支持的社交媒体平台 |
| `bettafish://search/types` | 搜索类型说明 |
| `bettafish://sentiment/levels` | 情感分析级别说明 |
| `bettafish://report/templates` | 可用的报告模板 |

### 7.2 Level 2/3 相关资源 (新增)

| Resource URI | 说明 |
|-------------|------|
| `bettafish://tasks/status` | 当前任务状态概览 |
| `bettafish://tasks/list` | 任务列表 |
| `bettafish://forum/engines` | ForumEngine引擎状态 |
| `bettafish://forum/roles` | 各Agent在论坛中的角色说明 |
| `bettafish://forum/workflow` | 论坛协作工作流程 |

---

## 八、Prompts 设计

### 8.1 Level 1/2 相关提示词 (已有)

| Prompt 名称 | 说明 |
|------------|------|
| `comprehensive_analysis` | 综合舆情分析 |
| `brand_reputation_check` | 品牌声誉检查 |
| `crisis_detection` | 危机检测 |
| `media_content_analysis` | 媒体内容分析 |
| `competitor_comparison` | 竞品对比分析 |
| `social_media_crawl` | 社交媒体数据采集 |
| `trend_report` | 趋势报告生成 |
| `daily_briefing` | 每日舆情简报 |

### 8.2 Level 2/3 相关提示词 (新增)

| Prompt 名称 | 说明 |
|------------|------|
| `async_task_usage` | 异步任务使用指南 |
| `forum_research` | 启动Forum多Agent协作研究 |
| `forum_guidance` | 论坛主持人引导生成提示 |
| `multi_agent_synthesis` | 多Agent结果综合分析 |
| `final_report_generation` | 最终报告生成提示 |

---

## 九、ForumEngine 协作机制

### 9.1 核心组件

| 组件 | 文件 | 作用 |
|------|------|------|
| LogMonitor | `ForumEngine/monitor.py` | 监控三个引擎的日志文件，检测 SummaryNode 输出 |
| ForumHost | `ForumEngine/llm_host.py` | LLM主持人（Qwen3模型），生成战略引导 |
| forum_reader | `utils/forum_reader.py` | Agent读取论坛日志的工具 |

### 9.2 协作流程

```
1. LogMonitor 监控三个引擎的日志文件 (insight.log/media.log/query.log)
         ↓
2. 检测到 SummaryNode 输出 (Agent完成一轮研究)
         ↓
3. 捕获Agent研究总结，写入 forum.log
         ↓
4. 每5条Agent发言 → 触发 ForumHost (LLM主持人)
         ↓
5. ForumHost 分析所有发言，生成战略引导
         ↓
6. 各Agent使用 forum_reader 读取主持人引导
         ↓
7. 调整研究方向，继续下一轮循环
         ↓
8. 直到所有Agent完成研究
```

---

## 十、配置说明

### 10.1 环境变量

```bash
# MCP 服务配置
MCP_ENABLED=true
MCP_SSE_HEARTBEAT_INTERVAL=15
MCP_SSE_IDLE_TIMEOUT=120

# 异步任务配置
MCP_MAX_CONCURRENT_TASKS=3
MCP_TASK_SUCCESS_TTL=3600       # 成功后保留1小时
MCP_TASK_FAILED_TTL=86400       # 失败后保留24小时
MCP_TASK_PENDING_TTL=3600       # 等待中超时1小时

# Level 3 需要额外配置 (ForumEngine)
FORUM_HOST_API_KEY=        # 论坛主持人LLM密钥
FORUM_HOST_BASE_URL=       # 论坛主持人API地址
FORUM_HOST_MODEL_NAME=     # 论坛主持人模型
```

### 10.2 客户端配置

**远程模式（HTTP）**：
```json
{
  "mcpServers": {
    "BettaFish": {
      "url": "http://your-server:5000/mcp"
    }
  }
}
```

---

## 十一、实施步骤

### 阶段一：基础设施 (已完成)

- [x] 1.1 创建 MCP 模块目录（mcp/__init__.py）
- [x] 1.2 创建 MCP Server（mcp/server.py）
- [x] 1.3 创建 Flask Blueprint（mcp/blueprint.py）

### 阶段二：Level 1 Tools (已完成)

- [x] 2.1 创建 Tools 模块（mcp/tools/__init__.py）
- [x] 2.2 实现搜索工具（mcp/tools/search.py）
- [x] 2.3 实现媒体分析工具（mcp/tools/media.py）
- [x] 2.4 实现舆情查询工具（mcp/tools/sentiment.py）
- [x] 2.5 实现报告生成工具（mcp/tools/report.py）
- [x] 2.6 实现爬虫工具（mcp/tools/crawl.py）

### 阶段三：Resources 和 Prompts (已完成)

- [x] 3.1 实现 Resources（mcp/resources.py）
- [x] 3.2 实现 Prompts（mcp/prompts.py）

### 阶段四：集成 (已完成)

- [x] 4.1 注册 MCP Blueprint（app.py）
- [x] 4.2 更新环境变量示例（.env.example）

### 阶段五：异步任务基础设施 🔄 进行中

- [ ] 5.1 创建 TaskRegistry 类（mcp/task_registry.py）
- [ ] 5.2 实现任务状态管理（pending/running/completed/failed/cancelled）
- [ ] 5.3 实现任务文件持久化（logs/mcp_tasks/）
- [ ] 5.4 实现任务过期清理机制（TTL）
- [ ] 5.5 实现 SSE 进度推送端点
- [ ] 5.6 更新 blueprint.py 注册任务端点

### 阶段六：Level 2 Tools (异步模式)

- [ ] 6.1 实现 start_search_full / get_search_full_status / get_search_full_result（mcp/tools/search.py）
- [ ] 6.2 实现 subscribe_search_full SSE 订阅（mcp/tools/search.py）
- [ ] 6.3 实现 start_media_full 系列（mcp/tools/media.py）
- [ ] 6.4 实现 start_sentiment_full 系列（mcp/tools/sentiment.py）
- [ ] 6.5 实现 crawl_data_full（mcp/tools/crawl.py）
- [ ] 6.6 注册 Level 2 工具到 blueprint.py
- [ ] 6.7 添加 Level 2 相关 Resources

### 阶段七：Level 3 Tools (异步模式)

- [ ] 7.1 创建 mcp/tools/forum.py
- [ ] 7.2 实现 start_forum_research / get_forum_progress / get_forum_result
- [ ] 7.3 实现 subscribe_forum SSE 订阅
- [ ] 7.4 实现 stop_forum_research
- [ ] 7.5 实现 get_forum_discussion
- [ ] 7.6 扩展 start_report / get_report_status / get_report_result
- [ ] 7.7 注册 Level 3 工具到 blueprint.py
- [ ] 7.8 添加 Level 3 相关 Resources 和 Prompts

### 阶段八：测试与验证

- [ ] 8.1 Level 1 工具测试
- [ ] 8.2 Level 2 工具测试（异步模式）
- [ ] 8.3 Level 3 工具测试（异步模式）
- [ ] 8.4 SSE 实时推送测试
- [ ] 8.5 任务持久化测试
- [ ] 8.6 任务过期清理测试
- [ ] 8.7 并发控制测试
- [ ] 8.8 创建独立运行入口（mcp_server.py）
- [ ] 8.9 远程访问测试

---

## 十二、侵入性分析

| 现有文件 | 侵入程度 | 说明 |
|---------|---------|------|
| `app.py` | **零侵入** | 只添加 1 行 `register_blueprint` |
| `config.py` | **零侵入** | 不修改 |
| `QueryEngine/*` | **零侵入** | 不修改 |
| `MediaEngine/*` | **零侵入** | 不修改 |
| `InsightEngine/*` | **零侵入** | 不修改 |
| `ReportEngine/*` | **零侵入** | 不修改 |
| `ForumEngine/*` | **零侵入** | 不修改 |
| `MindSpider/*` | **零侵入** | 不修改 |

---

## 十三、优势总结

1. **三层递进** - 从快速查询到深度分析，满足不同场景需求
2. **异步任务** - 长时任务不阻塞，支持实时进度推送
3. **混合模式** - 支持轮询和 SSE 两种获取进度方式
4. **零破坏** - 不修改任何现有 Agent 逻辑
5. **复用基础设施** - SSE、线程、配置、日志全部复用
6. **ForumEngine 协作** - 完整模拟主应用的多Agent协作流程
7. **统一进程** - MCP 和 Flask 共用进程，管理简单
8. **远程访问** - HTTP/SSE 原生支持远程调用
9. **灵活部署** - 可嵌入 Flask 或独立运行

---

## 十四、注意事项

1. **异步处理** - Level 2/3 工具调用需要使用线程池，避免阻塞
2. **超时设置** - 长时间运行的任务需要合理的超时和进度推送
3. **资源清理** - 注意线程和临时文件的清理
4. **并发控制** - 需要考虑多客户端并发调用的情况
5. **LLM 依赖** - Level 3 需要配置 FORUM_HOST_* 环境变量
6. **任务持久化** - 确保 logs/mcp_tasks/ 目录存在且可写

---

## 十五、参考资源

- 项目现有实现：`ReportEngine/flask_interface.py`
- ForumEngine 实现：`ForumEngine/monitor.py`, `ForumEngine/llm_host.py`
- 工具使用：`utils/forum_reader.py`
- DeepSearchAgent 实现：`QueryEngine/agent.py`, `MediaEngine/agent.py`, `InsightEngine/agent.py`
