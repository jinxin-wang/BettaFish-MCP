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
