# BettaFish MCP 改造任务清单

根据设计文档 MCP_TRANSFORM_GUIDE.md 和 TODO.md 的任务列表，逐个任务完成，不要同时做多个任务。在开始每个任务前要做计划，然后依照计划好的方案来执行。完成任务后更新 TODO.md 将任务设置为完成，[ ] 代表未完成，[x] 代表完成任务。完成任务要"git commit"将开发和修改的内容提交到仓库。如果上下文很长超过 35%，那么要压缩会话和上下文，命令是`/compact`

## MCP 工具三层架构

| 层级 | 描述 | 执行模式 | 工具数量 |
|------|------|---------|---------|
| **Level 1** | 单次搜索查询 (单次工具调用) | 同步 (秒级) | 5个 ✅ 已完成 |
| **Level 2** | 单Agent完整分析流程 + 爬虫异步 | 异步 (分钟级) | 35个 ✅ 已完成 |
| **Level 3** | 多Agent协作+报告生成 (ForumEngine+ReportEngine) | 异步 (十分钟级) | 10个 ✅ 已完成 |

---

## 异步任务架构

### 核心设计

| 配置项 | 值 | 说明 |
|--------|-----|------|
| **模式** | 混合模式 (轮询 + SSE) | 支持轮询和实时推送 |
| **最大并发** | 3 | 每种类型最多同时运行3个任务 |
| **成功TTL** | 1小时 | 成功后保留1小时供查询 |
| **失败TTL** | 24小时 | 失败保留24小时供调试 |
| **持久化** | `logs/mcp_tasks/` | 任务文件和结果存储 |

### 工具操作模式

| 操作 | 方法前缀 | 说明 |
|------|----------|------|
| 提交任务 | `start_*` | 返回 task_id |
| 查询状态 | `get_*_status` | 轮询进度 |
| 获取结果 | `get_*_result` | 获取结果/错误 |
| 订阅进度 | `subscribe_*` | SSE 实时推送 |
| 取消任务 | `cancel_*` | 中止任务 |

---

## 阶段一：基础设施搭建 ✅ 已完成

- [x] 1.1 创建 MCP 模块目录（mcp/__init__.py）
- [x] 1.2 创建 MCP Server（mcp/server.py）
- [x] 1.3 创建 Flask Blueprint（mcp/blueprint.py）

## 阶段二：Level 1 Tools ✅ 已完成

- [x] 2.1 创建 Tools 模块（mcp/tools/__init__.py）
- [x] 2.2 实现搜索工具 `search_news`（mcp/tools/search.py）
- [x] 2.3 实现媒体分析工具 `analyze_media`（mcp/tools/media.py）
- [x] 2.4 实现舆情查询工具 `query_sentiment`（mcp/tools/sentiment.py）
- [x] 2.5 实现报告生成工具 `generate_report`（mcp/tools/report.py）
- [x] 2.6 实现爬虫状态检查 `check_spider_status`（mcp/tools/crawl.py）

## 阶段二续：爬虫工具异步化 ✅ 已完成

- [x] 2.7 实现 `start_crawl_data` 系列（mcp/tools/crawl.py）
- [x] 2.8 实现 `start_crawl_topics` 系列（mcp/tools/crawl.py）
- [x] 2.9 实现 `start_crawl_social` 系列（mcp/tools/crawl.py）
- [x] 2.10 更新 blueprint.py 注册新异步工具

## 阶段三：Resources 和 Prompts ✅ 已完成

- [x] 3.1 实现 Resources（mcp/resources.py）
  - 6个默认资源：server_info, engines_list, platforms, search_types, sentiment_levels, report_templates
- [x] 3.2 实现 Prompts（mcp/prompts.py）
  - 8个提示词模板：comprehensive_analysis, brand_reputation_check, crisis_detection, media_content_analysis, competitor_comparison, social_media_crawl, trend_report, daily_briefing

## 阶段四：集成 ✅ 已完成

- [x] 4.1 注册 MCP Blueprint（app.py - 添加2行）
- [x] 4.2 更新环境变量示例（.env.example - 添加3个MCP配置）

## 阶段五：异步任务基础设施 ✅ 已完成

### 5.1 TaskRegistry 核心类

