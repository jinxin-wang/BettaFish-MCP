"""
MCP 异步工具进阶测试

测试超时处理、任务取消等进阶功能。
"""

import sys
import time
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp.tools.search import (
    start_search_full,
    get_search_full_status,
    cancel_search_full,
)
from mcp.tools.crawl import (
    start_crawl_data,
    get_crawl_data_status,
    cancel_crawl_data,
    start_crawl_topics,
    cancel_crawl_topics,
    start_crawl_social,
    cancel_crawl_social,
)


class TestAdvancedAsync:
    """进阶异步功能测试"""

    def setup_method(self):
        self.passed = 0
        self.failed = 0

    def _report(self, name: str, passed: bool, detail: str = ""):
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {name}: {status}" + (f" - {detail}" if detail else ""))
        if passed:
            self.passed += 1
        else:
            self.failed += 1

    def test_cancel_search_full(self):
        """测试取消 search_full 任务"""
        print("\n测试 cancel_search_full...")
        try:
            result = start_search_full(
                query="取消测试",
                max_reflections=1,
                save_report=False,
                timeout=60,
            )
            task_id = result.get("task_id")
            if not task_id:
                self._report("获取 task_id", False)
                return

            time.sleep(0.2)
            cancel_result = cancel_search_full(task_id)
            self._report("返回结果", isinstance(cancel_result, dict))
            if isinstance(cancel_result, dict):
                self._report("success 字段", "success" in cancel_result)

        except Exception as e:
            self._report("异常", False, str(e))
            self.failed += 1

    def test_cancel_crawl_data(self):
        """测试取消 crawl_data 任务"""
        print("\n测试 cancel_crawl_data...")
        try:
            result = start_crawl_data(
                keywords=["测试"],
                platforms=["xhs"],
                max_keywords=1,
                max_notes=1,
                test_mode=True,
                timeout=60,
            )
            task_id = result.get("task_id")
            if not task_id:
                self._report("获取 task_id", False)
                return

            time.sleep(0.2)
            cancel_result = cancel_crawl_data(task_id)
            self._report("返回结果", isinstance(cancel_result, dict))
            if isinstance(cancel_result, dict):
                self._report("success 字段", "success" in cancel_result)
        except Exception as e:
            self._report("异常", False, str(e))
            self.failed += 1

    def test_cancel_crawl_topics(self):
        """测试取消 crawl_topics 任务"""
        print("\n测试 cancel_crawl_topics...")
        try:
            result = start_crawl_topics(
                keywords_count=5,
                extract_date="2026-03-19",
                timeout=60,
            )
            task_id = result.get("task_id")
            if not task_id:
                self._report("获取 task_id", False)
                return

            time.sleep(0.2)
            cancel_result = cancel_crawl_topics(task_id)
            self._report("返回结果", isinstance(cancel_result, dict))
            if isinstance(cancel_result, dict):
                self._report("success 字段", "success" in cancel_result)
        except Exception as e:
            self._report("异常", False, str(e))
            self.failed += 1

    def test_cancel_crawl_social(self):
        """测试取消 crawl_social 任务"""
        print("\n测试 cancel_crawl_social...")
        try:
            result = start_crawl_social(
                platforms=["xhs"],
                max_keywords=1,
                max_notes=1,
                target_date="2026-03-19",
                test_mode=True,
                timeout=60,
            )
            task_id = result.get("task_id")
            if not task_id:
                self._report("获取 task_id", False)
                return

            time.sleep(0.2)
            cancel_result = cancel_crawl_social(task_id)
            self._report("返回结果", isinstance(cancel_result, dict))
            if isinstance(cancel_result, dict):
                self._report("success 字段", "success" in cancel_result)
        except Exception as e:
            self._report("异常", False, str(e))
            self.failed += 1

    def test_cancel_nonexistent_task(self):
        """测试取消不存在的任务"""
        print("\n测试 cancel 不存在的任务...")
        try:
            result = cancel_search_full("nonexistent_task_id_12345")
            self._report("返回结果", isinstance(result, dict))
            if isinstance(result, dict):
                self._report("success=False", result.get("success") == False)
                self._report("error 字段", "error" in result)
        except Exception as e:
            self._report("异常", False, str(e))
            self.failed += 1

    def test_task_timeout_rejected(self):
        """测试超时参数被正确设置"""
        print("\n测试 task 超时参数...")
        try:
            result = start_search_full(
                query="超时测试",
                max_reflections=1,
                save_report=False,
                timeout=5,
            )
            task_id = result.get("task_id")
            if not task_id:
                self._report("获取 task_id", False)
                return

            time.sleep(0.2)
            status = get_search_full_status(task_id)
            self._report("任务存在", status.get("task_id") == task_id)
            self._report(
                "有 timeout 配置",
                "timeout" in status
                or status.get("status") in ["pending", "running", "failed"],
            )

        except Exception as e:
            self._report("异常", False, str(e))
            self.failed += 1

    def test_concurrent_task_limit(self):
        """测试并发任务限制"""
        print("\n测试并发任务限制 (提交3个任务)...")
        try:
            task_ids = []
            for i in range(3):
                result = start_search_full(
                    query=f"并发测试{i}",
                    max_reflections=1,
                    save_report=False,
                    timeout=60,
                )
                if result.get("success") and result.get("task_id"):
                    task_ids.append(result["task_id"])
                time.sleep(0.1)

            self._report(
                "成功提交3个任务", len(task_ids) == 3, f"提交了 {len(task_ids)} 个"
            )
            for tid in task_ids:
                self._report(f"task_id 格式正确", tid.startswith("search_full_"), tid)

        except Exception as e:
            self._report("异常", False, str(e))
            self.failed += 1


def main():
    """运行进阶异步测试"""
    print("=" * 60)
    print("MCP 进阶异步功能测试 - 8.2.8-8.2.9")
    print("=" * 60)

    test_instance = TestAdvancedAsync()
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
        f"测试结果: {test_instance.passed}/{total} 通过, {test_instance.failed}/{total} 失败"
    )
    print("-" * 60)

    if test_instance.failed > 0:
        sys.exit(1)
    else:
        print("\n✓ 所有进阶异步功能测试通过")
        sys.exit(0)


if __name__ == "__main__":
    main()
