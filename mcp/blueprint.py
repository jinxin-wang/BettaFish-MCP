"""
MCP Flask Blueprint

Provides HTTP/SSE endpoints for MCP protocol communication.
"""

import json
import time
import uuid
from queue import Queue, Empty
from threading import Lock
from collections import defaultdict
from datetime import datetime

from flask import Blueprint, request, jsonify, Response, stream_with_context
from loguru import logger

from .server import MCPServer, format_sse
from .resources import get_resource_registry, list_mcp_resources, get_mcp_resource
from .prompts import (
    get_prompt_registry,
    list_mcp_prompts,
    get_mcp_prompt,
    render_mcp_prompt,
)
from .task_registry import get_task_registry


mcp_bp = Blueprint("mcp", __name__, url_prefix="/mcp")

mcp_server = MCPServer()

STREAM_HEARTBEAT_INTERVAL = 15
STREAM_IDLE_TIMEOUT = 120
STREAM_TERMINAL_STATUSES = {"completed", "error", "cancelled"}

stream_lock = Lock()
stream_subscribers = defaultdict(list)


def _broadcast_event(session_id: str, event: dict):
    with stream_lock:
        listeners = list(stream_subscribers.get(session_id, []))
    for queue in listeners:
        try:
            queue.put(event, timeout=0.1)
        except Exception:
            logger.exception(f"Failed to broadcast event to session {session_id}")


@mcp_bp.route("/sse", methods=["GET"])
def mcp_sse():
    """
    MCP SSE endpoint for client connections.

    Query params:
        session_id: Optional session identifier
    """
    session_id = request.args.get("session_id", str(uuid.uuid4()))

    session = mcp_server.create_session(session_id)

    last_event_id = request.headers.get("Last-Event-ID")
    try:
        last_event_idx = int(last_event_id) if last_event_id else 0
    except ValueError:
        last_event_idx = 0

    def event_generator():
        queue = session.subscribe()
        last_data_ts = time.time()

        yield format_sse(
            {
                "type": "connected",
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "payload": {
                    "session_id": session_id,
                    "message": "MCP connection established",
                },
            }
        )

        while True:
            try:
                event = queue.get(timeout=STREAM_HEARTBEAT_INTERVAL)
                yield format_sse(event)
                last_data_ts = time.time()
            except Empty:
                heartbeat = {
                    "type": "heartbeat",
                    "session_id": session_id,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "payload": {"status": "active"},
                }
                yield format_sse(heartbeat)
                idle_for = time.time() - last_data_ts
                if idle_for > STREAM_IDLE_TIMEOUT:
                    logger.info(f"SSE session {session_id} idle timeout, closing")
                    break

            try:
                if event.get("type") in STREAM_TERMINAL_STATUSES:
                    idle_for = time.time() - last_data_ts
                    if idle_for > STREAM_IDLE_TIMEOUT:
                        break
            except Exception:
                pass

        session.unsubscribe(queue)
        mcp_server.remove_session(session_id)

    response = Response(
        stream_with_context(event_generator()), mimetype="text/event-stream"
    )
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response


