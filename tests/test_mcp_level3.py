"""
MCP Level 3 工具测试

测试 ForumEngine 和 ReportEngine 异步工具。
"""

import sys
import time
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp.tools.forum import (
    start_forum_research,
    get_forum_progress,
    get_forum_result,
    subscribe_forum,
    stop_forum_research,
    get_forum_discussion,
    start_report,
    get_report_status as forum_get_report_status,
    get_report_result as forum_get_report_result,
)


class TestLevel3Tools:
    """Level 3 异步工具测试"""

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

    def test_start_forum_research(self):
        """测试 start_forum_research 返回正确的 task_id"""
        print("\n测试 start_forum_research...")
        try:
            result = start_forum_research(
                topic="人工智能发展趋势研究",
                engines=["query"],
                timeout=30,
            )
            self._report("返回结果", isinstance(result, dict))
            if isinstance(result, dict):
                self._report("success 字段", "success" in result)
                self._report("task_id 字段", "task_id" in result)
                self._report("status 字段", "status" in result)
                if result.get("task_id"):
                    self._report("task_id 格式", result["task_id"].startswith("forum_"))
        except Exception as e:
            self._report("异常", False, str(e))
            self.failed += 1

    def test_get_forum_progress(self):
        """测试 get_forum_progress 状态查询"""
        print("\n测试 get_forum_progress...")
        try:
            submit_result = start_forum_research(
                topic="测试论坛研究",
                engines=["query"],
                timeout=30,
            )
            task_id = submit_result.get("task_id")
            if not task_id:
                self._report("获取 task_id", False)
                return

            time.sleep(0.2)
            progress = get_forum_progress(task_id)
            self._report("返回结果", isinstance(progress, dict))
            if isinstance(progress, dict):
                self._report("success 字段", "success" in progress)
                self._report("task_id 匹配", progress.get("task_id") == task_id)
        except Exception as e:
            self._report("异常", False, str(e))
            self.failed += 1

    def test_get_forum_result(self):
        """测试 get_forum_result 结果获取"""
        print("\n测试 get_forum_result...")
        try:
            submit_result = start_forum_research(
                topic="测试论坛结果",
                engines=["query"],
                timeout=30,
            )
            task_id = submit_result.get("task_id")
            if not task_id:
                self._report("获取 task_id", False)
                return

            time.sleep(0.2)
            result = get_forum_result(task_id)
            self._report("返回结果", isinstance(result, dict))
            if isinstance(result, dict):
                self._report("success 字段", "success" in result)
                self._report("task_id 匹配", result.get("task_id") == task_id)
        except Exception as e:
            self._report("异常", False, str(e))
            self.failed += 1

    def test_subscribe_forum(self):
        """测试 subscribe_forum SSE 订阅"""
        print("\n测试 subscribe_forum...")
        try:
            submit_result = start_forum_research(
                topic="测试订阅",
                engines=["query"],
                timeout=30,
            )
            task_id = (
                submit_result.get("task_id")
                if isinstance(submit_result, dict)
                else None
            )
            if not task_id:
                self._report("获取 task_id", False, str(submit_result)[:100])
                time.sleep(2)
                return

            time.sleep(1.0)
            result = subscribe_forum(task_id)
            self._report("返回结果", isinstance(result, dict))
            if isinstance(result, dict):
                self._report("success 字段", "success" in result)
                self._report("stream_url 字段", "stream_url" in result)
        except Exception as e:
            self._report("异常", False, str(e))
            self.failed += 1

    def test_stop_forum_research(self):
        """测试 stop_forum_research 停止任务"""
        print("\n测试 stop_forum_research...")
        try:
            submit_result = start_forum_research(
                topic="测试停止",
                engines=["query"],
                timeout=30,
            )
            task_id = (
                submit_result.get("task_id")
                if isinstance(submit_result, dict)
                else None
            )
            if not task_id:
                self._report("获取 task_id", False, str(submit_result)[:100])
                time.sleep(2)
                return

            time.sleep(1.0)
            stop_result = stop_forum_research(task_id)
            self._report("返回结果", isinstance(stop_result, dict))
            if isinstance(stop_result, dict):
                self._report("success 字段", "success" in stop_result)
        except Exception as e:
            self._report("异常", False, str(e))
            self.failed += 1

    def test_stop_forum_research(self):
        """测试 stop_forum_research 停止任务"""
        print("\n测试 stop_forum_research...")
        try:
            submit_result = start_forum_research(
                topic="测试停止",
                engines=["query"],
                timeout=30,
            )
            task_id = (
                submit_result.get("task_id")
                if isinstance(submit_result, dict)
                else None
            )
            if not task_id:
                self._report("获取 task_id", False, str(submit_result))
                return

            time.sleep(0.8)
            stop_result = stop_forum_research(task_id)
            self._report("返回结果", isinstance(stop_result, dict))
            if isinstance(stop_result, dict):
                self._report("success 字段", "success" in stop_result)
        except Exception as e:
            self._report("异常", False, str(e))
            self.failed += 1

    def test_get_forum_discussion(self):
        """测试 get_forum_discussion 获取讨论内容"""
        print("\n测试 get_forum_discussion...")
        try:
            submit_result = start_forum_research(
                topic="测试讨论",
                engines=["query"],
                timeout=30,
            )
            task_id = submit_result.get("task_id")
            if not task_id:
                self._report("获取 task_id", False)
                return

            time.sleep(0.5)
            result = get_forum_discussion(task_id)
            self._report("返回结果", isinstance(result, dict))
            if isinstance(result, dict):
                self._report("success 字段", "success" in result)
        except Exception as e:
            self._report("异常", False, str(e))
            self.failed += 1

    def test_start_report(self):
        """测试 start_report 报告生成"""
        print("\n测试 start_report...")
        try:
            result = start_report(
                topic="测试报告",
                template="standard",
                timeout=30,
            )
            self._report("返回结果", isinstance(result, dict))
            if isinstance(result, dict):
                self._report("success 字段", "success" in result)
                self._report("task_id 字段", "task_id" in result)
        except Exception as e:
            self._report("异常", False, str(e))
            self.failed += 1

    def test_get_report_status(self):
        """测试 get_report_status"""
        print("\n测试 get_report_status...")
        try:
            submit_result = start_report(topic="测试状态报告", timeout=30)
            task_id = submit_result.get("task_id")
            if not task_id:
                self._report("获取 task_id", False)
                return

            time.sleep(0.2)
            status = forum_get_report_status(task_id)
            self._report("返回结果", isinstance(status, dict))
            if isinstance(status, dict):
                self._report("success 字段", "success" in status)
                self._report("task_id 匹配", status.get("task_id") == task_id)
        except Exception as e:
            self._report("异常", False, str(e))
            self.failed += 1

    def test_get_report_result(self):
        """测试 get_report_result"""
        print("\n测试 get_report_result...")
        try:
            submit_result = start_report(topic="测试结果报告", timeout=30)
            task_id = submit_result.get("task_id")
            if not task_id:
                self._report("获取 task_id", False)
                return

            time.sleep(0.2)
            result = forum_get_report_result(task_id)
            self._report("返回结果", isinstance(result, dict))
            if isinstance(result, dict):
                self._report("success 字段", "success" in result)
                self._report("task_id 匹配", result.get("task_id") == task_id)
        except Exception as e:
            self._report("异常", False, str(e))
            self.failed += 1


def main():
    """运行所有 Level 3 工具测试"""
    print("=" * 60)
    print("MCP 工具测试 - Level 3 (ForumEngine & ReportEngine)")
    print("=" * 60)

    test_instance = TestLevel3Tools()
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
        print("\n✓ 所有 Level 3 工具测试通过")
        sys.exit(0)


if __name__ == "__main__":
    main()
