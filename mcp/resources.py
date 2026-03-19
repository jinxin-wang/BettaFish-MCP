"""
MCP Resources Module

Provides static and dynamic resources for MCP clients.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import threading


class MCPResource:
    """Represents an MCP resource."""

    def __init__(
        self,
        uri: str,
        name: str,
        description: str,
        mime_type: str = "application/json",
        content_provider: Optional[callable] = None,
    ):
        self.uri = uri
        self.name = name
        self.description = description
        self.mime_type = mime_type
        self.content_provider = content_provider

    def get_content(self) -> Any:
        if self.content_provider:
            return self.content_provider()
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type,
        }


class ResourceRegistry:
    """Registry for MCP resources."""

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
        self._resources: Dict[str, MCPResource] = {}
        self._initialized = True
        self._register_default_resources()

    def _register_default_resources(self):
        self.register(
            uri="bettafish://server/info",
            name="server_info",
            description="MCP服务器信息",
            content_provider=self._get_server_info,
        )
        self.register(
            uri="bettafish://engines/list",
            name="engines_list",
            description="可用分析引擎列表",
            content_provider=self._get_engines_list,
        )
        self.register(
            uri="bettafish://platforms/supported",
            name="platforms",
            description="支持的社交媒体平台",
            content_provider=self._get_platforms,
        )
        self.register(
            uri="bettafish://search/types",
            name="search_types",
            description="搜索类型说明",
            content_provider=self._get_search_types,
        )
        self.register(
            uri="bettafish://sentiment/levels",
            name="sentiment_levels",
            description="情感分析级别说明",
            content_provider=self._get_sentiment_levels,
        )
        self.register(
            uri="bettafish://report/templates",
            name="report_templates",
            description="可用的报告模板",
            content_provider=self._get_report_templates,
        )
        self.register(
            uri="bettafish://forum/engines",
            name="forum_engines",
            description="ForumEngine引擎状态",
            content_provider=self._get_forum_engines,
        )
        self.register(
            uri="bettafish://forum/roles",
            name="forum_roles",
            description="各Agent角色说明",
            content_provider=self._get_forum_roles,
        )
        self.register(
            uri="bettafish://forum/workflow",
            name="forum_workflow",
            description="协作工作流程",
            content_provider=self._get_forum_workflow,
        )

    def _get_server_info(self) -> Dict[str, Any]:
        return {
            "name": "BettaFish-MCP",
            "version": "1.0.0",
            "description": "微舆 (BettaFish) MCP服务",
            "transport": "HTTP/SSE",
            "endpoints": {
                "sse": "/mcp/sse",
                "message": "/mcp/message",
                "status": "/mcp/status",
                "tools": "/mcp/tools",
            },
            "capabilities": {
                "tools": True,
                "resources": True,
                "prompts": True,
            },
        }

    def _get_engines_list(self) -> Dict[str, Any]:
        return {
            "engines": [
                {
                    "name": "QueryEngine",
                    "description": "新闻舆情搜索",
                    "capabilities": ["search_news", "search_news_deep"],
                },
                {
                    "name": "MediaEngine",
                    "description": "多模态内容分析",
                    "capabilities": ["analyze_media", "analyze_video", "analyze_image"],
                },
                {
                    "name": "InsightEngine",
                    "description": "舆情情感分析",
                    "capabilities": [
                        "query_sentiment",
                        "analyze_sentiment_texts",
                        "query_trending",
                    ],
                },
                {
                    "name": "ReportEngine",
                    "description": "报告生成",
                    "capabilities": [
                        "generate_report",
                        "get_report_status",
                        "get_report_result",
                    ],
                },
                {
                    "name": "MindSpider",
                    "description": "社交媒体爬虫",
                    "capabilities": [
                        "crawl_data",
                        "crawl_topics",
                        "crawl_social",
                        "check_spider_status",
                    ],
                },
            ]
        }

    def _get_platforms(self) -> Dict[str, Any]:
        return {
            "platforms": [
                {"id": "weibo", "name": "微博", "type": "social"},
                {"id": "douyin", "name": "抖音", "type": "short_video"},
                {"id": "bilibili", "name": "哔哩哔哩", "type": "video"},
                {"id": "xhs", "name": "小红书", "type": "lifestyle"},
                {"id": "kuaishou", "name": "快手", "type": "short_video"},
                {"id": "zhihu", "name": "知乎", "type": "q&a"},
                {"id": "tieba", "name": "百度贴吧", "type": "forum"},
            ],
            "crawler_platforms": ["xhs", "dy", "ks", "bili", "wb", "tieba", "zhihu"],
            "sentiment_platforms": [
                "bilibili",
                "weibo",
                "douyin",
                "kuaishou",
                "xhs",
                "zhihu",
                "tieba",
            ],
        }

    def _get_search_types(self) -> Dict[str, Any]:
        return {
            "search_types": [
                {"id": "basic", "name": "基础搜索", "description": "常规新闻搜索"},
                {"id": "deep", "name": "深度搜索", "description": "深入分析相关报道"},
                {
                    "id": "last_24h",
                    "name": "24小时搜索",
                    "description": "过去24小时内的新闻",
                },
                {"id": "last_week", "name": "周搜索", "description": "过去一周的新闻"},
                {
                    "id": "by_date",
                    "name": "日期范围搜索",
                    "description": "指定日期范围的新闻",
                },
            ]
        }

    def _get_sentiment_levels(self) -> Dict[str, Any]:
        return {
            "sentiment_levels": [
                {
                    "level": 1,
                    "name": "very_negative",
                    "chinese": "非常负面",
                    "score_range": "0.0-0.2",
                },
                {
                    "level": 2,
                    "name": "negative",
                    "chinese": "负面",
                    "score_range": "0.2-0.4",
                },
                {
                    "level": 3,
                    "name": "neutral",
                    "chinese": "中性",
                    "score_range": "0.4-0.6",
                },
                {
                    "level": 4,
                    "name": "positive",
                    "chinese": "正面",
                    "score_range": "0.6-0.8",
                },
                {
                    "level": 5,
                    "name": "very_positive",
                    "chinese": "非常正面",
                    "score_range": "0.8-1.0",
                },
            ],
            "supported_languages": [
                "zh",
                "en",
                "ja",
                "ko",
                "es",
                "fr",
                "de",
                "pt",
                "ru",
                "ar",
                "hi",
                "th",
                "vi",
                "id",
                "ms",
                "tl",
                "bn",
                "mr",
                "ne",
                "si",
                "km",
                "my",
            ],
        }

    def _get_report_templates(self) -> Dict[str, Any]:
        return {
            "templates": [
                {
                    "id": "standard",
                    "name": "标准报告",
                    "description": "通用分析报告模板",
                },
                {"id": "crisis", "name": "危机报告", "description": "舆情危机分析模板"},
                {
                    "id": "hot_topic",
                    "name": "热点报告",
                    "description": "热点话题分析模板",
                },
                {
                    "id": "competitor",
                    "name": "竞品报告",
                    "description": "竞品舆情对比模板",
                },
                {"id": "platform", "name": "平台报告", "description": "单平台分析模板"},
            ],
            "formats": ["html", "json", "pdf"],
        }

    def _get_forum_engines(self) -> Dict[str, Any]:
        return {
            "forum_engine": {
                "name": "ForumEngine",
                "description": "多Agent协作论坛引擎",
                "role": "主持人协调者",
                "components": {
                    "log_monitor": {
                        "name": "LogMonitor",
                        "description": "监控三个引擎的日志文件，检测SummaryNode输出",
                        "monitors": ["query.log", "media.log", "insight.log"],
                    },
                    "forum_host": {
                        "name": "ForumHost",
                        "description": "LLM主持人，生成战略引导",
                        "trigger": "每5条Agent发言触发一次",
                    },
                    "forum_reader": {
                        "name": "forum_reader",
                        "description": "Agent读取论坛日志的工具",
                    },
                },
            },
            "participating_engines": [
                {
                    "name": "QueryEngine",
                    "alias": "QUERY",
                    "description": "新闻舆情搜索引擎",
                    "log_file": "query.log",
                    "capabilities": ["search_news", "reflection_loop"],
                },
                {
                    "name": "MediaEngine",
                    "alias": "MEDIA",
                    "description": "多模态内容分析引擎",
                    "log_file": "media.log",
                    "capabilities": ["analyze_media", "reflection_loop"],
                },
                {
                    "name": "InsightEngine",
                    "alias": "INSIGHT",
                    "description": "舆情情感分析引擎",
                    "log_file": "insight.log",
                    "capabilities": ["query_sentiment", "reflection_loop"],
                },
            ],
        }

    def _get_forum_roles(self) -> Dict[str, Any]:
        return {
            "roles": [
                {
                    "role": "HOST",
                    "name": "论坛主持人 (ForumHost)",
                    "model": "Qwen3-235B",
                    "description": "LLM驱动的战略协调者",
                    "responsibilities": [
                        "分析所有Agent发言，识别研究进展",
                        "生成战略引导，指引下一轮研究方向",
                        "推动多轮反思循环直到完成",
                    ],
                    "trigger": "每5条Agent发言触发一次引导生成",
                    "tools": ["forum_reader"],
                },
                {
                    "role": "QUERY",
                    "name": "QueryEngine Agent",
                    "engine": "QueryEngine",
                    "description": "新闻舆情搜索专家",
                    "responsibilities": [
                        "进行国内外新闻广度搜索",
                        "基于主持人引导进行专项搜索",
                        "多轮反思循环深入分析",
                    ],
                    "tools": [
                        "execute_search_tool",
                        "reflection_loop",
                        "forum_reader",
                    ],
                    "reflection_rounds": 3,
                },
                {
                    "role": "MEDIA",
                    "name": "MediaEngine Agent",
                    "engine": "MediaEngine",
                    "description": "多模态内容分析专家",
                    "responsibilities": [
                        "分析图片、视频等多模态内容",
                        "识别媒体传播特征和模式",
                        "基于主持人引导调整研究重点",
                    ],
                    "tools": [
                        "execute_search_tool",
                        "reflection_loop",
                        "forum_reader",
                    ],
                    "reflection_rounds": 3,
                },
                {
                    "role": "INSIGHT",
                    "name": "InsightEngine Agent",
                    "engine": "InsightEngine",
                    "description": "舆情情感分析专家",
                    "responsibilities": [
                        "挖掘私有数据库舆情数据",
                        "分析情感趋势和热点",
                        "基于主持人引导深化分析",
                    ],
                    "tools": [
                        "execute_search_tool",
                        "reflection_loop",
                        "forum_reader",
                    ],
                    "reflection_rounds": 3,
                },
            ],
            "collaboration_model": {
                "type": "sequential_collaboration",
                "description": "三个Agent并行研究，定期通过主持人协调",
                "flow": [
                    "1. 初步分析：各Agent使用专属工具进行概览搜索",
                    "2. 策略制定：基于初步结果制定分块研究策略",
                    "3. 论坛协作：ForumEngine监控发言，生成战略引导",
                    "4. 深度研究：各Agent基于主持人引导进行专项搜索",
                    "5. 循环迭代：重复步骤3-4直到所有Agent完成研究",
                ],
            },
        }

    def _get_forum_workflow(self) -> Dict[str, Any]:
        return {
            "workflow": {
                "name": "ForumEngine 多Agent协作流程",
                "description": "完整的多Agent协作舆情分析工作流程",
                "phases": [
                    {
                        "phase": 1,
                        "name": "并行启动",
                        "description": "三个Agent同时开始工作",
                        "agents": ["QUERY", "MEDIA", "INSIGHT"],
                        "action": "各Agent使用专属工具进行概览搜索",
                    },
                    {
                        "phase": 2,
                        "name": "初步分析",
                        "description": "各Agent进行初步分析并输出SummaryNode",
                        "agents": ["QUERY", "MEDIA", "INSIGHT"],
                        "action": "使用execute_search_tool进行单次搜索",
                    },
                    {
                        "phase": 3,
                        "name": "策略制定",
                        "description": "基于初步结果制定分块研究策略",
                        "agents": ["QUERY", "MEDIA", "INSIGHT"],
                        "action": "各Agent内部决策模块制定研究计划",
                    },
                    {
                        "phase": 4,
                        "name": "论坛协作循环",
                        "description": "ForumEngine监控并协调多轮讨论",
                        "loop": True,
                        "iterations": "直到所有Agent完成研究",
                        "steps": [
                            {
                                "step": "4.1",
                                "name": "深度研究",
                                "description": "各Agent基于论坛主持人引导进行专项搜索",
                                "agents": ["QUERY", "MEDIA", "INSIGHT"],
                            },
                            {
                                "step": "4.2",
                                "name": "论坛监控",
                                "description": "LogMonitor监控三个引擎的日志文件",
                                "monitor": "LogMonitor",
                                "detects": "SummaryNode输出",
                            },
                            {
                                "step": "4.3",
                                "name": "论坛发言",
                                "description": "捕获Agent研究总结，写入forum.log",
                                "forum_log": "forum.log",
                            },
                            {
                                "step": "4.4",
                                "name": "主持人引导",
                                "description": "每5条Agent发言触发ForumHost生成战略引导",
                                "trigger": "5条发言",
                                "host": "ForumHost (LLM主持人)",
                            },
                            {
                                "step": "4.5",
                                "name": "交流融合",
                                "description": "各Agent使用forum_reader读取主持人引导",
                                "tool": "forum_reader",
                            },
                        ],
                    },
                    {
                        "phase": 5,
                        "name": "结果整合",
                        "description": "Report Agent收集所有分析结果和论坛内容",
                        "agent": "ReportAgent",
                    },
                    {
                        "phase": 6,
                        "name": "报告生成",
                        "description": "分块进行质量检测，渲染成交互式HTML报告",
                        "agent": "ReportAgent",
                    },
                ],
            },
            "monitoring": {
                "log_files": {
                    "query": "query.log",
                    "media": "media.log",
                    "insight": "insight.log",
                    "forum": "forum.log",
                },
                "detection": "LogMonitor检测SummaryNode输出以触发下一轮",
                "trigger_interval": "每5条Agent发言触发一次主持人引导",
            },
            "async_tools": {
                "start_forum_research": {
                    "description": "启动ForumEngine + 3个Agent并行研究",
                    "parameters": {
                        "topic": "研究主题 (必填)",
                        "engines": "启用的引擎列表 (默认全部)",
                        "timeout": "超时时间 (秒, 默认1800)",
                    },
                },
                "get_forum_progress": {
                    "description": "查询论坛研究进度",
                    "returns": "progress, engines状态, 发言数量",
                },
                "get_forum_discussion": {
                    "description": "获取论坛讨论内容",
                    "parameters": {"task_id": "任务ID", "limit": "返回条数"},
                },
                "stop_forum_research": {"description": "停止论坛研究"},
            },
        }

    def register(
        self,
        uri: str,
        name: str,
        description: str = "",
        mime_type: str = "application/json",
        content_provider: Optional[callable] = None,
    ):
        self._resources[uri] = MCPResource(
            uri=uri,
            name=name,
            description=description,
            mime_type=mime_type,
            content_provider=content_provider,
        )

    def unregister(self, uri: str) -> bool:
        return self._resources.pop(uri, None) is not None

    def get(self, uri: str) -> Optional[MCPResource]:
        return self._resources.get(uri)

    def get_all(self) -> Dict[str, MCPResource]:
        return self._resources.copy()

    def list_resources(self) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self._resources.values()]

    def get_resource_content(self, uri: str) -> Optional[Any]:
        resource = self._resources.get(uri)
        if resource:
            return resource.get_content()
        return None


_resource_registry = ResourceRegistry()


def get_resource_registry() -> ResourceRegistry:
    return _resource_registry


def list_mcp_resources() -> List[Dict[str, Any]]:
    return _resource_registry.list_resources()


def get_mcp_resource(uri: str) -> Optional[Dict[str, Any]]:
    resource = _resource_registry.get(uri)
    if resource:
        result = resource.to_dict()
        content = resource.get_content()
        if content:
            result["content"] = content
        return result
    return None