@mcp_bp.route("/message", methods=["POST"])
def mcp_message():
    """
    MCP message endpoint for JSON-RPC requests.

    Request body:
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "tool_name",
                "arguments": {}
            }
        }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify(
                {
                    "jsonrpc": "2.0",
                    "error": {"code": -32700, "message": "Parse error"},
                    "id": None,
                }
            ), 400

        jsonrpc_id = data.get("id")
        method = data.get("method", "")
        params = data.get("params", {})

        logger.info(f"MCP request: method={method}, id={jsonrpc_id}")

        if method == "initialize":
            return jsonify(
                {
                    "jsonrpc": "2.0",
                    "id": jsonrpc_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {"listChanged": True},
                            "resources": {"subscribe": True, "listChanged": True},
                            "prompts": {"listChanged": True},
                        },
                        "serverInfo": {"name": "BettaFish-MCP", "version": "1.0.0"},
                    },
                }
            )

        elif method == "tools/list":
            tools = [
                {
                    "name": name,
                    "description": desc.get("description", ""),
                    "inputSchema": {"type": "object", "properties": {}},
                }
                for name, desc in _get_tool_descriptions().items()
            ]
            return jsonify(
                {"jsonrpc": "2.0", "id": jsonrpc_id, "result": {"tools": tools}}
            )

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            result = _execute_tool(tool_name, arguments)

            return jsonify(
                {
                    "jsonrpc": "2.0",
                    "id": jsonrpc_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    result, ensure_ascii=False, indent=2
                                ),
                            }
                        ],
                        "isError": False,
                    },
                }
            )

        elif method == "resources/list":
            return jsonify(
                {
                    "jsonrpc": "2.0",
                    "id": jsonrpc_id,
                    "result": {"resources": list_mcp_resources()},
                }
            )

        elif method == "resources/read":
            uri = params.get("uri", "")
            content = get_mcp_resource(uri)
            if content:
                return jsonify(
                    {
                        "jsonrpc": "2.0",
                        "id": jsonrpc_id,
                        "result": {"contents": [content]},
                    }
                )
            return jsonify(
                {
                    "jsonrpc": "2.0",
                    "id": jsonrpc_id,
                    "error": {"code": -32602, "message": f"Resource not found: {uri}"},
                }
            ), 404

        elif method == "prompts/list":
            return jsonify(
                {
                    "jsonrpc": "2.0",
                    "id": jsonrpc_id,
                    "result": {"prompts": list_mcp_prompts()},
                }
            )

        elif method == "prompts/get":
            name = params.get("name", "")
            arguments = params.get("arguments", {})
            rendered = render_mcp_prompt(name, **arguments)
            if rendered:
                prompt = get_mcp_prompt(name)
                return jsonify(
                    {
                        "jsonrpc": "2.0",
                        "id": jsonrpc_id,
                        "result": {
                            "messages": [
                                {
                                    "role": "user",
                                    "content": {"type": "text", "text": rendered},
                                }
                            ]
                        },
                    }
                )
            return jsonify(
                {
                    "jsonrpc": "2.0",
                    "id": jsonrpc_id,
                    "error": {"code": -32602, "message": f"Prompt not found: {name}"},
                }
            ), 404

        elif method == "ping":
            return jsonify(
                {"jsonrpc": "2.0", "id": jsonrpc_id, "result": {"pong": True}}
            )

        else:
            return jsonify(
                {
                    "jsonrpc": "2.0",
                    "id": jsonrpc_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                }
            ), 404

    except Exception as e:
        logger.exception(f"MCP message processing error: {e}")
        return jsonify(
            {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
                "id": None,
            }
        ), 500


def _get_tool_descriptions() -> dict:
    return {
        "search_news": {
            "description": "搜索国内外新闻舆情信息",
            "parameters": {
                "query": "搜索关键词",
                "max_results": "最大结果数量（默认10）",
                "search_type": "搜索类型: basic/deep/last_24h/last_week/by_date",
                "start_date": "开始日期 (YYYY-MM-DD)",
                "end_date": "结束日期 (YYYY-MM-DD)",
            },
        },
        "start_search_full": {
            "description": "提交 QueryEngine 完整分析任务（异步，分钟级）",
            "parameters": {
                "query": "研究主题 (必填)",
                "max_reflections": "反思轮数 (默认3)",
                "save_report": "是否保存报告文件 (默认True)",
                "output_dir": "输出目录 (可选)",
                "timeout": "超时时间秒 (默认600)",
            },
        },
        "get_search_full_status": {
            "description": "查询分析进度 (轮询模式)",
            "parameters": {
                "task_id": "任务ID (必填)",
            },
        },
        "get_search_full_result": {
            "description": "获取分析结果",
            "parameters": {
                "task_id": "任务ID (必填)",
            },
        },
        "subscribe_search_full": {
            "description": "订阅 SSE 实时进度",
            "parameters": {
                "task_id": "任务ID (必填)",
            },
        },
        "cancel_search_full": {
            "description": "取消分析任务",
            "parameters": {
                "task_id": "任务ID (必填)",
            },
        },
        "start_media_full": {
            "description": "提交 MediaEngine 完整分析任务（异步，分钟级）",
            "parameters": {
                "query": "研究主题 (必填)",
                "max_reflections": "反思轮数 (默认3)",
                "save_report": "是否保存报告文件 (默认True)",
                "output_dir": "输出目录 (可选)",
                "timeout": "超时时间秒 (默认600)",
            },
        },
        "get_media_full_status": {
            "description": "查询媒体分析进度 (轮询模式)",
            "parameters": {
                "task_id": "任务ID (必填)",
            },
        },
        "get_media_full_result": {
            "description": "获取媒体分析结果",
            "parameters": {
                "task_id": "任务ID (必填)",
            },
        },
        "subscribe_media_full": {
            "description": "订阅 SSE 实时进度",
            "parameters": {
                "task_id": "任务ID (必填)",
            },
        },
        "cancel_media_full": {
            "description": "取消媒体分析任务",
            "parameters": {
                "task_id": "任务ID (必填)",
            },
        },
        "start_sentiment_full": {
            "description": "提交 InsightEngine 完整分析任务（异步，分钟级）",
            "parameters": {
                "query": "研究主题 (必填)",
                "max_reflections": "反思轮数 (默认3)",
                "save_report": "是否保存报告文件 (默认True)",
                "output_dir": "输出目录 (可选)",
                "timeout": "超时时间秒 (默认600)",
            },
        },
        "get_sentiment_full_status": {
            "description": "查询舆情分析进度 (轮询模式)",
            "parameters": {
                "task_id": "任务ID (必填)",
            },
        },
        "get_sentiment_full_result": {
            "description": "获取舆情分析结果",
            "parameters": {
                "task_id": "任务ID (必填)",
            },
        },
        "subscribe_sentiment_full": {
            "description": "订阅 SSE 实时进度",
            "parameters": {
                "task_id": "任务ID (必填)",
            },
        },
        "cancel_sentiment_full": {
            "description": "取消舆情分析任务",
            "parameters": {
                "task_id": "任务ID (必填)",
            },
        },
        "start_crawl_full": {
            "description": "提交完整爬取+分析任务（异步，分钟级）",
            "parameters": {
                "keywords": "关键词列表 (必填)",
                "platforms": "平台列表 (默认 [xhs, dy, wb])",
                "crawl_then_analyze": "爬取后是否分析 (默认False)",
                "max_keywords": "最大关键词数量 (默认50)",
                "max_notes": "每个关键词最大爬取数量 (默认50)",
                "test_mode": "测试模式 (默认False)",
                "timeout": "超时时间秒 (默认3600)",
            },
        },
        "get_crawl_full_status": {
            "description": "查询爬取进度 (轮询模式)",
            "parameters": {
                "task_id": "任务ID (必填)",
            },
        },
        "get_crawl_full_result": {
            "description": "获取爬取结果",
            "parameters": {
                "task_id": "任务ID (必填)",
            },
        },
        "subscribe_crawl_full": {
            "description": "订阅 SSE 实时进度",
            "parameters": {
                "task_id": "任务ID (必填)",
            },
        },
        "cancel_crawl_full": {
            "description": "取消爬取任务",
            "parameters": {
                "task_id": "任务ID (必填)",
            },
        },
        "analyze_media": {
            "description": "分析视频/图片等多模态内容",
            "parameters": {
                "query": "分析查询关键词",
                "media_type": "分析类型: comprehensive/web_only/structured/last_24h/last_week",
                "max_results": "最大结果数量",
            },
        },
        "query_sentiment": {
            "description": "查询舆情数据库并进行情感分析",
            "parameters": {
                "keyword": "查询关键词",
                "start_date": "开始日期（YYYY-MM-DD）",
                "end_date": "结束日期（YYYY-MM-DD）",
                "platforms": "平台列表: weibo/douyin/bilibili/xhs/kuaishou/zhihu/tieba",
                "sentiment_type": "情感类型: positive/negative/neutral/all",
                "limit": "返回数量限制",
            },
        },
        "generate_report": {
            "description": "生成分析报告",
            "parameters": {
                "topic": "报告主题",
                "template": "模板名称（可选）",
                "wait_for_completion": "是否等待完成（默认True）",
                "timeout": "超时时间（秒）",
            },
        },
        "crawl_data": {
            "description": "触发爬虫抓取数据",
            "parameters": {
                "keywords": "爬取关键词列表",
                "platforms": "平台列表: xhs/dy/ks/bili/wb/tieba/zhihu",
                "target_date": "目标日期 (YYYY-MM-DD)",
                "max_keywords": "最大关键词数量",
                "max_notes": "每个关键词最大爬取数量",
                "test_mode": "测试模式",
            },
        },
        "analyze_sentiment_texts": {
            "description": "独立分析文本情感",
            "parameters": {
                "texts": "单个文本或文本列表",
            },
        },
        "query_trending": {
            "description": "查询热门内容",
            "parameters": {
                "time_period": "时间范围: 24h/week/year",
                "limit": "返回数量限制",
            },
        },
        "get_report_status": {
            "description": "查询报告生成状态",
            "parameters": {
                "task_id": "任务ID",
            },
        },
        "get_report_result": {
            "description": "获取报告结果",
            "parameters": {
                "task_id": "任务ID",
                "format": "返回格式: html/json",
            },
        },
        "crawl_topics": {
            "description": "仅提取热点话题",
            "parameters": {
                "keywords_count": "关键词数量",
                "extract_date": "提取日期 (YYYY-MM-DD)",
            },
        },
        "check_spider_status": {"description": "检查爬虫系统状态", "parameters": {}},
        "start_forum_research": {
            "description": "启动 ForumEngine + 3个Agent并行研究（异步，10分钟级）",
            "parameters": {
                "topic": "研究主题 (必填)",
                "engines": "启用的引擎列表 (默认 [query, media, insight])",
                "timeout": "超时时间秒 (默认1800)",
            },
        },
        "get_forum_progress": {
            "description": "查询论坛研究进度 (轮询模式)",
            "parameters": {
                "task_id": "任务ID (必填)",
            },
        },
        "get_forum_result": {
            "description": "获取论坛研究结果",
            "parameters": {
                "task_id": "任务ID (必填)",
            },
        },
        "subscribe_forum": {
            "description": "订阅论坛 SSE 实时进度",
            "parameters": {
                "task_id": "任务ID (必填)",
            },
        },
        "stop_forum_research": {
            "description": "停止论坛研究",
            "parameters": {
                "task_id": "任务ID (必填)",
            },
        },
        "get_forum_discussion": {
            "description": "获取论坛讨论内容",
            "parameters": {
                "task_id": "可选的任务ID",
            },
        },
        "start_report": {
            "description": "启动最终报告生成（异步）",
            "parameters": {
                "topic": "报告主题 (必填)",
                "template": "模板名称 (可选)",
                "timeout": "超时时间秒 (默认600)",
            },
        },
        "get_report_status": {
            "description": "查询报告生成进度",
            "parameters": {
                "task_id": "任务ID (必填)",
            },
        },
        "get_report_result": {
            "description": "获取报告结果",
            "parameters": {
                "task_id": "任务ID (必填)",
            },
        },
        "subscribe_report": {
            "description": "订阅报告 SSE 实时进度",
            "parameters": {
                "task_id": "任务ID (必填)",
            },
        },
    }


def _execute_tool(tool_name: str, arguments: dict) -> dict:
    from .tools import search as search_tool
    from .tools import media as media_tool
    from .tools import sentiment as sentiment_tool
    from .tools import report as report_tool
    from .tools import crawl as crawl_tool
    from .tools import forum as forum_tool

    tool_map = {
        "search_news": search_tool.search_news,
        "search_news_deep": search_tool.search_news_deep,
        "start_search_full": search_tool.start_search_full,
        "get_search_full_status": search_tool.get_search_full_status,
        "get_search_full_result": search_tool.get_search_full_result,
        "subscribe_search_full": search_tool.subscribe_search_full,
        "cancel_search_full": search_tool.cancel_search_full,
        "start_media_full": media_tool.start_media_full,
        "get_media_full_status": media_tool.get_media_full_status,
        "get_media_full_result": media_tool.get_media_full_result,
        "subscribe_media_full": media_tool.subscribe_media_full,
        "cancel_media_full": media_tool.cancel_media_full,
        "start_sentiment_full": sentiment_tool.start_sentiment_full,
        "get_sentiment_full_status": sentiment_tool.get_sentiment_full_status,
        "get_sentiment_full_result": sentiment_tool.get_sentiment_full_result,
        "subscribe_sentiment_full": sentiment_tool.subscribe_sentiment_full,
        "cancel_sentiment_full": sentiment_tool.cancel_sentiment_full,
        "start_crawl_full": crawl_tool.start_crawl_full,
        "get_crawl_full_status": crawl_tool.get_crawl_full_status,
        "get_crawl_full_result": crawl_tool.get_crawl_full_result,
        "subscribe_crawl_full": crawl_tool.subscribe_crawl_full,
        "cancel_crawl_full": crawl_tool.cancel_crawl_full,
        "start_forum_research": forum_tool.start_forum_research,
        "get_forum_progress": forum_tool.get_forum_progress,
        "get_forum_result": forum_tool.get_forum_result,
        "subscribe_forum": forum_tool.subscribe_forum,
        "stop_forum_research": forum_tool.stop_forum_research,
        "get_forum_discussion": forum_tool.get_forum_discussion,
        "start_report": forum_tool.start_report,
        "get_report_status": forum_tool.get_report_status,
        "get_report_result": forum_tool.get_report_result,
        "subscribe_report": forum_tool.subscribe_report,
        "analyze_media": media_tool.analyze_media,
        "analyze_video": media_tool.analyze_video,
        "analyze_image": media_tool.analyze_image,
        "query_sentiment": sentiment_tool.query_sentiment,
        "analyze_sentiment_texts": sentiment_tool.analyze_sentiment_texts,
        "query_trending": sentiment_tool.query_trending,
        "generate_report": report_tool.generate_report,
        "get_report_status": report_tool.get_report_status,
        "get_report_result": report_tool.get_report_result,
        "crawl_data": crawl_tool.crawl_data,
        "crawl_topics": crawl_tool.crawl_topics,
        "crawl_social": crawl_tool.crawl_social,
        "check_spider_status": crawl_tool.check_spider_status,
    }

    handler = tool_map.get(tool_name)
    if not handler:
        return {"error": f"Tool not found: {tool_name}"}

    try:
        result = handler(**arguments)
        return result
    except TypeError as e:
        logger.exception(f"Tool parameters error: {tool_name}")
        return {"error": f"Invalid parameters: {str(e)}"}
    except Exception as e:
        logger.exception(f"Tool execution error: {tool_name}")
        return {"error": str(e)}


@mcp_bp.route("/status", methods=["GET"])
def mcp_status():
    """Get MCP server status."""
    return jsonify(
        {
            "success": True,
            "server": "BettaFish-MCP",
            "version": "1.0.0",
            "tools_count": len(_get_tool_descriptions()),
            "resources_count": len(list_mcp_resources()),
            "prompts_count": len(list_mcp_prompts()),
            "sessions": [s.to_dict() for s in mcp_server._sessions.values()],
        }
    )


@mcp_bp.route("/resources", methods=["GET"])
def list_resources():
    """List all available MCP resources."""
    return jsonify({"success": True, "resources": list_mcp_resources()})


@mcp_bp.route("/resources/<path:uri>", methods=["GET"])
def get_resource(uri):
    """Get a specific resource content."""
    resource = get_mcp_resource(f"bettafish://{uri}")
    if resource:
        return jsonify({"success": True, "resource": resource})
    return jsonify({"success": False, "error": f"Resource not found: {uri}"}), 404


@mcp_bp.route("/prompts", methods=["GET"])
def list_prompts():
    """List all available MCP prompts."""
    return jsonify({"success": True, "prompts": list_mcp_prompts()})


@mcp_bp.route("/tools", methods=["GET"])
def list_tools():
    """List all available MCP tools."""
    return jsonify({"success": True, "tools": _get_tool_descriptions()})


@mcp_bp.route("/sessions", methods=["GET"])
def list_sessions():
    """List all active MCP sessions."""
    with stream_lock:
        sessions = [s.to_dict() for s in mcp_server._sessions.values()]
    return jsonify({"success": True, "sessions": sessions, "count": len(sessions)})


@mcp_bp.errorhandler(404)
def not_found(error):
    return jsonify({"success": False, "error": "MCP endpoint not found"}), 404


@mcp_bp.errorhandler(500)
def internal_error(error):
    return jsonify({"success": False, "error": "MCP internal error"}), 500


@mcp_bp.route("/task/<task_id>/status", methods=["GET"])
def get_task_status_endpoint(task_id):
    """查询任务状态"""
    registry = get_task_registry()
    status = registry.get_task_status(task_id)
    if status is None:
        return jsonify({"success": False, "error": f"Task not found: {task_id}"}), 404
    return jsonify({"success": True, **status})


@mcp_bp.route("/task/<task_id>/result", methods=["GET"])
def get_task_result_endpoint(task_id):
    """获取任务结果"""
    registry = get_task_registry()
    result = registry.get_task_result(task_id)
    if result is None:
        return jsonify({"success": False, "error": f"Task not found: {task_id}"}), 404
    return jsonify({"success": True, **result})


@mcp_bp.route("/task/<task_id>/stream", methods=["GET"])
def task_sse_stream(task_id):
    """SSE 实时推送任务进度"""
    registry = get_task_registry()
    task = registry.get_task(task_id)
    if task is None:
        return jsonify({"success": False, "error": f"Task not found: {task_id}"}), 404

    def event_generator():
        last_event_id = request.headers.get("Last-Event-ID")
        try:
            last_event_idx = int(last_event_id) if last_event_id else 0
        except ValueError:
            last_event_idx = 0

        queue = []
        event_list = []

        def callback(event):
            event_list.append(event)

        registry.subscribe(task_id, callback)

        yield format_sse(
            {
                "type": "subscribed",
                "task_id": task_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        )

        last_data_ts = time.time()

        while True:
            if len(event_list) > last_event_idx:
                for i in range(last_event_idx, len(event_list)):
                    yield format_sse(event_list[i])
                    last_data_ts = time.time()
                last_event_idx = len(event_list)

            current_status = registry.get_task_status(task_id)
            if (
                current_status
                and current_status.get("status") in STREAM_TERMINAL_STATUSES
            ):
                break

            time.sleep(0.5)

            idle_for = time.time() - last_data_ts
            if idle_for > STREAM_IDLE_TIMEOUT:
                logger.info(f"Task SSE stream {task_id} idle timeout")
                break

        registry.unsubscribe(task_id, callback)

        yield format_sse(
            {
                "type": "stream_closed",
                "task_id": task_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        )

    response = Response(
        stream_with_context(event_generator()), mimetype="text/event-stream"
    )
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response


@mcp_bp.route("/task/<task_id>/cancel", methods=["POST"])
def cancel_task_endpoint(task_id):
    """取消任务"""
    registry = get_task_registry()
    task = registry.get_task(task_id)
    if task is None:
        return jsonify({"success": False, "error": f"Task not found: {task_id}"}), 404

    success = registry.cancel_task(task_id)
    if success:
        return jsonify(
            {
                "success": True,
                "message": f"Task {task_id} cancelled",
            }
        )
    return jsonify(
        {
            "success": False,
            "error": f"Cannot cancel task in status: {task.status.value}",
        }
    ), 400


@mcp_bp.route("/tasks", methods=["GET"])
def list_tasks_endpoint():
    """列出所有任务"""
    task_type = request.args.get("type")
    status = request.args.get("status")
    registry = get_task_registry()
    tasks = registry.list_tasks(task_type=task_type, status=status)
    return jsonify(
        {
            "success": True,
            "count": len(tasks),
            "tasks": tasks,
        }
    )
