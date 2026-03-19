"""
Report Generation Tool

Wraps ReportEngine for MCP access.
"""

import json
import os
import time
import concurrent.futures
from typing import Dict, Any, Optional
from loguru import logger


REPORT_ENGINE_API = "http://localhost:5000/api/report"


def generate_report(
    topic: str,
    template: str = None,
    wait_for_completion: bool = True,
    timeout: int = 600,
    **kwargs,
) -> Dict[str, Any]:
    """
    生成分析报告。

    Args:
        topic: 报告主题
        template: 模板名称（可选）
        wait_for_completion: 是否等待报告生成完成
        timeout: 超时时间（秒）
        **kwargs: 其他参数

    Returns:
        报告生成结果字典
    """
    logger.info(
        f"MCP generate_report: topic={topic}, template={template}, wait={wait_for_completion}"
    )

    try:
        import requests

        response = requests.post(
            f"{REPORT_ENGINE_API}/generate",
            json={"query": topic, "custom_template": template or ""},
            timeout=30,
        )

        if response.status_code != 200:
            return {
                "success": False,
                "error": f"Report API returned {response.status_code}: {response.text}",
                "topic": topic,
            }

        result = response.json()

        if not result.get("success"):
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "topic": topic,
            }

        task_id = result.get("task_id")
        stream_url = result.get("stream_url")

        if not wait_for_completion:
            return {
                "success": True,
                "topic": topic,
                "task_id": task_id,
                "status": "pending",
                "stream_url": stream_url,
                "message": "Report generation started",
            }

        status_url = f"{REPORT_ENGINE_API}/progress/{task_id}"
        start_time = time.time()

        while time.time() - start_time < timeout:
            status_response = requests.get(status_url, timeout=10)
            status_data = status_response.json()

            task = status_data.get("task", {})
            status = task.get("status")

            logger.info(f"Report generation status: {status}")

            if status == "completed":
                result_url = f"{REPORT_ENGINE_API}/result/{task_id}/json"
                result_response = requests.get(result_url, timeout=30)
                result_data = result_response.json()

                return {
                    "success": True,
                    "topic": topic,
                    "task_id": task_id,
                    "status": "completed",
                    "html_content": result_data.get("html_content", ""),
                    "report_file": task.get("report_file_path", ""),
                    "message": "Report generation completed",
                }

            elif status == "error":
                return {
                    "success": False,
                    "error": task.get("error_message", "Report generation failed"),
                    "topic": topic,
                    "task_id": task_id,
                    "status": "error",
                }

            time.sleep(5)

        return {
            "success": False,
            "error": f"Report generation timeout after {timeout} seconds",
            "topic": topic,
            "task_id": task_id,
            "status": "timeout",
        }

    except ImportError:
        logger.warning("requests library not available, using direct ReportAgent")
        return _generate_report_direct(topic, template, **kwargs)
    except Exception as e:
        logger.exception(f"Report generation error: {e}")
        return {"success": False, "error": str(e), "topic": topic}


def _generate_report_direct(
    topic: str, template: str = None, **kwargs
) -> Dict[str, Any]:
    """
    直接调用 ReportAgent 生成报告（无 SSE 流式）。

    Args:
        topic: 报告主题
        template: 模板名称
        **kwargs: 其他参数

    Returns:
        报告结果
    """
    try:
        from ReportEngine.flask_interface import (
            initialize_report_engine,
            check_engines_ready,
            ReportTask,
            run_report_generation,
        )
        import threading

        if not initialize_report_engine():
            return {"success": False, "error": "Report Engine initialization failed"}

        check_result = check_engines_ready()
        if not check_result["ready"]:
            return {
                "success": False,
                "error": "Input files not ready",
                "missing_files": check_result.get("missing_files", []),
            }

        task_id = f"mcp_report_{int(time.time())}"
        task = ReportTask(topic, task_id, template or "")

        thread = threading.Thread(
            target=run_report_generation,
            args=(task, topic, template or ""),
            daemon=True,
        )
        thread.start()

        thread.join(timeout=600)

        if task.status == "completed":
            return {
                "success": True,
                "topic": topic,
                "task_id": task_id,
                "status": "completed",
                "html_content": task.html_content,
                "report_file": task.report_file_path,
                "message": "Report generation completed",
            }
        elif task.status == "error":
            return {
                "success": False,
                "error": task.error_message,
                "topic": topic,
                "task_id": task_id,
                "status": "error",
            }
        else:
            return {
                "success": True,
                "topic": topic,
                "task_id": task_id,
                "status": task.status,
                "message": "Report generation in progress",
            }

    except Exception as e:
        logger.exception(f"Direct report generation error: {e}")
        return {"success": False, "error": str(e), "topic": topic}


def get_report_status(task_id: str, **kwargs) -> Dict[str, Any]:
    """
    查询报告生成状态。

    Args:
        task_id: 任务ID
        **kwargs: 其他参数

    Returns:
        状态信息
    """
    logger.info(f"MCP get_report_status: task_id={task_id}")

    try:
        import requests

        response = requests.get(f"{REPORT_ENGINE_API}/progress/{task_id}", timeout=10)

        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "task": data.get("task", {}),
                "message": f"Task status: {data.get('task', {}).get('status', 'unknown')}",
            }
        else:
            return {
                "success": False,
                "error": f"API returned {response.status_code}",
                "task_id": task_id,
            }

    except ImportError:
        return {
            "success": False,
            "error": "requests library not available",
            "task_id": task_id,
        }
    except Exception as e:
        logger.exception(f"Get status error: {e}")
        return {"success": False, "error": str(e), "task_id": task_id}


def get_report_result(task_id: str, format: str = "html", **kwargs) -> Dict[str, Any]:
    """
    获取报告结果。

    Args:
        task_id: 任务ID
        format: 返回格式 (html/json)
        **kwargs: 其他参数

    Returns:
        报告结果
    """
    logger.info(f"MCP get_report_result: task_id={task_id}, format={format}")

    try:
        import requests

        if format == "html":
            url = f"{REPORT_ENGINE_API}/result/{task_id}"
        else:
            url = f"{REPORT_ENGINE_API}/result/{task_id}/json"

        response = requests.get(url, timeout=30)

        if response.status_code == 200:
            if format == "html":
                return {
                    "success": True,
                    "task_id": task_id,
                    "html_content": response.text,
                    "message": "HTML content retrieved",
                }
            else:
                data = response.json()
                return {
                    "success": True,
                    "task_id": task_id,
                    "task": data.get("task", {}),
                    "html_content": data.get("html_content", ""),
                    "message": "JSON result retrieved",
                }
        else:
            return {
                "success": False,
                "error": f"API returned {response.status_code}",
                "task_id": task_id,
            }

    except ImportError:
        return {
            "success": False,
            "error": "requests library not available",
            "task_id": task_id,
        }
    except Exception as e:
        logger.exception(f"Get result error: {e}")
        return {"success": False, "error": str(e), "task_id": task_id}
