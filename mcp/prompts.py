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
