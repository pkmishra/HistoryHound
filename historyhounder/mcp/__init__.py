"""
Model Context Protocol (MCP) Server for Browser History

This module provides MCP server functionality to expose browser history data
as tools for AI models to access through the standardized MCP protocol.
"""

from .server import create_mcp_server
from .tools import get_browser_history, get_history_statistics, list_supported_browsers
from .models import MCPRequest, MCPResponse, ToolCall, ToolResult
from .config import MCPConfig

__all__ = [
    "create_mcp_server",
    "get_browser_history", 
    "get_history_statistics",
    "list_supported_browsers",
    "MCPRequest",
    "MCPResponse", 
    "ToolCall",
    "ToolResult",
    "MCPConfig"
] 