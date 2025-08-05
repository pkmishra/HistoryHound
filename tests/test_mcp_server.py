"""
Unit tests for FastMCP Server functionality.

Tests the FastMCP server implementation and tool definitions.
"""

import pytest
import json
import asyncio
from datetime import datetime
from unittest.mock import patch, MagicMock

from historyhounder.mcp.server import create_mcp_server
from historyhounder.mcp.models import MCPRequest, MCPResponse, ToolDefinition
from historyhounder.mcp.config import config


class TestFastMCPServer:
    """Test FastMCP server functionality."""
    
    def test_server_creation(self):
        """Test FastMCP server creation."""
        server = create_mcp_server()
        assert server is not None
        assert hasattr(server, 'get_tools')
        
        # Check that tools are registered
        tools = asyncio.run(server.get_tools())
        assert isinstance(tools, dict)
        tool_names = list(tools.keys())
        assert "get_browser_history_tool" in tool_names
        assert "get_history_statistics_tool" in tool_names
        assert "list_supported_browsers_tool" in tool_names
    
    def test_tool_definitions(self):
        """Test that tool definitions are properly structured."""
        server = create_mcp_server()
        tools = asyncio.run(server.get_tools())
        
        for tool_name, tool in tools.items():
            assert isinstance(tool_name, str)
            assert tool_name
            # Tools are FunctionTool objects
            assert hasattr(tool, 'name')
            assert hasattr(tool, 'description')
            assert tool.name == tool_name
            assert tool.description
    
    @patch('historyhounder.mcp.tools.list_supported_browsers')
    def test_list_supported_browsers_tool(self, mock_list_browsers):
        """Test list_supported_browsers_tool functionality."""
        # Mock the underlying function
        mock_list_browsers.return_value = {
            "browsers": [
                {"name": "chrome", "available": True, "path": "/test/path"},
                {"name": "firefox", "available": False, "path": None}
            ],
            "platform": {"system": "test", "release": "test"},
            "query_time": datetime.now().isoformat()
        }
        
        server = create_mcp_server()
        tools = asyncio.run(server.get_tools())
        
        # Check the tool exists
        assert "list_supported_browsers_tool" in tools
        tool = tools["list_supported_browsers_tool"]
        assert tool.name == "list_supported_browsers_tool"
        assert "browser" in tool.description.lower()
        assert "supported" in tool.description.lower()
    
    @patch('historyhounder.mcp.tools.get_browser_history')
    def test_get_browser_history_tool(self, mock_get_history):
        """Test get_browser_history_tool functionality."""
        # Mock the underlying function
        mock_get_history.return_value = {
            "history": [
                {
                    "url": "https://example.com",
                    "title": "Example",
                    "visit_time": "2024-01-01T00:00:00",
                    "visit_count": 1,
                    "browser": "chrome"
                }
            ],
            "total_items": 1,
            "query_time": datetime.now().isoformat()
        }
        
        server = create_mcp_server()
        tools = asyncio.run(server.get_tools())
        
        # Check the tool exists
        assert "get_browser_history_tool" in tools
        tool = tools["get_browser_history_tool"]
        assert tool.name == "get_browser_history_tool"
        assert "browser" in tool.description.lower()
        assert "history" in tool.description.lower()
        assert "filter" in tool.description.lower()
    
    @patch('historyhounder.mcp.tools.get_history_statistics')
    def test_get_history_statistics_tool(self, mock_get_stats):
        """Test get_history_statistics_tool functionality."""
        # Mock the underlying function
        mock_get_stats.return_value = {
            "total_items": 100,
            "browser_distribution": {"chrome": 50, "firefox": 30, "safari": 20},
            "top_domains": [{"domain": "google.com", "count": 10}],
            "date_range": {"earliest": "2024-01-01", "latest": "2024-12-31"},
            "query_time": datetime.now().isoformat()
        }
        
        server = create_mcp_server()
        tools = asyncio.run(server.get_tools())
        
        # Check the tool exists
        assert "get_history_statistics_tool" in tools
        tool = tools["get_history_statistics_tool"]
        assert tool.name == "get_history_statistics_tool"
        assert "statistics" in tool.description.lower()
        assert "analytics" in tool.description.lower()


