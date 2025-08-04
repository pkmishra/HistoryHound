"""
Unit tests for MCP (Model Context Protocol) Server functionality.

Tests the MCP server implementation, tool definitions, and basic
functionality without requiring actual browser history files.
"""

import pytest
import json
import asyncio
from datetime import datetime
from unittest.mock import patch, MagicMock

from historyhounder.mcp.server import MCPServer, create_mcp_server
from historyhounder.mcp.models import MCPRequest, MCPResponse, ToolDefinition
from historyhounder.mcp.config import config


class TestMCPServer:
    """Test MCP server functionality."""
    
    def test_server_initialization(self):
        """Test MCP server initialization."""
        server = MCPServer()
        assert server.initialized == False
        assert len(server.tools) == 3
        
        # Check tool names
        tool_names = [tool.name for tool in server.tools]
        assert "get_browser_history" in tool_names
        assert "get_history_statistics" in tool_names
        assert "list_supported_browsers" in tool_names
    
    def test_tool_definitions(self):
        """Test that tool definitions are properly structured."""
        server = MCPServer()
        
        for tool in server.tools:
            assert isinstance(tool, ToolDefinition)
            assert tool.name
            assert tool.description
            assert tool.inputSchema
            assert "type" in tool.inputSchema
            assert tool.inputSchema["type"] == "object"
    
    def test_initialize_method(self):
        """Test initialize method handling."""
        server = MCPServer()
        
        request_data = {
            "jsonrpc": "2.0",
            "id": "test-1",
            "method": "initialize",
            "params": {
                "protocolVersion": config.protocol_version,
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        response = asyncio.run(server.handle_request(request_data))
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "test-1"
        assert "result" in response
        assert "error" not in response
        
        result = response["result"]
        assert result["protocolVersion"] == config.protocol_version
        assert "capabilities" in result
        assert "serverInfo" in result
        assert result["serverInfo"]["name"] == config.server_name
        assert result["serverInfo"]["version"] == config.server_version
        
        # Server should be initialized
        assert server.initialized == True
    
    def test_initialize_invalid_version(self):
        """Test initialize with invalid protocol version."""
        server = MCPServer()
        
        request_data = {
            "jsonrpc": "2.0",
            "id": "test-1",
            "method": "initialize",
            "params": {
                "protocolVersion": "invalid-version",
                "capabilities": {}
            }
        }
        
        response = asyncio.run(server.handle_request(request_data))
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "test-1"
        assert "error" in response
        assert response["error"]["code"] == -32602  # Invalid params error
    
    def test_list_tools_before_initialize(self):
        """Test list_tools before initialization."""
        server = MCPServer()
        
        request_data = {
            "jsonrpc": "2.0",
            "id": "test-1",
            "method": "list_tools"
        }
        
        response = asyncio.run(server.handle_request(request_data))
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "test-1"
        assert "error" in response
        assert response["error"]["code"] == -32002
    
    def test_list_tools_after_initialize(self):
        """Test list_tools after initialization."""
        server = MCPServer()
        
        # First initialize
        init_request = {
            "jsonrpc": "2.0",
            "id": "init-1",
            "method": "initialize",
            "params": {
                "protocolVersion": config.protocol_version,
                "capabilities": {}
            }
        }
        asyncio.run(server.handle_request(init_request))
        
        # Then list tools
        list_request = {
            "jsonrpc": "2.0",
            "id": "test-1",
            "method": "list_tools"
        }
        
        response = asyncio.run(server.handle_request(list_request))
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "test-1"
        assert "result" in response
        assert "error" not in response or response["error"] is None
        
        result = response["result"]
        assert "tools" in result
        assert len(result["tools"]) == 3
        
        tool_names = [tool["name"] for tool in result["tools"]]
        assert "get_browser_history" in tool_names
        assert "get_history_statistics" in tool_names
        assert "list_supported_browsers" in tool_names
    
    def test_call_tool_before_initialize(self):
        """Test call_tool before initialization."""
        server = MCPServer()
        
        request_data = {
            "jsonrpc": "2.0",
            "id": "test-1",
            "method": "call_tool",
            "params": {
                "name": "list_supported_browsers",
                "arguments": {}
            }
        }
        
        response = asyncio.run(server.handle_request(request_data))
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "test-1"
        assert "error" in response
        assert response["error"]["code"] == -32002
    
    @patch('historyhounder.mcp.tools.list_supported_browsers')
    def test_call_tool_after_initialize(self, mock_list_browsers):
        """Test call_tool after initialization."""
        server = MCPServer()
        
        # Mock the tool function
        mock_list_browsers.return_value = {
            "browsers": [],
            "platform": {"system": "test"},
            "query_time": datetime.now().isoformat()
        }
        
        # First initialize
        init_request = {
            "jsonrpc": "2.0",
            "id": "init-1",
            "method": "initialize",
            "params": {
                "protocolVersion": config.protocol_version,
                "capabilities": {}
            }
        }
        asyncio.run(server.handle_request(init_request))
        
        # Then call tool
        call_request = {
            "jsonrpc": "2.0",
            "id": "test-1",
            "method": "call_tool",
            "params": {
                "name": "list_supported_browsers",
                "arguments": {}
            }
        }
        
        response = asyncio.run(server.handle_request(call_request))
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "test-1"
        assert "result" in response
        assert "error" not in response or response["error"] is None
        
        result = response["result"]
        assert "content" in result
        assert "isError" in result
        assert result["isError"] == False
        
        # Verify the tool returned a valid result
        assert len(result["content"]) == 1
        assert "browsers" in result["content"][0]
        assert "platform" in result["content"][0]
        assert "query_time" in result["content"][0]
    
    def test_call_tool_not_found(self):
        """Test call_tool with non-existent tool."""
        server = MCPServer()
        
        # Initialize first
        init_request = {
            "jsonrpc": "2.0",
            "id": "init-1",
            "method": "initialize",
            "params": {
                "protocolVersion": config.protocol_version,
                "capabilities": {}
            }
        }
        asyncio.run(server.handle_request(init_request))
        
        # Call non-existent tool
        call_request = {
            "jsonrpc": "2.0",
            "id": "test-1",
            "method": "call_tool",
            "params": {
                "name": "non_existent_tool",
                "arguments": {}
            }
        }
        
        response = asyncio.run(server.handle_request(call_request))
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "test-1"
        assert "error" in response
        assert response["error"]["code"] == -32601
    
    def test_method_not_found(self):
        """Test handling of unknown method."""
        server = MCPServer()
        
        request_data = {
            "jsonrpc": "2.0",
            "id": "test-1",
            "method": "unknown_method"
        }
        
        response = asyncio.run(server.handle_request(request_data))
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "test-1"
        assert "error" in response
        assert response["error"]["code"] == -32601
    
    def test_invalid_json(self):
        """Test handling of invalid JSON request."""
        server = MCPServer()
        
        # This should be handled by the caller, but we test error handling
        request_data = {
            "jsonrpc": "2.0",
            "id": "test-1",
            "method": "initialize",
            "params": "invalid_params"  # Should be dict
        }
        
        response = asyncio.run(server.handle_request(request_data))
        
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "test-1"
        assert "error" in response
        assert response["error"]["code"] == -32603  # Internal error for validation failure
    
    def test_create_mcp_server(self):
        """Test server creation function."""
        server = create_mcp_server()
        assert isinstance(server, MCPServer)
        assert server.initialized == False
        assert len(server.tools) == 3


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