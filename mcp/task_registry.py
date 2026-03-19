"""
MCP 异步任务注册中心

提供异步任务的创建、管理、查询和清理功能。
"""

import json
import os
import threading
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from loguru import logger


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    SEARCH_FULL = "search_full"
    MEDIA_FULL = "media_full"
    SENTIMENT_FULL = "sentiment_full"
    CRAWL_FULL = "crawl_full"
    CRAWL_DATA = "crawl_data"
    CRAWL_TOPICS = "crawl_topics"
    CRAWL_SOCIAL = "crawl_social"
    FORUM_RESEARCH = "forum_research"
    REPORT = "report"


class TaskInfo:
    """任务信息"""

    def __init__(
        self,
        task_id: str,
        task_type: str,
        params: Dict[str, Any],
        timeout: int = 600,
    ):
        self.task_id = task_id
        self.task_type = task_type
        self.params = params
        self.timeout = timeout
        self.status = TaskStatus.PENDING
        self.progress = 0
        self.stage = ""
        self.stage_detail = ""
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.created_at = datetime.now().isoformat()
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self._lock = threading.Lock()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": self.status.value,
            "progress": self.progress,
            "stage": self.stage,
            "stage_detail": self.stage_detail,
            "result": self.result,
            "error": self.error,
            "params": self.params,
            "timeout": self.timeout,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskInfo":
        task = cls(
            task_id=data["task_id"],
            task_type=data["task_type"],
            params=data.get("params", {}),
            timeout=data.get("timeout", 600),
        )
        task.status = TaskStatus(data.get("status", "pending"))
        task.progress = data.get("progress", 0)
        task.stage = data.get("stage", "")
        task.stage_detail = data.get("stage_detail", "")
        task.result = data.get("result")
        task.error = data.get("error")
        task.created_at = data.get("created_at", datetime.now().isoformat())
        task.started_at = data.get("started_at")
        task.completed_at = data.get("completed_at")
        return task


