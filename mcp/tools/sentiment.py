"""
Sentiment Query Tool

Wraps InsightEngine for MCP access.
"""

import concurrent.futures
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, Callable
from loguru import logger

from ..task_registry import TaskType, get_task_registry, TaskStatus


PLATFORM_CODES = {
    "bilibili": "bili",
    "weibo": "wb",
    "douyin": "dy",
    "kuaishou": "ks",
    "xiaohongshu": "xhs",
    "xhs": "xhs",
    "zhihu": "zhihu",
    "tieba": "tieba",
    "bili": "bili",
    "wb": "wb",
    "dy": "dy",
    "ks": "ks",
}

SENTIMENT_LABELS = {1: "非常负面", 2: "负面", 3: "中性", 4: "正面", 5: "非常正面"}


def query_sentiment(
    keyword: str,
    start_date: str = None,
    end_date: str = None,
    platforms: List[str] = None,
    sentiment_type: str = "all",
    enable_clustering: bool = True,
    limit: int = 100,
    **kwargs,
) -> Dict[str, Any]:
    """
    查询舆情数据库并进行情感分析。

    Args:
        keyword: 查询关键词
        start_date: 开始日期（YYYY-MM-DD）
        end_date: 结束日期（YYYY-MM-DD）
        platforms: 平台列表 ["weibo", "douyin", "bilibili", "xhs", "kuaishou", "zhihu", "tieba"]
        sentiment_type: 情感类型过滤 (positive/negative/neutral/all)
        enable_clustering: 是否启用聚类采样
        limit: 返回结果数量限制
        **kwargs: 其他参数

    Returns:
        舆情查询结果字典
    """
    logger.info(
        f"MCP query_sentiment: keyword={keyword}, platforms={platforms}, limit={limit}"
    )

    normalized_platforms = None
    if platforms:
        normalized_platforms = [PLATFORM_CODES.get(p.lower(), p) for p in platforms]

    try:
        from InsightEngine.agent import DeepSearchAgent

        def run_query():
            agent = DeepSearchAgent()

            if normalized_platforms and len(normalized_platforms) == 1:
                response = agent.execute_search_tool(
                    "search_topic_on_platform",
                    keyword,
                    platform=normalized_platforms[0],
                    start_date=start_date,
                    end_date=end_date,
                    limit_per_table=limit,
                    enable_sentiment=True,
                )
            else:
                if start_date and end_date:
                    response = agent.execute_search_tool(
                        "search_topic_by_date",
                        keyword,
                        start_date=start_date,
                        end_date=end_date,
                        limit_per_table=limit,
                        enable_sentiment=True,
                    )
                else:
                    response = agent.execute_search_tool(
                        "search_topic_globally",
                        keyword,
                        limit_per_table=limit,
                        enable_sentiment=True,
                    )

            return response

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_query)
            response = future.result(timeout=120)

        results = []
        sentiment_summary = {"positive": 0, "negative": 0, "neutral": 0}

        if response and hasattr(response, "results"):
            for result in response.results[:limit]:
                item = {
                    "content": getattr(result, "content", "")[:500],
                    "platform": getattr(result, "platform", ""),
                    "author": getattr(result, "author", ""),
                    "publish_time": getattr(result, "publish_time", ""),
                    "like_count": getattr(result, "like_count", 0),
                    "sentiment": getattr(result, "sentiment", None),
                }

                if item["sentiment"]:
                    sentiment_label = SENTIMENT_LABELS.get(item["sentiment"], "未知")
                    item["sentiment_label"] = sentiment_label

                    if item["sentiment"] >= 4:
                        sentiment_summary["positive"] += 1
                    elif item["sentiment"] <= 2:
                        sentiment_summary["negative"] += 1
                    else:
                        sentiment_summary["neutral"] += 1

                results.append(item)

        return {
            "success": True,
            "keyword": keyword,
            "platforms": normalized_platforms or "all",
            "start_date": start_date,
            "end_date": end_date,
            "results_count": len(results),
            "sentiment_summary": sentiment_summary,
            "results": results,
            "message": f"Found {len(results)} results with sentiment analysis",
        }
    except Exception as e:
        logger.exception(f"Sentiment query error: {e}")
        return {"success": False, "error": str(e), "keyword": keyword}


