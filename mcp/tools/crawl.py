"""
Crawl Data Tool

Wraps MindSpider for MCP access.
"""

import concurrent.futures
import time
from datetime import date, datetime
from typing import Dict, Any, List, Optional, Callable
from loguru import logger

from ..task_registry import TaskType, get_task_registry, TaskStatus


SUPPORTED_PLATFORMS = {
    "xhs": "小红书 (Xiaohongshu)",
    "dy": "抖音 (Douyin)",
    "ks": "快手 (Kuaishou)",
    "bili": "B站 (Bilibili)",
    "wb": "微博 (Weibo)",
    "tieba": "百度贴吧",
    "zhihu": "知乎",
}


def crawl_data(
    keywords: List[str],
    platforms: List[str] = None,
    target_date: str = None,
    max_keywords: int = 50,
    max_notes: int = 50,
    test_mode: bool = False,
    **kwargs,
) -> Dict[str, Any]:
    """
    触发爬虫抓取数据。

    Args:
        keywords: 爬取关键词列表
        platforms: 平台列表 ["xhs", "dy", "ks", "bili", "wb", "tieba", "zhihu"]
        target_date: 目标日期 (YYYY-MM-DD)，默认今天
        max_keywords: 最大关键词数量
        max_notes: 每个关键词最大爬取数量
        test_mode: 测试模式（少量数据）
        **kwargs: 其他参数

    Returns:
        爬取结果字典
    """
    logger.info(f"MCP crawl_data: keywords={keywords}, platforms={platforms}")

    if platforms is None:
        platforms = ["xhs", "dy", "wb"]

    normalized_platforms = [p.lower() for p in platforms]
    for p in normalized_platforms:
        if p not in SUPPORTED_PLATFORMS:
            return {
                "success": False,
                "error": f"Unsupported platform: {p}. Supported: {list(SUPPORTED_PLATFORMS.keys())}",
                "platforms": platforms,
            }

    try:
        target = date.today()
        if target_date:
            target = datetime.strptime(target_date, "%Y-%m-%d").date()

        from MindSpider.main import MindSpider

        def run_crawl():
            spider = MindSpider()

            if not spider.check_config():
                raise Exception("MindSpider config check failed")

            if not spider.check_database_connection():
                raise Exception("Database connection failed")

            spider.run_complete_workflow(
                target_date=target,
                platforms=normalized_platforms,
                keywords_count=len(keywords),
                max_keywords=max_keywords,
                max_notes=max_notes,
                test_mode=test_mode,
            )

            return {
                "platforms": normalized_platforms,
                "target_date": str(target),
                "keywords_count": len(keywords),
            }

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_crawl)
            result = future.result(timeout=3600)

        return {"success": True, "message": "Crawl completed", **result}

    except concurrent.futures.TimeoutError:
        return {
            "success": False,
            "error": f"Crawl timeout (>1 hour)",
            "keywords": keywords,
            "platforms": platforms,
        }
    except Exception as e:
        logger.exception(f"Crawl error: {e}")
        return {
            "success": False,
            "error": str(e),
            "keywords": keywords,
            "platforms": platforms,
        }


def crawl_topics(
    keywords_count: int = 100, extract_date: str = None, **kwargs
) -> Dict[str, Any]:
    """
    仅提取热点话题（不爬取社交媒体）。

    Args:
        keywords_count: 提取的关键词数量
        extract_date: 提取日期 (YYYY-MM-DD)
        **kwargs: 其他参数

    Returns:
        话题提取结果
    """
    logger.info(f"MCP crawl_topics: count={keywords_count}")

    try:
        target = date.today()
        if extract_date:
            target = datetime.strptime(extract_date, "%Y-%m-%d").date()

        from MindSpider.main import MindSpider

        def run_extraction():
            spider = MindSpider()
            spider.run_broad_topic_extraction(
                extract_date=target, keywords_count=keywords_count
            )
            return {"keywords_count": keywords_count, "date": str(target)}

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_extraction)
            result = future.result(timeout=600)

        return {"success": True, "message": "Topic extraction completed", **result}

    except Exception as e:
        logger.exception(f"Topic extraction error: {e}")
        return {"success": False, "error": str(e)}


