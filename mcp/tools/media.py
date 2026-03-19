"""
Media Analysis Tool

Wraps MediaEngine for MCP access.
"""

import concurrent.futures
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from loguru import logger

from ..task_registry import TaskType, get_task_registry, TaskStatus


def _run_media_full_task(
    task_id: str,
    query: str,
    max_reflections: int,
    save_report: bool,
    output_dir: str,
    progress_callback: Optional[Callable] = None,
):
    """后台执行完整媒体分析任务的内部函数"""
    registry = get_task_registry()
    start_time = time.time()

    try:
        registry.update_progress(task_id, 5, "initializing", "初始化 MediaEngine...")

        from MediaEngine.agent import DeepSearchAgent
        from MediaEngine.utils.config import settings

        config = settings
        config.MAX_REFLECTIONS = max_reflections
        if output_dir:
            config.OUTPUT_DIR = output_dir

        agent = DeepSearchAgent(config=config)

        registry.update_progress(task_id, 10, "generating_structure", "生成报告结构...")

        agent._generate_report_structure(query)

        total_paragraphs = len(agent.state.paragraphs)
        registry.update_progress(
            task_id,
            15,
            "processing_paragraphs",
            f"开始处理 {total_paragraphs} 个段落...",
        )

        for i in range(total_paragraphs):
            paragraph_progress = 15 + int((i / total_paragraphs) * 75)
            registry.update_progress(
                task_id,
                paragraph_progress,
                "initial_search",
                f"正在处理段落 {i + 1}/{total_paragraphs}: {agent.state.paragraphs[i].title[:30]}...",
            )

            agent._initial_search_and_summary(i)

            registry.update_progress(
                task_id,
                paragraph_progress + 5,
                "reflection_loop",
                f"段落 {i + 1} 反思中...",
            )

            agent._reflection_loop(i)
            agent.state.paragraphs[i].research.mark_completed()

            registry.update_progress(
                task_id,
                int(15 + ((i + 1) / total_paragraphs) * 75),
                "paragraph_completed",
                f"段落 {i + 1}/{total_paragraphs} 处理完成",
            )

        registry.update_progress(task_id, 90, "generating_report", "生成最终报告...")

        final_report = agent._generate_final_report()

        report_file = None
        if save_report:
            report_file = agent._save_report(final_report)

        execution_time = time.time() - start_time

        result = {
            "query": query,
            "report_content": final_report,
            "report_file": report_file,
            "paragraphs_count": total_paragraphs,
            "reflections_per_paragraph": max_reflections,
            "execution_time_seconds": round(execution_time, 2),
            "completed_at": datetime.now().isoformat(),
        }

        registry.complete_task(task_id, result)

    except Exception as e:
        logger.exception(f"Media full task failed: {task_id}")
        registry.fail_task(task_id, str(e))


def start_media_full(
    query: str,
    max_reflections: int = 3,
    save_report: bool = True,
    output_dir: str = None,
    timeout: int = 600,
    **kwargs,
) -> Dict[str, Any]:
    """
    提交 MediaEngine 完整分析任务（异步模式）。

    Args:
        query: 研究主题
        max_reflections: 反思轮数 (默认3)
        save_report: 是否保存报告文件
        output_dir: 输出目录 (可选)
        timeout: 超时时间(秒)
        **kwargs: 其他参数

    Returns:
        {
            "success": true,
            "task_id": "media_full_xxx",
            "status": "pending",
            "message": "..."
        }
    """
    logger.info(f"MCP start_media_full: query={query}")

    registry = get_task_registry()

    try:
        task_id = registry.create_task(
            task_type=TaskType.MEDIA_FULL.value,
            params={
                "query": query,
                "max_reflections": max_reflections,
                "save_report": save_report,
                "output_dir": output_dir,
            },
            timeout=timeout,
        )

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        executor.submit(
            _run_media_full_task,
            task_id,
            query,
            max_reflections,
            save_report,
            output_dir,
        )

        return {
            "success": True,
            "task_id": task_id,
            "status": "pending",
            "message": f"媒体分析任务已提交，请使用 get_media_full_status 查询进度",
            "endpoints": {
                "status": f"/mcp/task/{task_id}/status",
                "result": f"/mcp/task/{task_id}/result",
                "stream": f"/mcp/task/{task_id}/stream",
                "cancel": f"/mcp/task/{task_id}/cancel",
            },
        }

    except RuntimeError as e:
        return {
            "success": False,
            "error": str(e),
            "message": "并发任务已满，请稍后再试",
        }
    except Exception as e:
        logger.exception(f"Failed to start media full task: {e}")
        return {
            "success": False,
            "error": str(e),
        }


def get_media_full_status(task_id: str) -> Dict[str, Any]:
    """
    查询媒体分析进度 (轮询模式)。

    Args:
        task_id: 任务ID

    Returns:
        {
            "success": true,
            "task_id": "...",
            "status": "running",
            "progress": 45,
            "stage": "reflection_loop",
            "stage_detail": "正在处理段落 3/6",
            "started_at": "...",
            "message": "..."
        }
    """
    registry = get_task_registry()
    status = registry.get_task_status(task_id)

    if status is None:
        return {
            "success": False,
            "error": f"Task not found: {task_id}",
        }

    return {
        "success": True,
        **status,
    }


