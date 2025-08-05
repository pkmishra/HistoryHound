#!/usr/bin/env python3
"""
Direct test of FastMCP server functions with real browser history.
"""

from historyhounder.mcp.server import create_mcp_server
import asyncio


async def test_fastmcp_direct():
    """Test FastMCP server functions directly."""
    
    print("🔍 Testing FastMCP server functions directly...")
    
    # Create the server
    server = create_mcp_server()
    print("✅ FastMCP server created")
    
    # Get tools
    tools = await server.get_tools()
    print(f"✅ Found {len(tools)} tools:")
    for tool_name in tools.keys():
        print(f"  - {tool_name}")
    
    # Test list_supported_browsers_tool
    print("\n📋 Testing list_supported_browsers_tool...")
    try:
        list_tool = tools["list_supported_browsers_tool"]
        result = await list_tool()
        print("✅ List browsers result:")
        print(f"  Platform: {result.get('platform', 'N/A')}")
        print(f"  Browsers: {len(result.get('browsers', []))}")
        for browser in result.get('browsers', []):
            status = "✅" if browser.get('accessible') else "❌"
            print(f"    {status} {browser.get('name', 'Unknown')}: {browser.get('path', 'N/A')}")
    except Exception as e:
        print(f"❌ Error testing list browsers: {e}")
    
    # Test get_browser_history_tool
    print("\n📚 Testing get_browser_history_tool...")
    try:
        history_tool = tools["get_browser_history_tool"]
        result = await history_tool(limit=5)
        print("✅ Get history result:")
        print(f"  Total items: {result.get('total_count', 'N/A')}")
        print(f"  Query time: {result.get('query_time', 'N/A')}")
        
        if result.get('items'):
            print(f"  Sample history items:")
            for i, item in enumerate(result['items'][:3]):
                print(f"    {i+1}. {item.get('title', 'No title')} - {item.get('url', 'No URL')}")
        else:
            print("  ❌ No history items found")
    except Exception as e:
        print(f"❌ Error testing get history: {e}")
    
    # Test get_history_statistics_tool
    print("\n📈 Testing get_history_statistics_tool...")
    try:
        stats_tool = tools["get_history_statistics_tool"]
        result = await stats_tool()
        print("✅ Statistics result:")
        print(f"  Total items: {result.get('total_items', 'N/A')}")
        print(f"  Browser distribution: {result.get('browsers', 'N/A')}")
        print(f"  Date range: {result.get('date_range', 'N/A')}")
        print(f"  Query time: {result.get('query_time', 'N/A')}")
    except Exception as e:
        print(f"❌ Error testing statistics: {e}")


if __name__ == "__main__":
    print("🚀 Testing FastMCP server functions with real browser history...")
    asyncio.run(test_fastmcp_direct()) 