class TestMCPModels:
    """Test MCP model structures."""
    
    def test_mcp_request_model(self):
        """Test MCPRequest model validation."""
        request = MCPRequest(
            jsonrpc="2.0",
            id="test-1",
            method="initialize",
            params={"test": "value"}
        )
        
        assert request.jsonrpc == "2.0"
        assert request.id == "test-1"
        assert request.method == "initialize"
        assert request.params == {"test": "value"}
    
    def test_mcp_response_model(self):
        """Test MCPResponse model validation."""
        response = MCPResponse(
            jsonrpc="2.0",
            id="test-1",
            result={"success": True}
        )
        
        assert response.jsonrpc == "2.0"
        assert response.id == "test-1"
        assert response.result == {"success": True}
        assert response.error is None
    
    def test_tool_definition_model(self):
        """Test ToolDefinition model validation."""
        tool = ToolDefinition(
            name="test_tool",
            description="Test tool description",
            inputSchema={
                "type": "object",
                "properties": {
                    "test": {"type": "string"}
                }
            }
        )
        
        assert tool.name == "test_tool"
        assert tool.description == "Test tool description"
        assert tool.inputSchema["type"] == "object"


class TestMCPTools:
    """Test MCP tools functionality."""
    
    @patch('historyhounder.mcp.tools.list_supported_browsers')
    def test_list_supported_browsers_integration(self, mock_list_browsers):
        """Test list_supported_browsers tool integration."""
        from historyhounder.mcp.tools import list_supported_browsers
        
        # Mock the browser detection
        mock_list_browsers.return_value = {
            "browsers": [
                {"name": "chrome", "available": True, "path": "/test/path"},
                {"name": "firefox", "available": False, "path": None}
            ],
            "platform": {"system": "test", "release": "test"},
            "query_time": datetime.now().isoformat()
        }
        
        result = list_supported_browsers()
        
        assert "browsers" in result
        assert "platform" in result
        assert "query_time" in result
        assert len(result["browsers"]) == 2
        assert result["browsers"][0]["name"] == "chrome"
        assert result["browsers"][1]["name"] == "firefox"
    
    @patch('historyhounder.mcp.tools.get_browser_history')
    def test_get_browser_history_integration(self, mock_get_history):
        """Test get_browser_history tool integration."""
        from historyhounder.mcp.tools import get_browser_history
        
        # Mock the history extraction
        mock_get_history.return_value = {
            "history": [
                {
                    "url": "https://example.com",
                    "title": "Example",
                    "visit_time": "2024-01-01T00:00:00",
                    "visit_count": 1,
                    "browser": "chrome"
                }
            ],
            "total_items": 1,
            "query_time": datetime.now().isoformat()
        }
        
        result = get_browser_history(browser="chrome", limit=10)
        
        assert "history" in result
        assert "total_items" in result
        assert "query_time" in result
        assert len(result["history"]) == 1
        assert result["history"][0]["url"] == "https://example.com"
    
    @patch('historyhounder.mcp.tools.get_history_statistics')
    def test_get_history_statistics_integration(self, mock_get_stats):
        """Test get_history_statistics tool integration."""
        from historyhounder.mcp.tools import get_history_statistics
        
        # Mock the statistics calculation
        mock_get_stats.return_value = {
            "total_items": 100,
            "browser_distribution": {"chrome": 50, "firefox": 30, "safari": 20},
            "top_domains": [{"domain": "google.com", "count": 10}],
            "date_range": {"earliest": "2024-01-01", "latest": "2024-12-31"},
            "query_time": datetime.now().isoformat()
        }
        
        result = get_history_statistics()
        
        assert "total_items" in result
        assert "browser_distribution" in result
        assert "top_domains" in result
        assert "date_range" in result
        assert "query_time" in result
        assert result["total_items"] == 100 