def get_media_full_result(task_id: str) -> Dict[str, Any]:
    """
    获取媒体分析结果。

    Args:
        task_id: 任务ID

    Returns:
        {
            "success": true,
            "task_id": "...",
            "status": "completed",
            "query": "...",
            "report_content": "# Markdown...",
            "report_file": "path/to/report.md",
            "paragraphs_count": 6,
            "reflections_per_paragraph": 3,
            "execution_time_seconds": 180,
            "completed_at": "..."
        }
    """
    registry = get_task_registry()
    result = registry.get_task_result(task_id)

    if result is None:
        return {
            "success": False,
            "error": f"Task not found: {task_id}",
        }

    return {
        "success": True,
        **result,
    }


def subscribe_media_full(task_id: str) -> Dict[str, Any]:
    """
    订阅 SSE 实时进度（返回 SSE 端点）。

    Args:
        task_id: 任务ID

    Returns:
        {
            "success": true,
            "stream_url": "/mcp/task/{task_id}/stream",
            "message": "请使用 EventSource 连接 SSE 端点"
        }
    """
    registry = get_task_registry()
    task = registry.get_task(task_id)

    if task is None:
        return {
            "success": False,
            "error": f"Task not found: {task_id}",
        }

    return {
        "success": True,
        "stream_url": f"/mcp/task/{task_id}/stream",
        "message": "请使用 EventSource 连接 SSE 端点接收实时进度",
    }


def cancel_media_full(task_id: str) -> Dict[str, Any]:
    """
    取消媒体分析任务。

    Args:
        task_id: 任务ID

    Returns:
        {
            "success": true,
            "message": "..."
        }
    """
    registry = get_task_registry()

    task = registry.get_task(task_id)
    if task is None:
        return {
            "success": False,
            "error": f"Task not found: {task_id}",
        }

    success = registry.cancel_task(task_id)

    if success:
        return {
            "success": True,
            "message": f"Task {task_id} cancelled",
        }

    return {
        "success": False,
        "error": f"Cannot cancel task in status: {task.status.value}",
    }


def analyze_media(
    query: str, media_type: str = "comprehensive", max_results: int = 10, **kwargs
) -> Dict[str, Any]:
    """
    分析视频/图片等多模态内容。

    Args:
        query: 分析查询关键词
        media_type: 分析类型
            - comprehensive: 综合多模态搜索（默认）
            - web_only: 仅网络搜索
            - structured: 结构化数据（天气、股票等）
            - last_24h: 24小时内最新
            - last_week: 本周新闻
        max_results: 最大结果数量
        **kwargs: 其他参数

    Returns:
        分析结果字典
    """
    logger.info(
        f"MCP analyze_media: query={query}, type={media_type}, max_results={max_results}"
    )

    tool_name_map = {
        "comprehensive": "comprehensive_search",
        "web_only": "web_search_only",
        "structured": "search_for_structured_data",
        "last_24h": "search_last_24_hours",
        "last_week": "search_last_week",
    }

    tool_name = tool_name_map.get(media_type, "comprehensive_search")

    try:
        from MediaEngine.agent import DeepSearchAgent

        def run_analysis():
            agent = DeepSearchAgent()
            return agent.execute_search_tool(tool_name, query, max_results=max_results)

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_analysis)
            response = future.result(timeout=120)

        results = []
        if response and response.results:
            for result in response.results:
                results.append(
                    {
                        "title": result.title,
                        "url": result.url,
                        "content": result.content[:500] if result.content else "",
                        "score": getattr(result, "score", None),
                        "ai_answer": getattr(result, "ai_answer", None),
                    }
                )

        return {
            "success": True,
            "query": query,
            "media_type": media_type,
            "tool_used": tool_name,
            "results_count": len(results),
            "results": results,
            "message": f"Media analysis completed with {len(results)} results",
        }
    except Exception as e:
        logger.exception(f"Media analysis error: {e}")
        return {"success": False, "error": str(e), "query": query}


def analyze_video(url: str, **kwargs) -> Dict[str, Any]:
    """
    分析视频内容（通过URL）。

    Args:
        url: 视频URL
        **kwargs: 其他参数

    Returns:
        分析结果
    """
    logger.info(f"MCP analyze_video: url={url}")

    return {
        "success": True,
        "message": "Video analysis via URL - use comprehensive search with video-related query",
        "url": url,
        "suggestion": "Use analyze_media with query containing video description or topic",
    }


def analyze_image(url: str = None, path: str = None, **kwargs) -> Dict[str, Any]:
    """
    分析图片内容。

    Args:
        url: 图片URL
        path: 本地图片路径
        **kwargs: 其他参数

    Returns:
        分析结果
    """
    logger.info(f"MCP analyze_image: url={url}, path={path}")

    return {
        "success": True,
        "message": "Image analysis - use comprehensive search with image-related query",
        "url": url,
        "path": path,
        "suggestion": "Use analyze_media with query describing the image content",
    }