| 任务 | 文件 | 功能 | 状态 |
|------|------|------|------|
| 5.1.1 | mcp/task_registry.py | 创建 TaskRegistry 类 | ✅ |
| 5.1.2 | mcp/task_registry.py | 实现任务状态管理 | ✅ |
| 5.1.3 | mcp/task_registry.py | 实现文件持久化 | ✅ |
| 5.1.4 | mcp/task_registry.py | 实现 TTL 清理机制 | ✅ |
| 5.1.5 | mcp/task_registry.py | 实现 SSE 事件发布 | ✅ |

### 5.2 TaskRegistry API 设计

```python
class TaskRegistry:
    """异步任务注册中心"""
    
    # 创建任务
    def create_task(self, task_type: str, params: dict) -> str:
        """创建新任务，返回 task_id"""
        
    # 查询任务
    def get_task(self, task_id: str) -> dict:
        """获取任务详情"""
        
    def get_task_status(self, task_id: str) -> dict:
        """获取任务状态和进度"""
        
    def get_task_result(self, task_id: str) -> dict:
        """获取任务结果"""
        
    def list_tasks(self, task_type: str = None, status: str = None) -> list:
        """列出任务"""
        
    # 更新任务
    def update_progress(self, task_id: str, progress: int, stage: str, detail: str = None):
        """更新任务进度"""
        
    def complete_task(self, task_id: str, result: dict):
        """标记任务完成"""
        
    def fail_task(self, task_id: str, error: str):
        """标记任务失败"""
        
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        
    # 清理
    def cleanup_expired(self):
        """清理过期任务"""
```

### 5.3 任务端点

| 端点 | 方法 | 功能 | 状态 |
|------|------|------|------|
| 5.3.1 | GET `/mcp/task/<task_id>/status` | 查询任务状态 | ✅ |
| 5.3.2 | GET `/mcp/task/<task_id>/result` | 获取任务结果 | ✅ |
| 5.3.3 | GET `/mcp/task/<task_id>/stream` | SSE 实时推送 | ✅ |
| 5.3.4 | POST `/mcp/task/<task_id>/cancel` | 取消任务 | ✅ |
| 5.3.5 | GET `/mcp/tasks` | 列出所有任务 | ✅ |

### 5.4 Blueprint 注册

- [x] 5.4.1 注册任务管理端点到 blueprint.py
- [x] 5.4.2 添加任务状态管理变量

---

## 阶段六：Level 2 Tools - 单Agent完整分析流程 + 爬虫异步 (异步模式) ✅ 已完成

### 6.1 QueryEngine 异步工具

| 任务 | 工具名 | 功能 | 状态 |
|------|--------|------|------|
| 6.1.1 | `start_search_full` | 提交 QueryEngine 完整分析任务 | ✅ |
| 6.1.2 | `get_search_full_status` | 查询分析进度 (轮询) | ✅ |
| 6.1.3 | `get_search_full_result` | 获取分析结果 | ✅ |
| 6.1.4 | `subscribe_search_full` | 订阅 SSE 实时进度 | ✅ |
| 6.1.5 | `cancel_search_full` | 取消分析任务 | ✅ |

### 6.2 MediaEngine 异步工具

| 任务 | 工具名 | 功能 | 状态 |
|------|--------|------|------|
| 6.2.1 | `start_media_full` | 提交 MediaEngine 完整分析任务 | ✅ |
| 6.2.2 | `get_media_full_status` | 查询分析进度 | ✅ |
| 6.2.3 | `get_media_full_result` | 获取分析结果 | ✅ |
| 6.2.4 | `subscribe_media_full` | 订阅 SSE 实时进度 | ✅ |
| 6.2.5 | `cancel_media_full` | 取消媒体分析任务 | ✅ |

### 6.3 InsightEngine 异步工具

| 任务 | 工具名 | 功能 | 状态 |
|------|--------|------|------|
| 6.3.1 | `start_sentiment_full` | 提交 InsightEngine 完整分析任务 | ✅ |
| 6.3.2 | `get_sentiment_full_status` | 查询舆情分析进度 | ✅ |
| 6.3.3 | `get_sentiment_full_result` | 获取舆情分析结果 | ✅ |
| 6.3.4 | `subscribe_sentiment_full` | 订阅 SSE 实时进度 | ✅ |
| 6.3.5 | `cancel_sentiment_full` | 取消舆情分析任务 | ✅ |

### 6.4 MindSpider 异步工具 - crawl_data

