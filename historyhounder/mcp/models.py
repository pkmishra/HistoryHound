"""
Pydantic models for MCP (Model Context Protocol) structures.

Defines the data models for MCP requests, responses, tool calls,
and browser history data structures.
"""

from typing import Dict, List, Optional, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field


class MCPRequest(BaseModel):
    """Base MCP request model."""
    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    id: Optional[str] = Field(None, description="Request ID")
    method: str = Field(..., description="MCP method name")
    params: Optional[Dict[str, Any]] = Field(None, description="Method parameters")


class MCPResponse(BaseModel):
    """Base MCP response model."""
    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    id: Optional[str] = Field(None, description="Request ID")
    result: Optional[Dict[str, Any]] = Field(None, description="Response result")
    error: Optional[Dict[str, Any]] = Field(None, description="Error information")


class MCPError(BaseModel):
    """MCP error model."""
    code: int = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional error data")


class ToolCall(BaseModel):
    """MCP tool call model."""
    name: str = Field(..., description="Tool name")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")


class ToolResult(BaseModel):
    """MCP tool result model."""
    content: List[Dict[str, Any]] = Field(default_factory=list, description="Tool result content")
    is_error: bool = Field(default=False, description="Whether the result is an error")


class BrowserHistoryItem(BaseModel):
    """Individual browser history item."""
    id: str = Field(..., description="History item ID")
    url: str = Field(..., description="Page URL")
    title: str = Field(..., description="Page title")
    last_visit_time: datetime = Field(..., description="Last visit timestamp")
    visit_count: int = Field(default=1, description="Number of visits")
    browser: str = Field(..., description="Source browser")
    domain: str = Field(default="", description="Domain name")


class BrowserHistoryResult(BaseModel):
    """Result of browser history retrieval."""
    items: List[BrowserHistoryItem] = Field(default_factory=list, description="History items")
    total_count: int = Field(default=0, description="Total number of items")
    browser: str = Field(..., description="Source browser")
    query_time: datetime = Field(default_factory=datetime.now, description="Query timestamp")


class HistoryStatistics(BaseModel):
    """Browser history statistics."""
    total_items: int = Field(default=0, description="Total history items")
    browsers: Dict[str, int] = Field(default_factory=dict, description="Items per browser")
    domains: Dict[str, int] = Field(default_factory=dict, description="Top domains")
    date_range: Dict[str, datetime] = Field(default_factory=dict, description="Date range")
    query_time: datetime = Field(default_factory=datetime.now, description="Query timestamp")


class SupportedBrowser(BaseModel):
    """Information about a supported browser."""
    name: str = Field(..., description="Browser name")
    path: str = Field(..., description="History file path")
    exists: bool = Field(..., description="Whether history file exists")
    accessible: bool = Field(..., description="Whether file is accessible")


class BrowserListResult(BaseModel):
    """Result of supported browsers query."""
    browsers: List[SupportedBrowser] = Field(default_factory=list, description="Supported browsers")
    platform: str = Field(..., description="Current platform")
    query_time: datetime = Field(default_factory=datetime.now, description="Query timestamp")


# MCP Tool Definitions
class ToolDefinition(BaseModel):
    """MCP tool definition."""
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    inputSchema: Dict[str, Any] = Field(..., description="Tool input schema")


class ListToolsResult(BaseModel):
    """Result of list_tools method."""
    tools: List[ToolDefinition] = Field(default_factory=list, description="Available tools")


class InitializeParams(BaseModel):
    """Parameters for initialize method."""
    protocolVersion: str = Field(..., description="MCP protocol version")
    capabilities: Dict[str, Any] = Field(default_factory=dict, description="Client capabilities")
    clientInfo: Optional[Dict[str, str]] = Field(None, description="Client information")


class InitializeResult(BaseModel):
    """Result of initialize method."""
    protocolVersion: str = Field(..., description="MCP protocol version")
    capabilities: Dict[str, Any] = Field(default_factory=dict, description="Server capabilities")
    serverInfo: Dict[str, str] = Field(..., description="Server information")


class CallToolParams(BaseModel):
    """Parameters for call_tool method."""
    name: str = Field(..., description="Tool name")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")


class CallToolResult(BaseModel):
    """Result of call_tool method."""
    content: List[Dict[str, Any]] = Field(default_factory=list, description="Tool result content")
    isError: bool = Field(default=False, description="Whether the result is an error") 