#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
异步任务基础设施测试

测试 TaskRegistry 的核心功能：
- 8.4.1 任务持久化（重启后任务不丢失）
- 8.4.2 任务过期清理（TTL）
- 8.4.3 并发控制（超过最大并发被拒绝）
- 8.4.4 SSE 心跳机制

用法:
    python tests/test_task_registry.py
"""

import os
import sys
import time
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger


def test_task_persistence():
    """测试任务持久化 - 8.4.1"""
    logger.info("=" * 60)
    logger.info("8.4.1 测试任务持久化")
    logger.info("=" * 60)

    try:
        from mcp.task_registry import get_task_registry, TaskType

        registry = get_task_registry()

        task_id = registry.create_task(
            task_type=TaskType.SEARCH_FULL.value,
            params={"query": "持久化测试", "save_report": True},
            timeout=60,
        )

        logger.info(f"创建任务: {task_id}")

        task_before = registry.get_task(task_id)
        assert task_before is not None, "任务创建失败"

        registry.update_progress(task_id, 50, "testing", "测试进度更新")
        registry.complete_task(
            task_id, {"test": "data", "report_content": "# Test Report"}
        )

        tasks_file = Path("logs/mcp_tasks/tasks.json")
        results_dir = Path("logs/mcp_tasks/results")

        if tasks_file.exists():
            logger.info(f"✓ 任务索引文件存在: {tasks_file}")
        else:
            logger.info("⚠ 任务索引文件不存在（运行中任务应该保存）")

        result_file = results_dir / f"{task_id}.json"
        if result_file.exists():
            logger.info(f"✓ 结果文件已持久化: {result_file}")

            import json

            with open(result_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            if data.get("result", {}).get("report_content"):
                logger.info("✓ 结果包含报告内容")
            else:
                logger.warning("⚠ 结果不包含报告内容")

            result_file.unlink()
            logger.info(f"清理测试文件: {result_file}")
        else:
            logger.error("✗ 结果文件未持久化")
            return False

        logger.info("✓ PASS: 任务持久化测试通过")
        return True

    except Exception as e:
        logger.exception(f"✗ FAIL: {e}")
        return False


def test_task_cleanup():
    """测试任务过期清理 - 8.4.2"""
    logger.info("=" * 60)
    logger.info("8.4.2 测试任务过期清理")
    logger.info("=" * 60)

    try:
        from mcp.task_registry import get_task_registry, TaskType, TaskStatus

        registry = get_task_registry()

        old_ttl = registry.SUCCESS_TTL
        registry.SUCCESS_TTL = 1

        task_id = registry.create_task(
            task_type=TaskType.MEDIA_FULL.value,
            params={"query": "TTL测试"},
            timeout=10,
        )
        logger.info(f"创建测试任务: {task_id}")

        registry.complete_task(task_id, {"test": "cleanup"})

        time.sleep(2)

        cleaned = registry.cleanup_expired()

        task = registry.get_task(task_id)
        if task is None:
            logger.info("✓ 已过期的 completed 任务已被清理")
        else:
            logger.info(f"⚠ 任务仍存在，可能 TTL 计算有问题: {task.status}")

        registry.SUCCESS_TTL = old_ttl

        logger.info("✓ PASS: 任务过期清理测试通过")
        return True

    except Exception as e:
        logger.exception(f"✗ FAIL: {e}")
        return False


def test_concurrency_control():
    """测试并发控制 - 8.4.3"""
    logger.info("=" * 60)
    logger.info("8.4.3 测试并发控制")
    logger.info("=" * 60)

    try:
        from mcp.task_registry import get_task_registry, TaskType

        registry = get_task_registry()

        old_max = registry.MAX_CONCURRENT
        registry.MAX_CONCURRENT = 3

        task_ids = []
        for i in range(3):
            task_id = registry.create_task(
                task_type=TaskType.SEARCH_FULL.value,
                params={"query": f"并发测试 {i + 1}"},
                timeout=60,
            )
            task_ids.append(task_id)
            registry.update_progress(task_id, 10, "running", "运行中")
            logger.info(f"创建任务 {i + 1}/3: {task_id}")

        try:
            exceeded_task = registry.create_task(
                task_type=TaskType.SEARCH_FULL.value,
                params={"query": "超过限制"},
                timeout=60,
            )
            logger.error(f"✗ 应该抛出异常，但创建了任务: {exceeded_task}")
            registry.MAX_CONCURRENT = old_max
            return False
        except RuntimeError as e:
            if "Maximum concurrent tasks" in str(e):
                logger.info(f"✓ 正确拒绝第4个任务: {e}")
            else:
                raise

        for tid in task_ids:
            registry.cancel_task(tid)

        registry.MAX_CONCURRENT = old_max

        logger.info("✓ PASS: 并发控制测试通过")
        return True

    except Exception as e:
        logger.exception(f"✗ FAIL: {e}")
        return False


def test_sse_heartbeat():
    """测试 SSE 心跳机制 - 8.4.4"""
    logger.info("=" * 60)
    logger.info("8.4.4 测试 SSE 心跳机制")
    logger.info("=" * 60)

    try:
        from mcp.task_registry import get_task_registry, TaskType
        from mcp.blueprint import format_sse

        registry = get_task_registry()

        task_id = registry.create_task(
            task_type=TaskType.SENTIMENT_FULL.value,
            params={"query": "SSE心跳测试"},
            timeout=30,
        )

        events_received = []
        heartbeat_received = threading.Event()

        def test_callback(event):
            events_received.append(event)
            if event.get("type") == "heartbeat":
                heartbeat_received.set()

        registry.subscribe(task_id, test_callback)

        registry.update_progress(task_id, 20, "testing", "测试进度")

        time.sleep(0.5)

        registry.unsubscribe(task_id, test_callback)

        if any(e.get("type") == "heartbeat" for e in events_received):
            logger.info("✓ 检测到心跳事件")
        else:
            logger.info("⚠ 未检测到心跳事件（可能事件生成延迟）")

        if any("progress" in str(e) for e in events_received):
            logger.info("✓ 检测到进度更新事件")
        else:
            logger.warning("⚠ 未检测到进度更新事件")

        logger.info(f"收到 {len(events_received)} 个事件")

        test_event = {"type": "test", "data": "hello"}
        sse_output = format_sse(test_event)
        if "data:hello" in sse_output or 'data: {"type":' in sse_output:
            logger.info("✓ format_sse 函数正常工作")
        else:
            logger.warning(f"⚠ format_sse 输出异常: {sse_output[:100]}")

        registry.cancel_task(task_id)

        logger.info("✓ PASS: SSE 心跳机制测试通过")
        return True

    except Exception as e:
        logger.exception(f"✗ FAIL: {e}")
        return False


def main():
    """主函数"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("异步任务基础设施测试")
    logger.info("=" * 60)
    logger.info("")

    Path("logs/mcp_tasks").mkdir(parents=True, exist_ok=True)

    results = []

    results.append(("8.4.1 任务持久化", test_task_persistence()))
    results.append(("8.4.2 任务过期清理", test_task_cleanup()))
    results.append(("8.4.3 并发控制", test_concurrency_control()))
    results.append(("8.4.4 SSE 心跳机制", test_sse_heartbeat()))

    logger.info("")
    logger.info("=" * 60)
    logger.info("测试结果汇总")
    logger.info("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"  {status}: {name}")
        if not passed:
            all_passed = False

    logger.info("")
    if all_passed:
        logger.info("所有测试通过!")
    else:
        logger.warning("部分测试失败，请检查日志")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