| 任务 | 工具名 | 功能 | 状态 |
|------|--------|------|------|
| 6.4.1 | `start_crawl_data` | 提交数据爬取任务 | ✅ |
| 6.4.2 | `get_crawl_data_status` | 查询爬取进度 (轮询) | ✅ |
| 6.4.3 | `get_crawl_data_result` | 获取爬取结果 | ✅ |
| 6.4.4 | `subscribe_crawl_data` | 订阅 SSE 实时进度 | ✅ |
| 6.4.5 | `cancel_crawl_data` | 取消爬取任务 | ✅ |

### 6.5 MindSpider 异步工具 - crawl_topics

| 任务 | 工具名 | 功能 | 状态 |
|------|--------|------|------|
| 6.5.1 | `start_crawl_topics` | 提交热点话题提取任务 | ✅ |
| 6.5.2 | `get_crawl_topics_status` | 查询话题提取进度 | ✅ |
| 6.5.3 | `get_crawl_topics_result` | 获取话题提取结果 | ✅ |
| 6.5.4 | `subscribe_crawl_topics` | 订阅 SSE 实时进度 | ✅ |
| 6.5.5 | `cancel_crawl_topics` | 取消话题提取任务 | ✅ |

### 6.6 MindSpider 异步工具 - crawl_social

| 任务 | 工具名 | 功能 | 状态 |
|------|--------|------|------|
| 6.6.1 | `start_crawl_social` | 提交社交媒体爬取任务 | ✅ |
| 6.6.2 | `get_crawl_social_status` | 查询爬取进度 | ✅ |
| 6.6.3 | `get_crawl_social_result` | 获取爬取结果 | ✅ |
| 6.6.4 | `subscribe_crawl_social` | 订阅 SSE 实时进度 | ✅ |
| 6.6.5 | `cancel_crawl_social` | 取消爬取任务 | ✅ |

### 6.7 工具参数设计

```python
# start_search_full / start_media_full / start_sentiment_full 通用参数
{
    "query": "研究主题",                    # 必填
    "max_reflections": 3,                  # 反思轮数 (默认3)
    "save_report": True,                   # 是否保存报告文件
    "output_dir": "xxx_reports",           # 输出目录 (可选)
    "timeout": 600                         # 超时时间(秒)
}

# start_crawl_data 参数
{
    "keywords": ["关键词1", "关键词2"],     # 必填
    "platforms": ["xhs", "dy", "wb"],      # 平台列表
    "max_keywords": 50,
    "max_notes": 50,
    "test_mode": False,
    "timeout": 3600
}

# start_crawl_topics 参数
{
    "keywords_count": 100,                 # 关键词数量
    "extract_date": "2026-03-19",          # 提取日期
    "timeout": 600
}

# start_crawl_social 参数
{
    "platforms": ["xhs", "dy", "wb"],      # 平台列表
    "max_keywords": 30,
    "max_notes": 20,
    "target_date": "2026-03-19",
    "test_mode": False,
    "timeout": 3600
}
```

### 6.8 返回值设计

```json
// start_* 返回
{
    "success": true,
    "task_id": "search_full_xxx",
    "status": "pending",
    "message": "分析任务已提交，请使用 get_search_full_status 查询进度"
}

// get_*_status 返回
{
    "success": true,
    "task_id": "search_full_xxx",
    "status": "running",
    "progress": 45,
    "stage": "reflection_loop",
    "stage_detail": "正在处理段落 3/6",
    "started_at": "2026-03-18T10:00:00Z",
    "message": "分析进行中"
}

// get_*_result 返回
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
    "completed_at": "2026-03-18T10:03:00Z",
    "message": "分析完成"
}
```

### 6.9 Blueprint 注册

- [x] 6.9.1 在 `_get_tool_descriptions()` 添加 Level 2 工具描述
- [x] 6.9.2 在 `tool_map` 中注册 Level 2 工具
- [x] 6.9.3 在 `mcp/tools/__init__.py` 导出新工具

### 6.10 Resources 扩展

- [ ] 6.10.1 添加 `bettafish://tasks/status` - 当前任务状态
- [ ] 6.10.2 添加 `bettafish://tasks/list` - 任务列表

---

## 阶段七：Level 3 Tools - 多Agent协作+报告生成 (异步模式) ✅ 已完成

### 7.1 ForumEngine 协作工具