class SSEPublisher:
    """SSE 事件发布器"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._subscribers: Dict[str, List[Callable]] = {}
        self._subscriber_lock = threading.Lock()
        self._initialized = True

    def subscribe(self, task_id: str, callback: Callable[[Dict[str, Any]], None]):
        """订阅任务事件"""
        with self._subscriber_lock:
            if task_id not in self._subscribers:
                self._subscribers[task_id] = []
            self._subscribers[task_id].append(callback)

    def unsubscribe(self, task_id: str, callback: Callable):
        """取消订阅"""
        with self._subscriber_lock:
            if task_id in self._subscribers:
                try:
                    self._subscribers[task_id].remove(callback)
                    if not self._subscribers[task_id]:
                        del self._subscribers[task_id]
                except ValueError:
                    pass

    def publish(self, task_id: str, event: Dict[str, Any]):
        """发布任务事件"""
        with self._subscriber_lock:
            callbacks = self._subscribers.get(task_id, []).copy()

        for callback in callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.exception(f"SSE publish error: {e}")


class TaskRegistry:
    """
    异步任务注册中心

    提供以下功能：
    - 任务创建、查询、状态管理
    - 文件持久化
    - TTL 过期清理
    - SSE 实时推送
    - 并发控制
    """

    _instance = None
    _lock = threading.Lock()

    SUCCESS_TTL = 3600
    FAILED_TTL = 86400
    PENDING_TTL = 3600
    MAX_CONCURRENT = 3

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._tasks: Dict[str, TaskInfo] = {}
        self._tasks_lock = threading.Lock()
        self._sse_publisher = SSEPublisher()
        self._cleanup_thread: Optional[threading.Thread] = None
        self._running = False

        self._base_dir = Path("logs/mcp_tasks")
        self._results_dir = self._base_dir / "results"
        self._ensure_dirs()

        self._initialized = True
        self._load_persistent_tasks()
        self._start_cleanup_thread()

        logger.info(f"TaskRegistry initialized, base_dir: {self._base_dir}")

    def _ensure_dirs(self):
        """确保目录存在"""
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._results_dir.mkdir(parents=True, exist_ok=True)

    def _get_tasks_file(self) -> Path:
        return self._base_dir / "tasks.json"

    def _load_persistent_tasks(self):
        """加载持久化的任务"""
        tasks_file = self._get_tasks_file()
        if not tasks_file.exists():
            return

        try:
            with open(tasks_file, "r", encoding="utf-8") as f:
                tasks_data = json.load(f)

            for task_data in tasks_data:
                task = TaskInfo.from_dict(task_data)
                self._tasks[task.task_id] = task

            logger.info(f"Loaded {len(tasks_data)} persistent tasks")
        except Exception as e:
            logger.exception(f"Failed to load persistent tasks: {e}")

    def _save_tasks_index(self):
        """保存任务索引"""
        try:
            tasks_data = [
                task.to_dict()
                for task in self._tasks.values()
                if task.status in (TaskStatus.PENDING, TaskStatus.RUNNING)
            ]
            with open(self._get_tasks_file(), "w", encoding="utf-8") as f:
                json.dump(tasks_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.exception(f"Failed to save tasks index: {e}")

    def _save_task_result(self, task: TaskInfo):
        """保存任务结果"""
        try:
            result_file = self._results_dir / f"{task.task_id}.json"
            with open(result_file, "w", encoding="utf-8") as f:
                json.dump(task.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.exception(f"Failed to save task result: {e}")

    def _count_running_by_type(self, task_type: str) -> int:
        """统计指定类型的运行中任务数"""
        count = 0
        with self._tasks_lock:
            for task in self._tasks.values():
                if task.task_type == task_type and task.status == TaskStatus.RUNNING:
                    count += 1
        return count

    def _start_cleanup_thread(self):
        """启动清理线程"""
        self._running = True
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop, daemon=True, name="TaskCleanup"
        )
        self._cleanup_thread.start()

    def _cleanup_loop(self):
        """清理过期任务"""
        while self._running:
            time.sleep(60)
            try:
                self.cleanup_expired()
            except Exception as e:
                logger.exception(f"Cleanup error: {e}")

    def create_task(
        self, task_type: str, params: Dict[str, Any], timeout: int = 600
    ) -> str:
        """
        创建新任务

        Args:
            task_type: 任务类型
            params: 任务参数
            timeout: 超时时间(秒)

        Returns:
            task_id
        """
        if self._count_running_by_type(task_type) >= self.MAX_CONCURRENT:
            raise RuntimeError(
                f"Maximum concurrent tasks ({self.MAX_CONCURRENT}) reached for {task_type}"
            )

        task_id = f"{task_type}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        task = TaskInfo(task_id, task_type, params, timeout)

        with self._tasks_lock:
            self._tasks[task_id] = task

        logger.info(f"Task created: {task_id}, type: {task_type}")
        return task_id

    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """获取任务"""
        with self._tasks_lock:
            return self._tasks.get(task_id)

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        task = self.get_task(task_id)
        if not task:
            return None

        return {
            "task_id": task.task_id,
            "task_type": task.task_type,
            "status": task.status.value,
            "progress": task.progress,
            "stage": task.stage,
            "stage_detail": task.stage_detail,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "message": self._get_status_message(task),
        }

    def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务结果"""
        task = self.get_task(task_id)
        if not task:
            return None

        return {
            "task_id": task.task_id,
            "task_type": task.task_type,
            "status": task.status.value,
            "result": task.result,
            "error": task.error,
            "completed_at": task.completed_at,
        }

    def update_progress(
        self, task_id: str, progress: int, stage: str, stage_detail: str = ""
    ):
        """更新任务进度"""
        task = self.get_task(task_id)
        if not task:
            return

        with task._lock:
            if task.status == TaskStatus.PENDING:
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.now().isoformat()

            task.progress = min(100, max(0, progress))
            task.stage = stage
            task.stage_detail = stage_detail

        self._sse_publisher.publish(
            task_id,
            {
                "event": "progress",
                "progress": task.progress,
                "stage": task.stage,
                "stage_detail": task.stage_detail,
            },
        )

        logger.debug(f"Task progress: {task_id}, progress={progress}%, stage={stage}")

    def complete_task(self, task_id: str, result: Dict[str, Any]):
        """标记任务完成"""
        task = self.get_task(task_id)
        if not task:
            return

        with task._lock:
            task.status = TaskStatus.COMPLETED
            task.progress = 100
            task.result = result
            task.completed_at = datetime.now().isoformat()

        self._save_task_result(task)
        self._sse_publisher.publish(task_id, {"event": "completed", "result": result})

        logger.info(f"Task completed: {task_id}")

    def fail_task(self, task_id: str, error: str):
        """标记任务失败"""
        task = self.get_task(task_id)
        if not task:
            return

        with task._lock:
            task.status = TaskStatus.FAILED
            task.error = error
            task.completed_at = datetime.now().isoformat()

        self._save_task_result(task)
        self._sse_publisher.publish(task_id, {"event": "failed", "error": error})

        logger.error(f"Task failed: {task_id}, error: {error}")

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self.get_task(task_id)
        if not task:
            return False

        if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
            return False

        with task._lock:
            task.status = TaskStatus.CANCELLED
            task.error = "Cancelled by user"
            task.completed_at = datetime.now().isoformat()

        self._sse_publisher.publish(
            task_id, {"event": "cancelled", "error": "Cancelled by user"}
        )

        logger.info(f"Task cancelled: {task_id}")
        return True

    def subscribe(self, task_id: str, callback: Callable[[Dict[str, Any]], None]):
        """订阅任务 SSE 事件"""
        self._sse_publisher.subscribe(task_id, callback)

    def unsubscribe(self, task_id: str, callback: Callable[[Dict[str, Any]], None]):
        """取消订阅"""
        self._sse_publisher.unsubscribe(task_id, callback)

    def list_tasks(
        self, task_type: Optional[str] = None, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """列出任务"""
        with self._tasks_lock:
            tasks = list(self._tasks.values())

        result = []
        for task in tasks:
            if task_type and task.task_type != task_type:
                continue
            if status and task.status.value != status:
                continue
            result.append(task.to_dict())

        return result

    def cleanup_expired(self):
        """清理过期任务"""
        now = datetime.now()
        expired_task_ids = []

        with self._tasks_lock:
            for task_id, task in self._tasks.items():
                if task.status == TaskStatus.COMPLETED:
                    if task.completed_at:
                        completed_time = datetime.fromisoformat(task.completed_at)
                        if (now - completed_time).total_seconds() > self.SUCCESS_TTL:
                            expired_task_ids.append(task_id)

                elif task.status == TaskStatus.FAILED:
                    if task.completed_at:
                        completed_time = datetime.fromisoformat(task.completed_at)
                        if (now - completed_time).total_seconds() > self.FAILED_TTL:
                            expired_task_ids.append(task_id)

                elif task.status == TaskStatus.PENDING:
                    if task.created_at:
                        created_time = datetime.fromisoformat(task.created_at)
                        if (now - created_time).total_seconds() > self.PENDING_TTL:
                            task.status = TaskStatus.FAILED
                            task.error = "Timeout: pending task expired"
                            task.completed_at = now.isoformat()
                            expired_task_ids.append(task_id)

        for task_id in expired_task_ids:
            try:
                del self._tasks[task_id]
                result_file = self._results_dir / f"{task_id}.json"
                if result_file.exists():
                    result_file.unlink()
                logger.info(f"Cleaned up expired task: {task_id}")
            except Exception as e:
                logger.exception(f"Failed to cleanup task {task_id}: {e}")

        if expired_task_ids:
            self._save_tasks_index()

        return expired_task_ids

    def shutdown(self):
        """关闭任务注册中心"""
        self._running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)
        self._save_tasks_index()
        logger.info("TaskRegistry shutdown")

    def _get_status_message(self, task: TaskInfo) -> str:
        """获取状态消息"""
        messages = {
            TaskStatus.PENDING: "任务已提交，等待调度",
            TaskStatus.RUNNING: f"任务进行中 ({task.progress}%)",
            TaskStatus.COMPLETED: "任务已完成",
            TaskStatus.FAILED: f"任务失败: {task.error}",
            TaskStatus.CANCELLED: "任务已取消",
        }
        return messages.get(task.status, "未知状态")


def get_task_registry() -> TaskRegistry:
    """获取任务注册中心单例"""
    return TaskRegistry()


def create_task(task_type: str, params: Dict[str, Any], timeout: int = 600) -> str:
    """创建任务的快捷函数"""
    return get_task_registry().create_task(task_type, params, timeout)


def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """获取任务状态的快捷函数"""
    return get_task_registry().get_task_status(task_id)


def get_task_result(task_id: str) -> Optional[Dict[str, Any]]:
    """获取任务结果的快捷函数"""
    return get_task_registry().get_task_result(task_id)
