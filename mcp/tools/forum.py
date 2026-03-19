"""
Forum & Report Tool

Wraps ForumEngine and ReportEngine for MCP access.
"""

import concurrent.futures
import time
import os
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
from loguru import logger

from ..task_registry import TaskType, get_task_registry, TaskStatus


def _run_forum_research_task(
    task_id: str,
    topic: str,
    engines: List[str],
    progress_callback: Optional[Callable] = None,
):
    """后台执行论坛研究任务的内部函数"""
    registry = get_task_registry()
    start_time = time.time()

    try:
        registry.update_progress(task_id, 5, "initializing", "初始化 ForumEngine...")

        from ForumEngine.monitor import start_forum_monitoring, get_monitor

        monitor = get_monitor()
        monitor.clear_forum_log()

        registry.update_progress(task_id, 10, "starting_monitoring", "启动日志监控...")

        start_forum_monitoring()

        registry.update_progress(task_id, 15, "launching_engines", "启动分析引擎...")

        engine_configs = {
            "query": {
                "port": 8501,
                "name": "QueryEngine",
                "log_file": "logs/query.log",
            },
            "media": {
                "port": 8502,
                "name": "MediaEngine",
                "log_file": "logs/media.log",
            },
            "insight": {
                "port": 8503,
                "name": "InsightEngine",
                "log_file": "logs/insight.log",
            },
        }

        launched_engines = []
        for engine_name in engines:
            config = engine_configs.get(engine_name)
            if config:
                try:
                    from utils.streamlit_launcher import launch_streamlit_app

                    launch_streamlit_app(
                        engine_name,
                        config["port"],
                        config["name"],
                        config["log_file"],
                    )
                    launched_engines.append(engine_name)
                    registry.update_progress(
                        task_id,
                        15 + len(launched_engines) * 5,
                        "launching_engines",
                        f"已启动 {len(launched_engines)}/{len(engines)} 引擎...",
                    )
                except Exception as e:
                    logger.warning(f"Failed to launch {engine_name}: {e}")

        registry.update_progress(
            task_id, 35, "engines_running", f"引擎运行中，监控研究进度..."
        )

        max_wait = 1800
        check_interval = 5
        waited = 0

        while waited < max_wait:
            task_info = registry.get_task(task_id)
            if not task_info or task_info.status == TaskStatus.CANCELLED:
                break

            log_file = Path("logs/forum.log")
            if log_file.exists():
                with open(log_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                completed_engines = 0
                for engine_name in launched_engines:
                    if any(
                        f"[{engine_name.upper()}] 研究完成" in line for line in lines
                    ):
                        completed_engines += 1

                progress = (
                    35 + int((completed_engines / len(launched_engines)) * 50)
                    if launched_engines
                    else 35
                )
                registry.update_progress(
                    task_id,
                    min(progress, 85),
                    "monitoring",
                    f"研究进度: {completed_engines}/{len(launched_engines)} 引擎完成",
                )

                if completed_engines == len(launched_engines):
                    break

            time.sleep(check_interval)
            waited += check_interval

        registry.update_progress(task_id, 90, "stopping_monitoring", "停止监控...")

        from ForumEngine.monitor import stop_forum_monitoring

        stop_forum_monitoring()

        forum_log_content = ""
        log_file = Path("logs/forum.log")
        if log_file.exists():
            with open(log_file, "r", encoding="utf-8") as f:
                forum_log_content = f.read()

        execution_time = time.time() - start_time

        result = {
            "topic": topic,
            "engines": launched_engines,
            "forum_log_file": str(log_file) if log_file.exists() else None,
            "forum_log_preview": forum_log_content[-5000:]
            if forum_log_content
            else None,
            "total_speeches": forum_log_content.count("发言:")
            if forum_log_content
            else 0,
            "execution_time_seconds": round(execution_time, 2),
            "completed_at": datetime.now().isoformat(),
        }

        registry.complete_task(task_id, result)

    except Exception as e:
        logger.exception(f"Forum research task failed: {task_id}")
        registry.fail_task(task_id, str(e))


def start_forum_research(
    topic: str,
    engines: List[str] = None,
    timeout: int = 1800,
    **kwargs,
) -> Dict[str, Any]:
    """
    启动 ForumEngine + 3个Agent并行研究（异步模式）。

    Args:
        topic: 研究主题
        engines: 启用的引擎列表 (默认 ["query", "media", "insight"])
        timeout: 超时时间(秒，默认30分钟)
        **kwargs: 其他参数

    Returns:
        {
            "success": true,
            "task_id": "forum_xxx",
            "status": "pending",
            "message": "..."
        }
    """
    logger.info(f"MCP start_forum_research: topic={topic}")

    if engines is None:
        engines = ["query", "media", "insight"]

    registry = get_task_registry()

    try:
        task_id = registry.create_task(
            task_type=TaskType.FORUM_RESEARCH.value,
            params={
                "topic": topic,
                "engines": engines,
            },
            timeout=timeout,
        )

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        executor.submit(
            _run_forum_research_task,
            task_id,
            topic,
            engines,
        )

        return {
            "success": True,
            "task_id": task_id,
            "status": "pending",
            "message": f"ForumEngine研究任务已提交，请使用 get_forum_progress 查询进度",
            "endpoints": {
                "progress": f"/mcp/task/{task_id}/status",
                "result": f"/mcp/task/{task_id}/result",
                "stream": f"/mcp/task/{task_id}/stream",
                "stop": f"/mcp/task/{task_id}/cancel",
                "discussion": f"/mcp/forums/discussion",
            },
        }

    except RuntimeError as e:
        return {
            "success": False,
            "error": str(e),
            "message": "并发任务已满，请稍后再试",
        }
    except Exception as e:
        logger.exception(f"Failed to start forum research: {e}")
        return {
            "success": False,
            "error": str(e),
        }


def get_forum_progress(task_id: str) -> Dict[str, Any]:
    """
    查询论坛研究进度 (轮询模式)。

    Args:
        task_id: 任务ID

    Returns:
        {
            "success": true,
            "task_id": "...",
            "status": "running",
            "progress": 45,
            "engines": {...},
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


def get_forum_result(task_id: str) -> Dict[str, Any]:
    """
    获取论坛研究结果。

    Args:
        task_id: 任务ID

    Returns:
        {
            "success": true,
            "task_id": "...",
            "status": "completed",
            "topic": "...",
            "engines": ["query", "media", "insight"],
            "forum_log_file": "...",
            "total_speeches": 25,
            "execution_time_seconds": 600,
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


def subscribe_forum(task_id: str) -> Dict[str, Any]:
    """
    订阅论坛 SSE 实时进度（返回 SSE 端点）。

    Args:
        task_id: 任务ID

    Returns:
        {
            "success": true,
            "stream_url": "/mcp/task/{task_id}/stream",
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

    return {
        "success": True,
        "stream_url": f"/mcp/task/{task_id}/stream",
        "message": "请使用 EventSource 连接 SSE 端点接收实时进度",
    }


def stop_forum_research(task_id: str) -> Dict[str, Any]:
    """
    停止论坛研究。

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
        try:
            from ForumEngine.monitor import stop_forum_monitoring

            stop_forum_monitoring()
        except Exception as e:
            logger.warning(f"Failed to stop forum monitoring: {e}")

        return {
            "success": True,
            "message": f"Task {task_id} stopped",
        }

    return {
        "success": False,
        "error": f"Cannot stop task in status: {task.status.value}",
    }


def get_forum_discussion(task_id: str = None) -> Dict[str, Any]:
    """
    获取论坛讨论内容。

    Args:
        task_id: 可选的论坛任务ID

    Returns:
        {
            "success": true,
            "discussion": "...",
            "file": "logs/forum.log"
        }
    """
    try:
        from ForumEngine.monitor import get_monitor

        monitor = get_monitor()
        content = monitor.get_forum_log_content()

        return {
            "success": True,
            "discussion": content,
            "file": "logs/forum.log",
            "lines": len(content) if isinstance(content, list) else 0,
        }

    except Exception as e:
        logger.exception(f"Failed to get forum discussion: {e}")
        return {
            "success": False,
            "error": str(e),
        }


def _run_report_task(
    task_id: str,
    topic: str,
    template: str,
    progress_callback: Optional[Callable] = None,
):
    """后台执行报告生成任务的内部函数"""
    registry = get_task_registry()
    start_time = time.time()

    try:
        registry.update_progress(task_id, 5, "initializing", "初始化 ReportEngine...")

        from ReportEngine.flask_interface import generate_report_sync

        registry.update_progress(task_id, 10, "collecting_data", "收集分析数据...")

        report_content = generate_report_sync(
            topic=topic,
            template=template,
            wait_for_completion=True,
        )

        registry.update_progress(task_id, 90, "finalizing", "生成最终报告...")

        execution_time = time.time() - start_time

        result = {
            "topic": topic,
            "template": template,
            "report_content": report_content,
            "execution_time_seconds": round(execution_time, 2),
            "completed_at": datetime.now().isoformat(),
        }

        registry.complete_task(task_id, result)

    except Exception as e:
        logger.exception(f"Report task failed: {task_id}")
        registry.fail_task(task_id, str(e))


def start_report(
    topic: str,
    template: str = None,
    timeout: int = 600,
    **kwargs,
) -> Dict[str, Any]:
    """
    启动最终报告生成（异步模式）。

    Args:
        topic: 报告主题
        template: 模板名称 (可选)
        timeout: 超时时间(秒，默认10分钟)
        **kwargs: 其他参数

    Returns:
        {
            "success": true,
            "task_id": "report_xxx",
            "status": "pending",
            "message": "..."
        }
    """
    logger.info(f"MCP start_report: topic={topic}")

    registry = get_task_registry()

    try:
        task_id = registry.create_task(
            task_type=TaskType.REPORT.value,
            params={
                "topic": topic,
                "template": template,
            },
            timeout=timeout,
        )

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        executor.submit(
            _run_report_task,
            task_id,
            topic,
            template,
        )

        return {
            "success": True,
            "task_id": task_id,
            "status": "pending",
            "message": f"报告生成任务已提交，请使用 get_report_status 查询进度",
            "endpoints": {
                "status": f"/mcp/task/{task_id}/status",
                "result": f"/mcp/task/{task_id}/result",
                "stream": f"/mcp/task/{task_id}/stream",
            },
        }

    except RuntimeError as e:
        return {
            "success": False,
            "error": str(e),
            "message": "并发任务已满，请稍后再试",
        }
    except Exception as e:
        logger.exception(f"Failed to start report: {e}")
        return {
            "success": False,
            "error": str(e),
        }


def get_report_status(task_id: str) -> Dict[str, Any]:
    """
    查询报告生成进度。

    Args:
        task_id: 任务ID

    Returns:
        {
            "success": true,
            "task_id": "...",
            "status": "running",
            "progress": 45,
            "stage": "collecting_data",
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


def get_report_result(task_id: str) -> Dict[str, Any]:
    """
    获取报告结果。

    Args:
        task_id: 任务ID

    Returns:
        {
            "success": true,
            "task_id": "...",
            "status": "completed",
            "topic": "...",
            "report_content": "# Markdown...",
            "execution_time_seconds": 120,
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


def subscribe_report(task_id: str) -> Dict[str, Any]:
    """
    订阅报告 SSE 实时进度（返回 SSE 端点）。

    Args:
        task_id: 任务ID

    Returns:
        {
            "success": true,
            "stream_url": "/mcp/task/{task_id}/stream",
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

    return {
        "success": True,
        "stream_url": f"/mcp/task/{task_id}/stream",
        "message": "请使用 EventSource 连接 SSE 端点接收实时进度",
    }