| 任务 | 工具名 | 功能 | 状态 |
|------|--------|------|------|
| 7.1.1 | `start_forum_research` | 启动ForumEngine + 3个Agent并行研究 | ✅ |
| 7.1.2 | `get_forum_progress` | 查询论坛研究进度 (轮询) | ✅ |
| 7.1.3 | `get_forum_result` | 获取论坛研究结果 | ✅ |
| 7.1.4 | `subscribe_forum` | 订阅论坛 SSE 实时进度 | ✅ |
| 7.1.5 | `stop_forum_research` | 停止论坛研究 | ✅ |
| 7.1.6 | `get_forum_discussion` | 获取论坛讨论内容 | ✅ |

### 7.2 ReportEngine 异步工具

| 任务 | 工具名 | 功能 | 状态 |
|------|--------|------|------|
| 7.2.1 | `start_report` | 启动最终报告生成 | ✅ |
| 7.2.2 | `get_report_status` | 查询报告生成进度 | ✅ |
| 7.2.3 | `get_report_result` | 获取报告结果 | ✅ |
| 7.2.4 | `subscribe_report` | 订阅报告 SSE 实时进度 | ✅ |

### 7.3 工具参数设计

```python
# start_forum_research 参数
{
    "topic": "研究主题",                              # 必填
    "engines": ["query", "media", "insight"],        # 启用的引擎
    "timeout": 1800                                   # 30分钟超时
}

# start_report 参数
{
    "topic": "报告主题",                              # 必填
    "template": "企业品牌声誉分析报告",               # 可选模板
    "timeout": 600                                    # 10分钟超时
}
```

### 7.4 返回值设计

```json
// start_forum_research 返回
{
    "success": true,
    "task_id": "forum_20260318_xxx",
    "status": "pending",
    "message": "ForumEngine研究任务已提交"
}

// get_forum_progress 返回
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
    "started_at": "2026-03-18T10:00:00Z"
}

// get_forum_result 返回
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
    "execution_time_seconds": 600,
    "completed_at": "2026-03-18T10:10:00Z",
    "message": "ForumEngine研究完成"
}
```

### 7.5 Blueprint 注册

- [x] 7.5.1 在 `_get_tool_descriptions()` 添加 Level 3 工具描述
- [x] 7.5.2 在 `tool_map` 中注册 Level 3 工具

### 7.6 Resources 扩展

- [x] 7.6.1 添加 `bettafish://forum/engines` - ForumEngine引擎状态
- [x] 7.6.2 添加 `bettafish://forum/roles` - 各Agent角色说明
- [x] 7.6.3 添加 `bettafish://forum/workflow` - 协作工作流程

### 7.7 Prompts 扩展

- [x] 7.7.1 添加 `async_task_usage` - 异步任务使用指南
- [x] 7.7.2 添加 `forum_research` - 启动Forum多Agent协作研究
- [x] 7.7.3 添加 `forum_guidance` - 论坛主持人引导生成提示
- [x] 7.7.4 添加 `multi_agent_synthesis` - 多Agent结果综合分析
- [x] 7.7.5 添加 `final_report_generation` - 最终报告生成提示

---

## 阶段八：测试与验证 🔄 待实现

### 8.1 Level 1 工具测试

- [ ] 8.1.1 测试 `search_news`
- [ ] 8.1.2 测试 `analyze_media`
- [ ] 8.1.3 测试 `query_sentiment`
- [ ] 8.1.4 测试 `check_spider_status`

### 8.2 Level 2 工具测试 (异步模式)

- [ ] 8.2.1 测试 `start_search_full` / `get_search_full_status` / `get_search_full_result`
- [ ] 8.2.2 测试 `subscribe_search_full` SSE 订阅
- [ ] 8.2.3 测试 `start_media_full` 系列
- [ ] 8.2.4 测试 `start_sentiment_full` 系列
- [ ] 8.2.5 测试 `start_crawl_data` 系列
- [ ] 8.2.6 测试 `start_crawl_topics` 系列
- [ ] 8.2.7 测试 `start_crawl_social` 系列
- [ ] 8.2.8 测试超时处理
- [ ] 8.2.9 测试任务取消
- [ ] 8.2.10 测试报告保存功能

### 8.3 Level 3 工具测试 (异步模式)

- [ ] 8.3.1 测试 `start_forum_research` / `get_forum_progress` / `get_forum_result`
- [ ] 8.3.2 测试 `subscribe_forum` SSE 订阅
- [ ] 8.3.3 测试 `stop_forum_research`
- [ ] 8.3.4 测试 `get_forum_discussion`
- [ ] 8.3.5 测试 `start_report` / `get_report_status` / `get_report_result`
- [ ] 8.3.6 测试完整协作流程
- [ ] 8.3.7 测试并发运行多个引擎

