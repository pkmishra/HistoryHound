"""
Model Context Protocol (MCP) Server for Browser History

Implements the MCP protocol to expose browser history data as tools
for AI models to access through standardized MCP methods.
"""

import json
import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

from .config import config
from .models import (
    MCPRequest, MCPResponse, MCPError, ToolDefinition,
    InitializeParams, InitializeResult, CallToolParams, CallToolResult
)
from .tools import get_browser_history, get_history_statistics, list_supported_browsers

logger = logging.getLogger(__name__)


class MCPServer:
    """MCP Server implementation for browser history access."""
    
    def __init__(self):
        """Initialize the MCP server."""
        self.initialized = False
        self.tools = self._define_tools()
        
    def _define_tools(self) -> List[ToolDefinition]:
        """Define the available MCP tools."""
        return [
            ToolDefinition(
                name="get_browser_history",
                description="Retrieve browser history with optional filtering by browser, date range, domain, and limit",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "browser": {
                            "type": "string",
                            "description": "Specific browser to query (chrome, firefox, safari, edge). If not specified, queries all accessible browsers."
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of history items to return",
                            "default": 100,
                            "minimum": 1,
                            "maximum": 1000
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Start date for filtering (ISO format: YYYY-MM-DDTHH:MM:SS)",
                            "format": "date-time"
                        },
                        "end_date": {
                            "type": "string", 
                            "description": "End date for filtering (ISO format: YYYY-MM-DDTHH:MM:SS)",
                            "format": "date-time"
                        },
                        "domain": {
                            "type": "string",
                            "description": "Domain filter (e.g., 'google.com', 'github.com')"
                        }
                    }
                }
            ),
            ToolDefinition(
                name="get_history_statistics",
                description="Get statistics about browser history including total items, browser breakdown, top domains, and date range",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            ToolDefinition(
                name="list_supported_browsers",
                description="List all supported browsers and their accessibility status on the current platform",
                inputSchema={
                    "type": "object", 
                    "properties": {}
                }
            )
        ]
    
    async def handle_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an MCP request and return the response."""
        try:
            request = MCPRequest(**request_data)
            
            if request.method == "initialize":
                return await self._handle_initialize(request)
            elif request.method == "list_tools":
                return await self._handle_list_tools(request)
            elif request.method == "call_tool":
                return await self._handle_call_tool(request)
            else:
                return self._create_error_response(
                    request.id, 
                    -32601, 
                    f"Method not found: {request.method}"
                )
                
        except Exception as e:
            logger.error(f"Error handling MCP request: {e}")
            return self._create_error_response(
                request_data.get("id"),
                -32603,
                f"Internal error: {str(e)}"
            )
    
    async def _handle_initialize(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle initialize method."""
        try:
            params = InitializeParams(**request.params) if request.params else InitializeParams(
                protocolVersion=config.protocol_version,
                capabilities={},
                clientInfo=None
            )
            
            # Validate protocol version
            if params.protocolVersion != config.protocol_version:
                return self._create_error_response(
                    request.id,
                    -32602,
                    f"Unsupported protocol version: {params.protocolVersion}"
                )
            
            self.initialized = True
            
            result = InitializeResult(
                protocolVersion=config.protocol_version,
                capabilities={
                    "tools": {}
                },
                serverInfo={
                    "name": config.server_name,
                    "version": config.server_version
                }
            )
            
            response_data = {
                "jsonrpc": "2.0",
                "id": request.id,
                "result": result.model_dump()
            }
            return response_data
            
        except Exception as e:
            logger.error(f"Error in initialize: {e}")
            return self._create_error_response(
                request.id,
                -32602,
                f"Invalid params: {str(e)}"
            )
    
    async def _handle_list_tools(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle list_tools method."""
        if not self.initialized:
            return self._create_error_response(
                request.id,
                -32002,
                "Server not initialized"
            )
        
        result = {
            "tools": [tool.model_dump() for tool in self.tools]
        }
        
        response_data = {
            "jsonrpc": "2.0",
            "id": request.id,
            "result": result
        }
        return response_data
    
    async def _handle_call_tool(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle call_tool method."""
        if not self.initialized:
            return self._create_error_response(
                request.id,
                -32002,
                "Server not initialized"
            )
        
        try:
            params = CallToolParams(**request.params) if request.params else CallToolParams(
                name="",
                arguments={}
            )
            
            # Find the tool
            tool = next((t for t in self.tools if t.name == params.name), None)
            if not tool:
                return self._create_error_response(
                    request.id,
                    -32601,
                    f"Tool not found: {params.name}"
                )
            
            # Execute the tool
            result = await self._execute_tool(params.name, params.arguments)
            
            response_data = {
                "jsonrpc": "2.0",
                "id": request.id,
                "result": {
                    "content": [result],
                    "isError": False
                }
            }
            return response_data
            
        except Exception as e:
            logger.error(f"Error in call_tool: {e}")
            return self._create_error_response(
                request.id,
                -32603,
                f"Tool execution failed: {str(e)}"
            )
    
    async def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific tool with the given arguments."""
        
        if tool_name == "get_browser_history":
            return get_browser_history(
                browser=arguments.get("browser"),
                limit=arguments.get("limit", config.default_limit),
                start_date=arguments.get("start_date"),
                end_date=arguments.get("end_date"),
                domain=arguments.get("domain")
            )
            
        elif tool_name == "get_history_statistics":
            return get_history_statistics()
            
        elif tool_name == "list_supported_browsers":
            return list_supported_browsers()
            
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    def _create_error_response(self, request_id: Optional[str], code: int, message: str) -> Dict[str, Any]:
        """Create an error response."""
        error = MCPError(
            code=code,
            message=message
        )
        
        return MCPResponse(
            id=request_id,
            error=error.model_dump()
        ).model_dump()


class MCPWebSocketServer:
    """WebSocket-based MCP server for real-time communication."""
    
    def __init__(self):
        """Initialize the WebSocket MCP server."""
        self.mcp_server = MCPServer()
    
    async def handle_websocket(self, websocket):
        """Handle WebSocket connections for MCP protocol."""
        try:
            async for message in websocket:
                try:
                    # Parse the message
                    request_data = json.loads(message)
                    
                    # Handle the request
                    response = await self.mcp_server.handle_request(request_data)
                    
                    # Send the response
                    await websocket.send(json.dumps(response))
                    
                except json.JSONDecodeError as e:
                    error_response = self.mcp_server._create_error_response(
                        None, -32700, f"Parse error: {str(e)}"
                    )
                    await websocket.send(json.dumps(error_response))
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    error_response = self.mcp_server._create_error_response(
                        None, -32603, f"Internal error: {str(e)}"
                    )
                    await websocket.send(json.dumps(error_response))
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("WebSocket connection closed")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")


def create_mcp_server() -> MCPServer:
    """Create and return an MCP server instance."""
    return MCPServer()


def create_websocket_server() -> MCPWebSocketServer:
    """Create and return a WebSocket MCP server instance."""
    return MCPWebSocketServer() 