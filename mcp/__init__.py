"""
BettaFish MCP Module

This module provides MCP (Model Context Protocol) integration for the BettaFish system.
"""

__version__ = "1.0.0"

from .blueprint import mcp_bp
from .server import MCPServer

__all__ = ["mcp_bp", "MCPServer"]
