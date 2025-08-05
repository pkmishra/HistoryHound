#!/usr/bin/env python3
"""
WebSocket test client for FastMCP server.
"""

import asyncio
import json
import websockets
from datetime import datetime


async def test_fastmcp_websocket():
    """Test FastMCP server with WebSocket connection."""
    
    uri = "ws://localhost:8087/mcp/"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("🔗 Connected to FastMCP server")
            
            # Step 1: Initialize the connection
            print("\n📋 Step 1: Initializing connection...")
            init_request = {
                "jsonrpc": "2.0",
                "id": "init-1",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "test-client",
                        "version": "1.0.0"
                    }
                }
            }
            
            await websocket.send(json.dumps(init_request))
            response = await websocket.recv()
            init_result = json.loads(response)
            
            print("✅ Initialize response:")
            print(json.dumps(init_result, indent=2))
            
            # Step 2: List available tools
            print("\n📋 Step 2: Listing tools...")
            list_tools_request = {
                "jsonrpc": "2.0",
                "id": "tools-1",
                "method": "tools/list"
            }
            
            await websocket.send(json.dumps(list_tools_request))
            response = await websocket.recv()
            tools_result = json.loads(response)
            
            print("✅ Tools response:")
            print(json.dumps(tools_result, indent=2))
            
            # Step 3: Call list_supported_browsers_tool
            print("\n📋 Step 3: Testing list_supported_browsers_tool...")
            call_request = {
                "jsonrpc": "2.0",
                "id": "call-1",
                "method": "tools/call",
                "params": {
                    "name": "list_supported_browsers_tool",
                    "arguments": {}
                }
            }
            
            await websocket.send(json.dumps(call_request))
            response = await websocket.recv()
            call_result = json.loads(response)
            
            print("✅ List browsers response:")
            print(json.dumps(call_result, indent=2))
            
            # Step 4: Call get_browser_history_tool
            print("\n📋 Step 4: Testing get_browser_history_tool...")
            call_request = {
                "jsonrpc": "2.0",
                "id": "call-2",
                "method": "tools/call",
                "params": {
                    "name": "get_browser_history_tool",
                    "arguments": {
                        "limit": 5
                    }
                }
            }
            
            await websocket.send(json.dumps(call_request))
            response = await websocket.recv()
            call_result = json.loads(response)
            
            print("✅ Get history response:")
            print(json.dumps(call_result, indent=2))
            
            # Step 5: Call get_history_statistics_tool
            print("\n📋 Step 5: Testing get_history_statistics_tool...")
            call_request = {
                "jsonrpc": "2.0",
                "id": "call-3",
                "method": "tools/call",
                "params": {
                    "name": "get_history_statistics_tool",
                    "arguments": {}
                }
            }
            
            await websocket.send(json.dumps(call_request))
            response = await websocket.recv()
            call_result = json.loads(response)
            
            print("✅ Statistics response:")
            print(json.dumps(call_result, indent=2))
                
    except websockets.exceptions.InvalidStatus as e:
        print(f"❌ Server rejected WebSocket connection: {e}")
        print("💡 This might be due to server configuration or protocol mismatch")
    except ConnectionRefusedError:
        print("❌ Could not connect to FastMCP server. Is it running on port 8087?")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    print("🚀 Testing FastMCP server with WebSocket connection...")
    asyncio.run(test_fastmcp_websocket()) 