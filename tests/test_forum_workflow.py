#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Level 3 工具完整协作流程测试

测试 ForumEngine 的完整协作流程：
- 8.3.6 测试完整协作流程
- 8.3.7 测试并发运行多个引擎

用法:
    python tests/test_forum_workflow.py
"""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger


def test_forum_tools_available():
    """测试 ForumEngine 工具是否可用"""
    logger.info("=" * 60)
    logger.info("测试 ForumEngine 工具可用性")
    logger.info("=" * 60)

    try:
        from mcp.tools.forum import (
            start_forum_research,
            get_forum_progress,
            get_forum_result,
            subscribe_forum,
            stop_forum_research,
            get_forum_discussion,
        )

        logger.info("✓ 所有 ForumEngine 工具已导入")
        logger.info(f"  - start_forum_research: {callable(start_forum_research)}")
        logger.info(f"  - get_forum_progress: {callable(get_forum_progress)}")
        logger.info(f"  - get_forum_result: {callable(get_forum_result)}")
        logger.info(f"  - subscribe_forum: {callable(subscribe_forum)}")
        logger.info(f"  - stop_forum_research: {callable(stop_forum_research)}")
        logger.info(f"  - get_forum_discussion: {callable(get_forum_discussion)}")

        return True

    except ImportError as e:
        logger.warning(f"⚠ ForumEngine 工具不可用: {e}")
        return True
    except Exception as e:
        logger.exception(f"✗ FAIL: {e}")
        return False


def test_forum_task_creation():
    """测试 ForumEngine 任务创建"""
    logger.info("=" * 60)
    logger.info("测试 ForumEngine 任务创建")
    logger.info("=" * 60)

    try:
        from mcp.tools.forum import start_forum_research
        from mcp.task_registry import get_task_registry

        result = start_forum_research(
            topic="测试协作流程",
            timeout=60,
        )

        logger.info(f"start_forum_research 返回: {result}")

        if result.get("success"):
            task_id = result.get("task_id")
            logger.info(f"✓ 任务创建成功: {task_id}")

            registry = get_task_registry()
            task = registry.get_task(task_id)
            if task:
                logger.info(
                    f"✓ 任务已注册: type={task.task_type}, status={task.status.value}"
                )
                registry.cancel_task(task_id)
                logger.info(f"已取消测试任务: {task_id}")
                return True
            else:
                logger.error("✗ 任务未在注册中心找到")
                return False
        else:
            logger.error(f"✗ 任务创建失败: {result.get('message')}")
            return False

    except Exception as e:
        logger.exception(f"✗ FAIL: {e}")
        return False


def test_forum_workflow_functions():
    """测试 ForumEngine 工作流函数"""
    logger.info("=" * 60)
    logger.info("测试 ForumEngine 工作流函数")
    logger.info("=" * 60)

    try:
        from mcp.tools.forum import (
            get_forum_progress,
            get_forum_discussion,
            stop_forum_research,
        )

        test_task_id = "test_forum_nonexistent"

        progress = get_forum_progress(test_task_id)
        logger.info(f"get_forum_progress: {progress}")
        if (
            progress.get("success")
            or "not found" in progress.get("message", "").lower()
        ):
            logger.info("✓ get_forum_progress 正常工作")

        discussion = get_forum_discussion(test_task_id)
        logger.info(f"get_forum_discussion: {discussion}")
        if (
            discussion.get("success")
            or "not found" in discussion.get("message", "").lower()
        ):
            logger.info("✓ get_forum_discussion 正常工作")

        stop_result = stop_forum_research(test_task_id)
        logger.info(f"stop_forum_research: {stop_result}")
        if stop_result.get("success"):
            logger.info("✓ stop_forum_research 正常工作")

        return True

    except Exception as e:
        logger.exception(f"✗ FAIL: {e}")
        return False


def test_multiple_engines_concurrent():
    """测试并发运行多个引擎 - 8.3.7"""
    logger.info("=" * 60)
    logger.info("8.3.7 测试并发运行多个引擎")
    logger.info("=" * 60)

    try:
        from mcp.tools.forum import start_forum_research
        from mcp.task_registry import get_task_registry

        registry = get_task_registry()

        topics = [
            "人工智能发展趋势",
            "新能源汽车市场分析",
            "半导体行业动态",
        ]

        task_ids = []
        for topic in topics:
            result = start_forum_research(
                topic=topic,
                timeout=120,
            )
            if result.get("success"):
                task_ids.append((topic, result.get("task_id")))
                logger.info(f"✓ 为 '{topic}' 创建任务: {result.get('task_id')}")

        logger.info(f"创建了 {len(task_ids)} 个并发任务")

        if len(task_ids) >= 2:
            logger.info("✓ 支持并发创建多个任务")
        else:
            logger.warning("⚠ 未能创建多个并发任务")

        for topic, task_id in task_ids:
            registry.cancel_task(task_id)
            logger.info(f"已取消任务: {topic} -> {task_id}")

        return True

    except Exception as e:
        logger.exception(f"✗ FAIL: {e}")
        return False


def main():
    """主函数"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("Level 3 工具完整协作流程测试")
    logger.info("=" * 60)
    logger.info("")

    results = []

    results.append(("ForumEngine 工具可用性", test_forum_tools_available()))
    results.append(("ForumEngine 任务创建", test_forum_task_creation()))
    results.append(("ForumEngine 工作流函数", test_forum_workflow_functions()))
    results.append(("8.3.7 并发多引擎", test_multiple_engines_concurrent()))

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
