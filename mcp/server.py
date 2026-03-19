"""
MCP Server Implementation

Wraps the MCP protocol handler with Flask-compatible streaming.
"""

import json
import threading
import asyncio
from collections import defaultdict
from datetime import datetime
from queue import Queue, Empty
from typing import Dict, Any, Optional, Callable
from loguru import logger


class MCPServer:
    """
    MCP Server wrapper providing:
    - Tool registration and execution
    - SSE event streaming
    - Session management
    """

    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._resources: Dict[str, Any] = {}
        self._prompts: Dict[str, Any] = {}
        self._sessions: Dict[str, "MCPSession"] = {}
        self._session_lock = threading.Lock()
        self._event_handlers: list = []

    def register_tool(self, name: str, handler: Callable, description: str = ""):
        self._tools[name] = handler
        logger.info(f"MCP tool registered: {name}")

    def register_resource(self, uri: str, data: Any):
        self._resources[uri] = data

    def register_prompt(self, name: str, template: str, description: str = ""):
        self._prompts[name] = {"template": template, "description": description}

    def create_session(self, session_id: str) -> "MCPSession":
        with self._session_lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = MCPSession(session_id)
            return self._sessions[session_id]

    def get_session(self, session_id: str) -> Optional["MCPSession"]:
        with self._session_lock:
            return self._sessions.get(session_id)

    def remove_session(self, session_id: str):
        with self._session_lock:
            self._sessions.pop(session_id, None)

    def get_tools(self) -> Dict[str, Any]:
        return {
            name: {
                "handler": handler,
                "name": name,
            }
            for name, handler in self._tools.items()
        }

    def get_resources(self) -> Dict[str, Any]:
        return self._resources.copy()

    def get_prompts(self) -> Dict[str, Any]:
        return self._prompts.copy()


class MCPSession:
    """
    MCP session for tracking client connections and streaming events.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self._queue: Queue = Queue()
        self._subscribers: list = []
        self._lock = threading.Lock()
        self._terminal_statuses = {"completed", "error", "cancelled"}

    def subscribe(self) -> Queue:
        with self._lock:
            self._subscribers.append(self._queue)
        return self._queue

    def unsubscribe(self, queue: Queue):
        with self._lock:
            if queue in self._subscribers:
                self._subscribers.remove(queue)

    def publish(self, event_type: str, payload: Dict[str, Any]):
        event = {
            "type": event_type,
            "session_id": self.session_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "payload": payload,
        }
        with self._lock:
            for subscriber in self._subscribers:
                try:
                    subscriber.put(event, timeout=0.1)
                except Exception:
                    pass

    def is_active(self) -> bool:
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
        }


def format_sse(event: Dict[str, Any]) -> str:
    payload = json.dumps(event, ensure_ascii=False)
    return f"data: {payload}\n\n"