def crawl_social(
    platforms: List[str],
    max_keywords: int = 30,
    max_notes: int = 20,
    target_date: str = None,
    test_mode: bool = False,
    **kwargs,
) -> Dict[str, Any]:
    """
    仅爬取社交媒体数据（使用已有话题）。

    Args:
        platforms: 平台列表
        max_keywords: 最大关键词数量
        max_notes: 每个关键词最大爬取数量
        target_date: 目标日期
        test_mode: 测试模式
        **kwargs: 其他参数

    Returns:
        爬取结果
    """
    logger.info(f"MCP crawl_social: platforms={platforms}")

    try:
        target = date.today()
        if target_date:
            target = datetime.strptime(target_date, "%Y-%m-%d").date()

        from MindSpider.main import MindSpider

        def run_crawl():
            spider = MindSpider()
            spider.run_deep_sentiment_crawling(
                target_date=target,
                platforms=[p.lower() for p in platforms],
                max_keywords=max_keywords,
                max_notes=max_notes,
                test_mode=test_mode,
            )
            return {"platforms": platforms, "date": str(target)}

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_crawl)
            result = future.result(timeout=3600)

        return {"success": True, "message": "Social media crawl completed", **result}

    except Exception as e:
        logger.exception(f"Social crawl error: {e}")
        return {"success": False, "error": str(e), "platforms": platforms}


def check_spider_status(**kwargs) -> Dict[str, Any]:
    """
    检查爬虫系统状态。

    Returns:
        系统状态信息
    """
    logger.info("MCP check_spider_status")

    try:
        from MindSpider.main import MindSpider

        spider = MindSpider()

        config_ok = spider.check_config()
        db_ok = spider.check_database_connection()
        tables_ok = spider.check_database_tables()

        return {
            "success": True,
            "config_valid": config_ok,
            "database_connected": db_ok,
            "tables_ready": tables_ok,
            "supported_platforms": SUPPORTED_PLATFORMS,
            "message": "All checks passed"
            if all([config_ok, db_ok, tables_ok])
            else "Some checks failed",
        }

    except Exception as e:
        logger.exception(f"Status check error: {e}")
        return {"success": False, "error": str(e)}


def _run_crawl_full_task(
    task_id: str,
    keywords: List[str],
    platforms: List[str],
    crawl_then_analyze: bool,
    max_keywords: int,
    max_notes: int,
    test_mode: bool,
    progress_callback: Optional[Callable] = None,
):
    """后台执行完整爬取+分析任务的内部函数"""
    registry = get_task_registry()
    start_time = time.time()

    try:
        registry.update_progress(task_id, 5, "initializing", "初始化 MindSpider...")

        from MindSpider.main import MindSpider

        spider = MindSpider()

        if not spider.check_config():
            raise Exception("MindSpider config check failed")

        registry.update_progress(task_id, 10, "config_checked", "配置检查通过...")

        if not spider.check_database_connection():
            raise Exception("Database connection failed")

        registry.update_progress(task_id, 15, "db_connected", "数据库连接正常...")

        target = date.today()
        registry.update_progress(
            task_id, 20, "starting_crawl", f"开始爬取 {len(keywords)} 个关键词..."
        )

        spider.run_complete_workflow(
            target_date=target,
            platforms=platforms,
            keywords_count=len(keywords),
            max_keywords=max_keywords,
            max_notes=max_notes,
            test_mode=test_mode,
        )

        registry.update_progress(
            task_id, 70, "crawl_completed", "爬取完成，正在分析..."
        )

        crawl_result = {
            "platforms": platforms,
            "target_date": str(target),
            "keywords_count": len(keywords),
            "max_keywords": max_keywords,
            "max_notes": max_notes,
        }

        execution_time = time.time() - start_time

        result = {
            "keywords": keywords,
            **crawl_result,
            "crawl_then_analyze": crawl_then_analyze,
            "execution_time_seconds": round(execution_time, 2),
            "completed_at": datetime.now().isoformat(),
        }

        registry.complete_task(task_id, result)

    except Exception as e:
        logger.exception(f"Crawl full task failed: {task_id}")
        registry.fail_task(task_id, str(e))


