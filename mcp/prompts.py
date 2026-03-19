"""
MCP Prompts Module

Provides pre-defined prompt templates for common tasks.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import threading


class MCPPrompt:
    """Represents an MCP prompt template."""

    def __init__(
        self,
        name: str,
        description: str,
        arguments: List[Dict[str, Any]],
        template: str,
    ):
        self.name = name
        self.description = description
        self.arguments = arguments
        self.template = template

    def render(self, **kwargs) -> str:
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            return f"Error: Missing required argument: {e}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "arguments": self.arguments,
        }


class PromptRegistry:
    """Registry for MCP prompts."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._prompts: Dict[str, MCPPrompt] = {}
        self._initialized = True
        self._register_default_prompts()

    def _register_default_prompts(self):
        self.register(
            MCPPrompt(
                name="comprehensive_analysis",
                description="综合舆情分析 - 搜索、情感分析并生成报告",
                arguments=[
                    {"name": "topic", "description": "分析主题", "required": True},
                    {
                        "name": "time_range",
                        "description": "时间范围 (如: 24h, 1week, 1month)",
                        "required": False,
                    },
                ],
                template="""请对"{topic}"进行全面舆情分析：

1. 首先使用 search_news 工具搜索相关舆情信息
2. 使用 query_sentiment 工具分析情感倾向
3. 使用 query_trending 工具查询热门内容
4. 最后使用 generate_report 生成综合报告

时间范围: {time_range if time_range else '默认最近一周'}
""",
            )
        )

        self.register(
            MCPPrompt(
                name="brand_reputation_check",
                description="品牌声誉检查 - 检查特定品牌的多平台舆情",
                arguments=[
                    {"name": "brand_name", "description": "品牌名称", "required": True},
                    {
                        "name": "platforms",
                        "description": "平台列表 (逗号分隔)",
                        "required": False,
                    },
                ],
                template="""请对品牌 "{brand_name}" 进行声誉检查：

1. 在以下平台搜索相关讨论：
   - 微博、抖音、小红书、知乎、贴吧
   {platforms if platforms else '(使用所有支持平台)'}

2. 使用 query_sentiment 工具分析情感

3. 重点关注：
   - 正面评价和负面评价的比例
   - 主要投诉或赞誉点
   - 热度趋势变化

4. 生成品牌声誉分析报告
""",
            )
        )

        self.register(
            MCPPrompt(
                name="crisis_detection",
                description="危机检测 - 监控潜在危机事件",
                arguments=[
                    {
                        "name": "keywords",
                        "description": "监控关键词列表",
                        "required": True,
                    },
                    {
                        "name": "sensitivity",
                        "description": "敏感度阈值 (high/medium/low)",
                        "required": False,
                    },
                ],
                template="""执行危机检测监控：

监控关键词: {keywords}

1. 使用 search_news_deep 进行深度搜索
2. 使用 query_sentiment 分析情感变化
3. 关注负面情感的突然增加

敏感度: {sensitivity if sensitivity else 'medium'}

如发现异常立即告警。
""",
            )
        )

        self.register(
            MCPPrompt(
                name="media_content_analysis",
                description="媒体内容分析 - 分析视频/图片的传播情况",
                arguments=[
                    {
                        "name": "media_query",
                        "description": "媒体内容描述或关键词",
                        "required": True,
                    },
                    {
                        "name": "analysis_type",
                        "description": "分析类型 (comprehensive/web_only/structured)",
                        "required": False,
                    },
                ],
                template="""分析媒体内容传播：

查询: {media_query}

1. 使用 analyze_media 工具进行全面分析
   类型: {analysis_type if analysis_type else 'comprehensive'}

2. 分析要点：
   - 播放量和互动数据
   - 评论情感分布
   - 传播路径和来源
""",
            )
        )

        self.register(
            MCPPrompt(
                name="competitor_comparison",
                description="竞品对比分析 - 对比多个品牌的舆情表现",
                arguments=[
                    {
                        "name": "competitors",
                        "description": "竞品列表 (逗号分隔)",
                        "required": True,
                    },
                    {
                        "name": "metric",
                        "description": "对比维度 (sentiment/volume/trend)",
                        "required": False,
                    },
                ],
                template="""竞品舆情对比分析：

竞品: {competitors}

1. 分别搜索各竞品的舆情数据
2. 使用 query_sentiment 分析各品牌情感
3. 使用 query_trending 对比热度

对比维度: {metric if metric else '综合对比'}

生成对比报告，展示各品牌的优劣势。
""",
            )
        )

        self.register(
            MCPPrompt(
                name="social_media_crawl",
                description="社交媒体数据采集 - 采集特定话题的社交数据",
                arguments=[
                    {"name": "topic", "description": "采集主题", "required": True},
                    {"name": "platforms", "description": "目标平台", "required": False},
                    {
                        "name": "volume",
                        "description": "采集数量级别 (small/medium/large)",
                        "required": False,
                    },
                ],
                template="""采集社交媒体数据：

主题: {topic}
平台: {platforms if platforms else '所有支持平台'}
数量: {volume if volume else 'medium'}

1. 使用 crawl_data 工具启动数据采集
2. 使用 crawl_topics 提取热点话题
3. 采集完成后进行情感分析
""",
            )
        )

        self.register(
            MCPPrompt(
                name="trend_report",
                description="趋势报告生成 - 生成话题趋势分析报告",
                arguments=[
                    {
                        "name": "trend_topic",
                        "description": "趋势主题",
                        "required": True,
                    },
                    {
                        "name": "period",
                        "description": "分析周期 (day/week/month)",
                        "required": False,
                    },
                ],
                template="""生成趋势分析报告：

主题: {trend_topic}
周期: {period if period else 'week'}

1. 搜索近期相关趋势数据
2. 分析情感变化趋势
3. 识别关键传播节点
4. 预测后续发展

生成包含趋势图表的完整报告。
""",
            )
        )

        self.register(
            MCPPrompt(
                name="daily_briefing",
                description="每日舆情简报 - 生成每日舆情摘要",
                arguments=[
                    {
                        "name": "date",
                        "description": "简报日期 (YYYY-MM-DD, 默认今天)",
                        "required": False,
                    },
                    {
                        "name": "focus_areas",
                        "description": "重点关注领域",
                        "required": False,
                    },
                ],
                template="""生成每日舆情简报：

日期: {date if date else '今天'}
关注领域: {focus_areas if focus_areas else '全部'}

1. 搜索过去24小时的重要舆情
2. 汇总各平台热点话题
3. 情感分布统计
4. 重点事件摘要

生成结构化的每日简报。
""",
            )
        )

        self.register(
            MCPPrompt(
                name="async_task_usage",
                description="异步任务使用指南 - 如何使用Level 2/3异步工具",
                arguments=[
                    {
                        "name": "tool_type",
                        "description": "工具类型 (search_full/media_full/sentiment_full/crawl_data/crawl_topics/crawl_social)",
                        "required": False,
                    },
                    {
                        "name": "mode",
                        "description": "获取进度模式 (poll/sse)",
                        "required": False,
                    },
                ],
                template="""异步任务使用指南：

## 异步工具调用流程

### 轮询模式 (Poll)
1. 使用 start_* 工具提交任务，获得 task_id
   - 返回: {{"success": true, "task_id": "xxx", "status": "pending"}}
2. 使用 get_*_status 查询进度
   - 返回: {{"progress": 45, "stage": "reflection_loop", "status": "running"}}
3. 当 status 变为 "completed" 时，使用 get_*_result 获取结果
   - 返回: {{"status": "completed", "result": {{...}}}}

### SSE 模式 (实时推送)
1. 使用 start_* 工具提交任务
2. 使用 subscribe_* 工具获取 SSE 流 URL
3. 接收实时进度推送事件
4. 事件类型: progress / completed / failed / cancelled

### 取消任务
- 使用 cancel_* 工具可随时取消运行中的任务

工具类型: {tool_type if tool_type else '所有异步工具'}
获取模式: {mode if mode else '轮询'}
""",
            )
        )

        self.register(
            MCPPrompt(
                name="forum_research",
                description="启动Forum多Agent协作研究",
                arguments=[
                    {"name": "topic", "description": "研究主题", "required": True},
                    {
                        "name": "engines",
                        "description": "启用的引擎 (query/media/insight, 默认全部)",
                        "required": False,
                    },
                    {
                        "name": "max_reflections",
                        "description": "最大反思轮数 (默认3)",
                        "required": False,
                    },
                ],
                template="""启动ForumEngine多Agent协作研究：

研究主题: {topic}
启用引擎: {engines if engines else 'query, media, insight'}
反思轮数: {max_reflections if max_reflections else 3}

## 研究流程

1. 使用 start_forum_research 提交任务
   - 三个Agent (Query/Media/Insight) 将并行开始工作
   - ForumEngine主持人将协调多轮讨论

2. 使用 get_forum_progress 监控研究进度
   - 查看各引擎的研究状态
   - 了解论坛发言数量

3. 使用 get_forum_discussion 获取讨论内容
   - 查看QUERY/MEDIA/INSIGHT/HOST各方的发言
   - 理解各Agent的研究发现

4. 使用 subscribe_forum 订阅实时进度 (SSE模式)

5. 研究完成后使用 get_forum_result 获取综合报告

## 注意事项
- 完整研究可能需要10-30分钟
- 可随时使用 stop_forum_research 停止研究
""",
            )
        )

        self.register(
            MCPPrompt(
                name="forum_guidance",
                description="论坛主持人引导生成提示 - ForumHost生成战略引导的提示词",
                arguments=[
                    {"name": "topic", "description": "研究主题", "required": True},
                    {
                        "name": "recent_speeches",
                        "description": "最近的Agent发言内容",
                        "required": True,
                    },
                    {
                        "name": "research_phase",
                        "description": "当前研究阶段",
                        "required": False,
                    },
                ],
                template="""作为论坛主持人，请分析以下Agent发言并生成战略引导：

研究主题: {topic}
当前阶段: {research_phase if research_phase else '多轮反思循环中'}

## Agent发言摘要:
{recent_speeches}

## 引导生成要求

1. 分析各Agent的研究发现：
   - 识别共同关注点
   - 发现研究空白
   - 指出矛盾或分歧

2. 生成战略引导：
   - 指出下一步研究方向
   - 提出需要深化的具体问题
   - 建议Agent之间的协作角度

3. 引导风格：
   - 简洁明了，不超过200字
   - 聚焦战略层面，不涉及具体操作
   - 鼓励多元视角和深入分析

请生成下一轮的战略引导发言。
""",
            )
        )

        self.register(
            MCPPrompt(
                name="multi_agent_synthesis",
                description="多Agent结果综合分析 - 综合三个Agent的研究结果",
                arguments=[
                    {"name": "topic", "description": "研究主题", "required": True},
                    {
                        "name": "query_results",
                        "description": "QueryEngine研究结果",
                        "required": False,
                    },
                    {
                        "name": "media_results",
                        "description": "MediaEngine研究结果",
                        "required": False,
                    },
                    {
                        "name": "insight_results",
                        "description": "InsightEngine研究结果",
                        "required": False,
                    },
                ],
                template="""综合分析多Agent研究结果：

研究主题: {topic}

## QueryEngine发现:
{query_results if query_results else '等待QueryEngine研究结果...'}

## MediaEngine发现:
{media_results if media_results else '等待MediaEngine研究结果...'}

## InsightEngine发现:
{insight_results if insight_results else '等待InsightEngine研究结果...'}

## 综合分析任务

1. 交叉验证：
   - 识别三个引擎发现中的共同趋势
   - 对比不同数据源的一致性
   - 发现被单一引擎忽视的重要信息

2. 补充分析：
   - 识别各引擎的独特贡献
   - 补充信息空白
   - 构建完整的舆情画像

3. 洞察提炼：
   - 提取关键发现和洞察
   - 识别风险和机会
   - 提出建议和行动项

4. 生成综合报告供ReportEngine使用
""",
            )
        )

        self.register(
            MCPPrompt(
                name="final_report_generation",
                description="最终报告生成提示 - 指导生成最终综合报告",
                arguments=[
                    {"name": "topic", "description": "报告主题", "required": True},
                    {
                        "name": "template",
                        "description": "报告模板 (standard/crisis/hot_topic/competitor/platform)",
                        "required": False,
                    },
                    {
                        "name": "synthesis",
                        "description": "多Agent综合分析结果",
                        "required": False,
                    },
                    {
                        "name": "format",
                        "description": "输出格式 (html/json/pdf)",
                        "required": False,
                    },
                ],
                template="""生成最终综合报告：

报告主题: {topic}
报告模板: {template if template else 'standard'}
输出格式: {format if format else 'html'}

## 综合分析结果:
{synthesis if synthesis else '等待多Agent综合分析完成...'}

## 报告生成流程

1. 数据收集：
   - 汇总QueryEngine新闻搜索结果
   - 汇总MediaEngine多模态分析结果
   - 汇总InsightEngine舆情情感结果
   - 整合ForumEngine论坛讨论洞察

2. 报告结构：
   - 执行摘要 (关键发现)
   - 舆情概况 (数据概览)
   - 深度分析 (各维度分析)
   - 趋势预测 (未来展望)
   - 建议行动 (下一步)

3. 质量检测：
   - 检查数据完整性和准确性
   - 确保分析逻辑连贯
   - 验证结论有数据支撑

4. 渲染输出：
   - 使用选定模板渲染报告
   - 生成交互式HTML报告
   - 保存到指定目录

使用 start_report 工具启动报告生成流程。
""",
            )
        )

    def register(self, prompt: MCPPrompt):
        self._prompts[prompt.name] = prompt

    def unregister(self, name: str) -> bool:
        return self._prompts.pop(name, None) is not None

    def get(self, name: str) -> Optional[MCPPrompt]:
        return self._prompts.get(name)

    def get_all(self) -> Dict[str, MCPPrompt]:
        return self._prompts.copy()

    def list_prompts(self) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in self._prompts.values()]

    def render_prompt(self, name: str, **kwargs) -> Optional[str]:
        prompt = self._prompts.get(name)
        if prompt:
            return prompt.render(**kwargs)
        return None


_prompt_registry = PromptRegistry()


def get_prompt_registry() -> PromptRegistry:
    return _prompt_registry


def list_mcp_prompts() -> List[Dict[str, Any]]:
    return _prompt_registry.list_prompts()


def get_mcp_prompt(name: str) -> Optional[Dict[str, Any]]:
    prompt = _prompt_registry.get(name)
    if prompt:
        return prompt.to_dict()
    return None


def render_mcp_prompt(name: str, **kwargs) -> Optional[str]:
    return _prompt_registry.render_prompt(name, **kwargs)
