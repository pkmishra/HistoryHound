#!/usr/bin/env python3
"""
Simple test client for FastMCP server to test real browser history.
"""

import asyncio
import json
import websockets
from datetime import datetime


async def test_fastmcp_server():
    """Test FastMCP server with real browser history."""
    
    uri = "ws://localhost:8087/mcp/"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("🔗 Connected to FastMCP server")
            
            # Test 1: List supported browsers
            print("\n📋 Testing list_supported_browsers_tool...")
            request = {
                "jsonrpc": "2.0",
                "id": "test-1",
                "method": "tools/call",
                "params": {
                    "name": "list_supported_browsers_tool",
                    "arguments": {}
                }
            }
            
            await websocket.send(json.dumps(request))
            response = await websocket.recv()
            result = json.loads(response)
            
            print("✅ List browsers response:")
            print(json.dumps(result, indent=2))
            
            # Test 2: Get browser history (limited to 10 items)
            print("\n📚 Testing get_browser_history_tool...")
            request = {
                "jsonrpc": "2.0",
                "id": "test-2",
                "method": "tools/call",
                "params": {
                    "name": "get_browser_history_tool",
                    "arguments": {
                        "limit": 10
                    }
                }
            }
            
            await websocket.send(json.dumps(request))
            response = await websocket.recv()
            result = json.loads(response)
            
            print("✅ Get history response:")
            if "result" in result and "content" in result["result"]:
                content = result["result"]["content"][0]
                print(f"📊 Total items: {content.get('total_items', 'N/A')}")
                print(f"🔍 Query time: {content.get('query_time', 'N/A')}")
                
                if "history" in content and content["history"]:
                    print(f"📝 Sample history items:")
                    for i, item in enumerate(content["history"][:3]):
                        print(f"  {i+1}. {item.get('title', 'No title')} - {item.get('url', 'No URL')}")
                else:
                    print("❌ No history items found")
            else:
                print("❌ Error in response:")
                print(json.dumps(result, indent=2))
            
            # Test 3: Get history statistics
            print("\n📈 Testing get_history_statistics_tool...")
            request = {
                "jsonrpc": "2.0",
                "id": "test-3",
                "method": "tools/call",
                "params": {
                    "name": "get_history_statistics_tool",
                    "arguments": {}
                }
            }
            
            await websocket.send(json.dumps(request))
            response = await websocket.recv()
            result = json.loads(response)
            
            print("✅ Statistics response:")
            if "result" in result and "content" in result["result"]:
                content = result["result"]["content"][0]
                print(f"📊 Total items: {content.get('total_items', 'N/A')}")
                print(f"🌐 Browser distribution: {content.get('browser_distribution', 'N/A')}")
                print(f"📅 Date range: {content.get('date_range', 'N/A')}")
                print(f"🔍 Query time: {content.get('query_time', 'N/A')}")
            else:
                print("❌ Error in response:")
                print(json.dumps(result, indent=2))
                
    except websockets.exceptions.InvalidStatus as e:
        print(f"❌ Server rejected WebSocket connection: {e}")
        print("💡 This might be due to server configuration or protocol mismatch")
    except ConnectionRefusedError:
        print("❌ Could not connect to FastMCP server. Is it running on port 8087?")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    print("🚀 Testing FastMCP server with real browser history...")
    asyncio.run(test_fastmcp_server()) 