def start_crawl_full(
    keywords: List[str],
    platforms: List[str] = None,
    crawl_then_analyze: bool = False,
    max_keywords: int = 50,
    max_notes: int = 50,
    test_mode: bool = False,
    timeout: int = 3600,
    **kwargs,
) -> Dict[str, Any]:
    """
    提交完整爬取+分析任务（异步模式）。

    Args:
        keywords: 爬取关键词列表
        platforms: 平台列表 (默认 ["xhs", "dy", "wb"])
        crawl_then_analyze: 爬取后是否分析 (暂未实现)
        max_keywords: 最大关键词数量
        max_notes: 每个关键词最大爬取数量
        test_mode: 测试模式
        timeout: 超时时间(秒)
        **kwargs: 其他参数

    Returns:
        {
            "success": true,
            "task_id": "crawl_full_xxx",
            "status": "pending",
            "message": "..."
        }
    """
    logger.info(f"MCP start_crawl_full: keywords={keywords}, platforms={platforms}")

    if platforms is None:
        platforms = ["xhs", "dy", "wb"]

    normalized_platforms = [p.lower() for p in platforms]
    for p in normalized_platforms:
        if p not in SUPPORTED_PLATFORMS:
            return {
                "success": False,
                "error": f"Unsupported platform: {p}. Supported: {list(SUPPORTED_PLATFORMS.keys())}",
                "platforms": platforms,
            }

    registry = get_task_registry()

    try:
        task_id = registry.create_task(
            task_type=TaskType.CRAWL_FULL.value,
            params={
                "keywords": keywords,
                "platforms": normalized_platforms,
                "crawl_then_analyze": crawl_then_analyze,
                "max_keywords": max_keywords,
                "max_notes": max_notes,
                "test_mode": test_mode,
            },
            timeout=timeout,
        )

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        executor.submit(
            _run_crawl_full_task,
            task_id,
            keywords,
            normalized_platforms,
            crawl_then_analyze,
            max_keywords,
            max_notes,
            test_mode,
        )

        return {
            "success": True,
            "task_id": task_id,
            "status": "pending",
            "message": f"爬取任务已提交，请使用 get_crawl_full_status 查询进度",
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
        logger.exception(f"Failed to start crawl full task: {e}")
        return {
            "success": False,
            "error": str(e),
        }


def get_crawl_full_status(task_id: str) -> Dict[str, Any]:
    """
    查询爬取进度 (轮询模式)。

    Args:
        task_id: 任务ID

    Returns:
        {
            "success": true,
            "task_id": "...",
            "status": "running",
            "progress": 45,
            "stage": "starting_crawl",
            "stage_detail": "开始爬取 10 个关键词...",
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


def get_crawl_full_result(task_id: str) -> Dict[str, Any]:
    """
    获取爬取结果。

    Args:
        task_id: 任务ID

    Returns:
        {
            "success": true,
            "task_id": "...",
            "status": "completed",
            "keywords": ["关键词1", "关键词2"],
            "platforms": ["xhs", "dy", "wb"],
            "target_date": "2026-03-18",
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


def subscribe_crawl_full(task_id: str) -> Dict[str, Any]:
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


def cancel_crawl_full(task_id: str) -> Dict[str, Any]:
    """
    取消爬取任务。

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
