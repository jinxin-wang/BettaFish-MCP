"""
MCP 工具测试

测试 Level 1 / Level 2 / Level 3 工具的可用性。
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp.tools.search import search_news
from mcp.tools.media import analyze_media
from mcp.tools.sentiment import query_sentiment
from mcp.tools.crawl import check_spider_status


class TestLevel1Tools:
    """Level 1 同步工具测试"""

    def setup_method(self):
        """每个测试方法运行前的准备"""
        self.passed = 0
        self.failed = 0

    def _report(self, name: str, passed: bool, detail: str = ""):
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {name}: {status}" + (f" - {detail}" if detail else ""))
        if passed:
            self.passed += 1
        else:
            self.failed += 1

    def test_search_news(self):
        """测试 search_news 工具"""
        print("\n测试 search_news...")
        try:
            result = search_news(query="人工智能", max_results=5)
            self._report(
                "返回结果",
                isinstance(result, dict),
                f"type={type(result).__name__}",
            )
            if isinstance(result, dict):
                self._report("success 字段", "success" in result)
                self._report("results 字段", "results" in result)
        except Exception as e:
            self._report("异常", False, str(e))
            self.failed += 1

    def test_analyze_media(self):
        """测试 analyze_media 工具"""
        print("\n测试 analyze_media...")
        try:
            result = analyze_media(query="特斯拉新车发布", max_results=5)
            self._report(
                "返回结果",
                isinstance(result, dict),
                f"type={type(result).__name__}",
            )
            if isinstance(result, dict):
                self._report("success 字段", "success" in result)
        except Exception as e:
            self._report("异常", False, str(e))
            self.failed += 1

    def test_query_sentiment(self):
        """测试 query_sentiment 工具"""
        print("\n测试 query_sentiment...")
        try:
            result = query_sentiment(keyword="新能源", days=7, max_results=10)
            self._report(
                "返回结果",
                isinstance(result, dict),
                f"type={type(result).__name__}",
            )
            if isinstance(result, dict):
                self._report("success 字段", "success" in result)
        except Exception as e:
            self._report("异常", False, str(e))
            self.failed += 1

    def test_check_spider_status(self):
        """测试 check_spider_status 工具"""
        print("\n测试 check_spider_status...")
        try:
            result = check_spider_status()
            self._report(
                "返回结果",
                isinstance(result, dict),
                f"type={type(result).__name__}",
            )
            if isinstance(result, dict):
                self._report("success 字段", "success" in result)
                self._report("status 字段", "status" in result)
        except Exception as e:
            self._report("异常", False, str(e))
            self.failed += 1


def main():
    """运行所有 MCP 工具测试"""
    print("=" * 60)
    print("MCP 工具测试 - Level 1")
    print("=" * 60)

    test_instance = TestLevel1Tools()
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
        print("\n✓ 所有 Level 1 工具测试通过")
        sys.exit(0)


if __name__ == "__main__":
    main()