def analyze_sentiment_texts(texts: Union[str, List[str]], **kwargs) -> Dict[str, Any]:
    """
    独立分析文本情感。

    Args:
        texts: 单个文本或文本列表
        **kwargs: 其他参数

    Returns:
        情感分析结果
    """
    logger.info(
        f"MCP analyze_sentiment_texts: {len(texts) if isinstance(texts, list) else 1} texts"
    )

    try:
        from InsightEngine.agent import DeepSearchAgent

        def run_analysis():
            agent = DeepSearchAgent()
            return agent.analyze_sentiment_only(texts)

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_analysis)
            results = future.result(timeout=60)

        analyzed = []
        if isinstance(results, list):
            for item in results:
                if isinstance(item, dict):
                    sentiment = item.get("sentiment", 3)
                    analyzed.append(
                        {
                            "text": item.get("text", "")[:200],
                            "sentiment": sentiment,
                            "sentiment_label": SENTIMENT_LABELS.get(sentiment, "未知"),
                            "confidence": item.get("confidence", 0),
                        }
                    )

        return {
            "success": True,
            "texts_count": len(analyzed),
            "results": analyzed,
            "summary": {
                "positive": sum(1 for r in analyzed if r["sentiment"] >= 4),
                "negative": sum(1 for r in analyzed if r["sentiment"] <= 2),
                "neutral": sum(1 for r in analyzed if r["sentiment"] == 3),
            },
        }
    except Exception as e:
        logger.exception(f"Sentiment analysis error: {e}")
        return {"success": False, "error": str(e)}


def query_trending(
    time_period: str = "24h", limit: int = 50, **kwargs
) -> Dict[str, Any]:
    """
    查询热门内容。

    Args:
        time_period: 时间范围 (24h/week/year)
        limit: 返回数量限制
        **kwargs: 其他参数

    Returns:
        热门内容列表
    """
    logger.info(f"MCP query_trending: period={time_period}, limit={limit}")

    try:
        from InsightEngine.agent import DeepSearchAgent

        def run_query():
            agent = DeepSearchAgent()
            return agent.execute_search_tool(
                "search_hot_content", time_period=time_period, limit=limit
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_query)
            response = future.result(timeout=60)

        results = []
        if response and hasattr(response, "results"):
            for result in response.results[:limit]:
                results.append(
                    {
                        "content": getattr(result, "content", "")[:300],
                        "platform": getattr(result, "platform", ""),
                        "hot_score": getattr(result, "hot_score", 0),
                        "publish_time": getattr(result, "publish_time", ""),
                    }
                )

        return {
            "success": True,
            "time_period": time_period,
            "results_count": len(results),
            "results": results,
        }
    except Exception as e:
        logger.exception(f"Trending query error: {e}")
        return {"success": False, "error": str(e)}


def _run_sentiment_full_task(
    task_id: str,
    query: str,
    max_reflections: int,
    save_report: bool,
    output_dir: str,
    progress_callback: Optional[Callable] = None,
):
    """后台执行完整舆情分析任务的内部函数"""
    registry = get_task_registry()
    start_time = time.time()

    try:
        registry.update_progress(task_id, 5, "initializing", "初始化 InsightEngine...")

        from InsightEngine.agent import DeepSearchAgent
        from InsightEngine.utils.config import settings

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
        logger.exception(f"Sentiment full task failed: {task_id}")
        registry.fail_task(task_id, str(e))


def start_sentiment_full(
    query: str,
    max_reflections: int = 3,
    save_report: bool = True,
    output_dir: str = None,
    timeout: int = 600,
    **kwargs,
) -> Dict[str, Any]:
    """
    提交 InsightEngine 完整分析任务（异步模式）。

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
            "task_id": "sentiment_full_xxx",
            "status": "pending",
            "message": "..."
        }
    """
    logger.info(f"MCP start_sentiment_full: query={query}")

    registry = get_task_registry()

    try:
        task_id = registry.create_task(
            task_type=TaskType.SENTIMENT_FULL.value,
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
            _run_sentiment_full_task,
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
            "message": f"舆情分析任务已提交，请使用 get_sentiment_full_status 查询进度",
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
        logger.exception(f"Failed to start sentiment full task: {e}")
        return {
            "success": False,
            "error": str(e),
        }


def get_sentiment_full_status(task_id: str) -> Dict[str, Any]:
    """
    查询舆情分析进度 (轮询模式)。

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


def get_sentiment_full_result(task_id: str) -> Dict[str, Any]:
    """
    获取舆情分析结果。

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


def subscribe_sentiment_full(task_id: str) -> Dict[str, Any]:
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


def cancel_sentiment_full(task_id: str) -> Dict[str, Any]:
    """
    取消舆情分析任务。

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