### 8.4 异步任务基础设施测试

- [ ] 8.4.1 测试任务持久化（重启后任务不丢失）
- [ ] 8.4.2 测试任务过期清理（TTL）
- [ ] 8.4.3 测试并发控制（超过3个任务被拒绝）
- [ ] 8.4.4 测试 SSE 心跳机制

### 8.5 独立服务测试

- [ ] 8.5.1 创建独立运行入口（mcp_server.py）
- [ ] 8.5.2 测试独立模式运行
- [ ] 8.5.3 测试远程访问

---

## 任务依赖关系

```
阶段五 (异步任务基础设施)
    │
    ├── 5.1.1-5.1.5 TaskRegistry 核心类
    │
    ├── 5.3.1-5.3.5 任务端点
    │
    └── 5.4.1-5.4.2 Blueprint 注册
            │
            ▼
阶段六 (Level 2 Tools)
    │
    ├── 6.1.1-6.1.5 QueryEngine 异步工具
    ├── 6.2.1-6.2.5 MediaEngine 异步工具
    ├── 6.3.1-6.3.5 InsightEngine 异步工具
    ├── 6.4.1-6.4.5 MindSpider crawl_data 异步工具
    ├── 6.5.1-6.5.5 MindSpider crawl_topics 异步工具
    ├── 6.6.1-6.6.5 MindSpider crawl_social 异步工具
    │
    └── 6.9.1-6.9.3 Blueprint + __init__ 注册
            │
            ▼
阶段七 (Level 3 Tools)
    │
    ├── 7.1.1-7.1.6 ForumEngine 协作工具
    ├── 7.2.1-7.2.4 ReportEngine 异步工具
    │
    └── 7.5.1-7.5.2 Blueprint 注册
    └── 7.6.1-7.6.3, 7.7.1-7.7.5 Resources/Prompts
            │
            ▼
阶段八 (测试)
    │
    ├── 8.1 Level 1 测试
    ├── 8.2 Level 2 测试
    ├── 8.3 Level 3 测试
    ├── 8.4 异步任务基础设施测试
    └── 8.5 独立服务测试
```

---

## 进度统计

| 阶段 | 总任务数 | 已完成 | 待实现 |
|------|---------|-------|-------|
| 一：基础设施 | 3 | 3 | 0 |
| 二：Level 1 Tools | 6 | 6 | 0 |
| 二续：爬虫异步化 | 4 | 4 | 0 |
| 三：Resources/Prompts | 2 | 2 | 0 |
| 四：集成 | 2 | 2 | 0 |
| 五：异步任务基础设施 | 10 | 10 | 0 |
| 六：Level 2 Tools | 37 | 37 | 0 |
| 七：Level 3 Tools | 15 | 10 | 5 |
| 八：测试 | 19 | 0 | 19 |
| **总计** | **98** | **74** | **24** |

---

## 新增文件清单

```
mcp/
├── task_registry.py      # 异步任务注册中心 (NEW)
└── tools/
    ├── search.py         # Level 1: search_news
    │                     # Level 2: start_search_full + 4个异步操作
    ├── media.py          # Level 1: analyze_media
    │                     # Level 2: start_media_full + 4个异步操作
    ├── sentiment.py      # Level 1: query_sentiment, analyze_sentiment_texts, query_trending
    │                     # Level 2: start_sentiment_full + 4个异步操作
    ├── report.py         # Level 1: generate_report
    ├── crawl.py          # Level 1: check_spider_status
    │                     # Level 2: start_crawl_data + 4个异步操作
    │                     # Level 2: start_crawl_topics + 4个异步操作
    │                     # Level 2: start_crawl_social + 4个异步操作
    └── forum.py          # Level 3: ForumEngine协作 + ReportEngine异步

logs/
└── mcp_tasks/           # 任务持久化目录 (NEW)
    ├── tasks.json
    └── results/
```

---

## 相关文档

- [MCP_TRANSFORM_GUIDE.md](./MCP_TRANSFORM_GUIDE.md) - 详细设计文档
- [MCP 模块目录](./mcp/) - MCP 实现代码
- [原项目 README](./README.md) - BettaFish 项目说明
