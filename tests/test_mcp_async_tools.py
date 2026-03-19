"""
MCP 异步工具测试

测试 Level 2/3 异步工具的 task_id 返回、状态查询、结果获取模式。
"""

import sys
import time
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp.tools.search import (
    start_search_full,
    get_search_full_status,
    get_search_full_result,
)
from mcp.tools.media import (
    start_media_full,
    get_media_full_status,
    get_media_full_result,
)
from mcp.tools.sentiment import (
    start_sentiment_full,
    get_sentiment_full_status,
    get_sentiment_full_result,
)
from mcp.tools.crawl import (
    start_crawl_data,
    get_crawl_data_status,
    get_crawl_data_result,
    start_crawl_topics,
    get_crawl_topics_status,
    get_crawl_topics_result,
    start_crawl_social,
    get_crawl_social_status,
    get_crawl_social_result,
)


class TestLevel2AsyncTools:
    """Level 2 异步工具测试"""

    def setup_method(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0

    def _report(self, name: str, passed: bool, detail: str = ""):
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {name}: {status}" + (f" - {detail}" if detail else ""))
        if passed:
            self.passed += 1
        else:
            self.failed += 1

    def _skip(self, name: str, reason: str = ""):
        status = "○ 跳过"
        print(f"  {name}: {status}" + (f" ({reason})" if reason else ""))
        self.skipped += 1

    def test_start_search_full(self):
        """测试 start_search_full 返回 task_id"""
        print("\n测试 start_search_full...")
        try:
            result = start_search_full(
                query="人工智能发展趋势",
                max_reflections=1,
                save_report=False,
                timeout=60,
            )
            self._report(
                "返回结果", isinstance(result, dict), f"type={type(result).__name__}"
            )
            if isinstance(result, dict):
                self._report("success 字段", "success" in result)
                self._report(
                    "task_id 字段", "task_id" in result, result.get("task_id", "")
                )
                self._report(
                    "status 字段", "status" in result, result.get("status", "")
                )
        except Exception as e:
            self._report("异常", False, str(e))
            self.failed += 1

    def test_get_search_full_status(self):
        """测试 get_search_full_status 状态查询"""
        print("\n测试 get_search_full_status...")
        try:
            submit_result = start_search_full(
                query="量子计算最新进展",
                max_reflections=1,
                save_report=False,
                timeout=60,
            )
            task_id = submit_result.get("task_id")
            if not task_id:
                self._report("获取 task_id", False, "start_search_full 未返回 task_id")
                return

            time.sleep(0.5)
            status_result = get_search_full_status(task_id)
            self._report("返回结果", isinstance(status_result, dict))
            if isinstance(status_result, dict):
                self._report("success 字段", "success" in status_result)
                self._report("task_id 匹配", status_result.get("task_id") == task_id)
                self._report(
                    "status 字段",
                    "status" in status_result,
                    status_result.get("status", ""),
                )
                self._report(
                    "progress 字段",
                    "progress" in status_result,
                    f"progress={status_result.get('progress')}",
                )
        except Exception as e:
            self._report("异常", False, str(e))
            self.failed += 1

    def test_get_search_full_result(self):
        """测试 get_search_full_result 结果获取"""
        print("\n测试 get_search_full_result...")
        try:
            submit_result = start_search_full(
                query="新能源汽车市场分析",
                max_reflections=1,
                save_report=False,
                timeout=60,
            )
            task_id = submit_result.get("task_id")
            if not task_id:
                self._report("获取 task_id", False)
                return

            time.sleep(0.5)
            result = get_search_full_result(task_id)
            self._report("返回结果", isinstance(result, dict))
            if isinstance(result, dict):
                self._report("success 字段", "success" in result)
                self._report("task_id 匹配", result.get("task_id") == task_id)
                self._report("status 字段", "status" in result)
        except Exception as e:
            self._report("异常", False, str(e))
            self.failed += 1

    def test_start_media_full(self):
        """测试 start_media_full"""
        print("\n测试 start_media_full...")
        try:
            result = start_media_full(
                query="特斯拉最新车型",
                max_reflections=1,
                save_report=False,
                timeout=60,
            )
            self._report("返回结果", isinstance(result, dict))
            if isinstance(result, dict):
                self._report("success 字段", "success" in result)
                self._report("task_id 字段", "task_id" in result)
        except Exception as e:
            self._report("异常", False, str(e))
            self.failed += 1

    def test_start_sentiment_full(self):
        """测试 start_sentiment_full"""
        print("\n测试 start_sentiment_full...")
        try:
            result = start_sentiment_full(
                query="国产手机品牌",
                max_reflections=1,
                save_report=False,
                timeout=60,
            )
            self._report("返回结果", isinstance(result, dict))
            if isinstance(result, dict):
                self._report("success 字段", "success" in result)
                self._report("task_id 字段", "task_id" in result)
        except Exception as e:
            self._report("异常", False, str(e))
            self.failed += 1

    def test_start_crawl_data(self):
        """测试 start_crawl_data"""
        print("\n测试 start_crawl_data...")
        try:
            result = start_crawl_data(
                keywords=["人工智能", "机器学习"],
                platforms=["xhs"],
                max_keywords=5,
                max_notes=5,
                test_mode=True,
                timeout=60,
            )
            self._report("返回结果", isinstance(result, dict))
            if isinstance(result, dict):
                self._report("success 字段", "success" in result)
                self._report("task_id 字段", "task_id" in result)
                self._report("status 字段", "status" in result)
        except Exception as e:
            self._report("异常", False, str(e))
            self.failed += 1

    def test_start_crawl_topics(self):
        """测试 start_crawl_topics"""
        print("\n测试 start_crawl_topics...")
        try:
            result = start_crawl_topics(
                keywords_count=10,
                extract_date="2026-03-19",
                timeout=60,
            )
            self._report("返回结果", isinstance(result, dict))
            if isinstance(result, dict):
                self._report("success 字段", "success" in result)
                self._report("task_id 字段", "task_id" in result)
        except Exception as e:
            self._report("异常", False, str(e))
            self.failed += 1

    def test_start_crawl_social(self):
        """测试 start_crawl_social"""
        print("\n测试 start_crawl_social...")
        try:
            result = start_crawl_social(
                platforms=["xhs"],
                max_keywords=5,
                max_notes=5,
                target_date="2026-03-19",
                test_mode=True,
                timeout=60,
            )
            self._report("返回结果", isinstance(result, dict))
            if isinstance(result, dict):
                self._report("success 字段", "success" in result)
                self._report("task_id 字段", "task_id" in result)
        except Exception as e:
            self._report("异常", False, str(e))
            self.failed += 1

    def test_task_status_fields(self):
        """测试 get_*_status 返回字段的完整性"""
        print("\n测试 task status 字段完整性...")
        try:
            result = start_search_full(
                query="测试查询",
                max_reflections=1,
                save_report=False,
                timeout=60,
            )
            task_id = result.get("task_id")
            if not task_id:
                self._report("获取 task_id", False)
                return

            time.sleep(0.5)
            status = get_search_full_status(task_id)
            if isinstance(status, dict):
                self._report("stage 字段", "stage" in status)
                self._report("started_at 字段", "started_at" in status)
                self._report("message 字段", "message" in status)
            else:
                self._report("状态返回类型", False)
        except Exception as e:
            self._report("异常", False, str(e))
            self.failed += 1


def main():
    """运行所有 Level 2 异步工具测试"""
    print("=" * 60)
    print("MCP 异步工具测试 - Level 2")
    print("=" * 60)

    test_instance = TestLevel2AsyncTools()
    test_instance.setup_method()

    test_methods = [m for m in dir(test_instance) if m.startswith("test_")]

    for test_method_name in test_methods:
        test_method = getattr(test_instance, test_method_name)
        try:
            test_method()
        except Exception as e:
            print(f"  测试执行错误: {e}")

    print()
    print("-" * 60)
    total = test_instance.passed + test_instance.failed
    print(
        f"测试结果: {test_instance.passed}/{total} 通过, {test_instance.failed}/{total} 失败, {test_instance.skipped} 跳过"
    )
    print("-" * 60)

    if test_instance.failed > 0:
        sys.exit(1)
    else:
        print("\n✓ 所有 Level 2 异步工具测试通过")
        sys.exit(0)


if __name__ == "__main__":
    main()
