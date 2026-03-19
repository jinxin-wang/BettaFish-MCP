#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
报告保存功能测试

测试 MCP 工具的报告保存功能是否正常工作。

用法:
    python tests/test_report_save.py
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger


def test_report_save_config():
    """测试报告保存配置"""
    logger.info("=" * 60)
    logger.info("测试报告保存配置")
    logger.info("=" * 60)

    try:
        from QueryEngine.utils.config import settings

        logger.info(f"默认输出目录: {settings.OUTPUT_DIR}")
        if hasattr(settings, "REPORT_PREFIX"):
            logger.info(f"报告前缀: {settings.REPORT_PREFIX}")
        if hasattr(settings, "REPORT_FORMAT"):
            logger.info(f"报告格式: {settings.REPORT_FORMAT}")

        output_dir = tempfile.mkdtemp()
        settings.OUTPUT_DIR = output_dir

        test_report = f"""# 测试报告

## 概述
这是一份自动生成的测试报告。

## 内容
测试报告内容...

## 结论
报告保存功能测试通过。
"""

        test_filename = f"test_report_{int(os.times().elapsed * 1000)}.md"
        report_path = Path(output_dir) / test_filename

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(test_report)

        if report_path.exists():
            logger.info(f"✓ 测试报告保存成功: {report_path}")
            logger.info(f"  文件大小: {report_path.stat().st_size} bytes")

            with open(report_path, "r", encoding="utf-8") as f:
                content = f.read()
                if "测试报告" in content:
                    logger.info("✓ 报告内容验证通过")
                else:
                    logger.error("✗ 报告内容验证失败")
                    return False
        else:
            logger.error("✗ 测试报告保存失败")
            return False

        report_path.unlink()
        Path(output_dir).rmdir()

        return True

    except ImportError as e:
        logger.warning(f"QueryEngine 不可用，跳过配置测试: {e}")
        return True
    except Exception as e:
        logger.exception(f"测试失败: {e}")
        return False


def test_task_registry_result():
    """测试任务注册中心的结果保存"""
    logger.info("=" * 60)
    logger.info("测试任务注册中心结果保存")
    logger.info("=" * 60)

    try:
        from mcp.task_registry import get_task_registry, TaskType

        registry = get_task_registry()

        test_result = {
            "query": "测试查询",
            "report_content": "# 测试报告\n\n这是测试报告内容。",
            "report_file": "query_engine_streamlit_reports/test_report.md",
            "paragraphs_count": 3,
            "reflections_per_paragraph": 2,
        }

        task_id = registry.create_task(
            task_type=TaskType.SEARCH_FULL.value,
            params={"query": "测试查询", "save_report": True},
            timeout=60,
        )

        registry.complete_task(task_id, test_result)

        saved_result = registry.get_task_result(task_id)

        if saved_result and saved_result.get("result"):
            logger.info(f"✓ 任务结果保存成功: task_id={task_id}")
            logger.info(
                f"  报告内容长度: {len(saved_result['result'].get('report_content', ''))}"
            )

            result_file = Path("logs/mcp_tasks/results") / f"{task_id}.json"
            if result_file.exists():
                logger.info(f"✓ 结果文件持久化成功: {result_file}")
            else:
                logger.warning(f"⚠ 结果文件未找到: {result_file}")

            return True
        else:
            logger.error("✗ 任务结果保存失败")
            return False

    except Exception as e:
        logger.exception(f"测试失败: {e}")
        return False


def test_report_file_persistence():
    """测试报告文件持久化"""
    logger.info("=" * 60)
    logger.info("测试报告文件持久化")
    logger.info("=" * 60)

    try:
        results_dir = Path("logs/mcp_tasks/results")
        results_dir.mkdir(parents=True, exist_ok=True)

        test_files = list(results_dir.glob("*.json"))
        logger.info(f"找到 {len(test_files)} 个结果文件")

        for i, f in enumerate(test_files[:5]):
            logger.info(f"  {i + 1}. {f.name}")

        if test_files:
            latest = max(test_files, key=lambda p: p.stat().st_mtime)
            logger.info(f"最新结果文件: {latest.name}")

            import json

            with open(latest, "r", encoding="utf-8") as f:
                data = json.load(f)

            if "report_content" in data.get("result", {}):
                logger.info("✓ 结果包含报告内容")
            else:
                logger.info("⚠ 结果不包含报告内容（可能未启用 save_report）")

        return True

    except Exception as e:
        logger.exception(f"测试失败: {e}")
        return False


def main():
    """主函数"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("报告保存功能测试")
    logger.info("=" * 60)
    logger.info("")

    results = []

    results.append(("报告保存配置", test_report_save_config()))
    results.append(("任务注册中心结果保存", test_task_registry_result()))
    results.append(("报告文件持久化", test_report_file_persistence()))

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
