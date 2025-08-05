#!/usr/bin/env python3
"""
Test Brave browser support.
"""

from historyhounder.mcp.tools import list_supported_browsers, get_browser_history, get_history_statistics
from historyhounder.mcp.browser_detection import get_browser_info, get_supported_browsers


def test_brave_browser():
    """Test Brave browser support."""
    
    print("🔍 Testing Brave browser support...")
    
    # Test 1: Check if Brave is detected
    print("\n📋 Testing Brave browser detection...")
    try:
        brave_info = get_browser_info("brave")
        if brave_info:
            print(f"✅ Brave browser info:")
            print(f"  Path: {brave_info.path}")
            print(f"  Exists: {brave_info.exists}")
            print(f"  Accessible: {brave_info.accessible}")
        else:
            print("❌ Brave browser not found in configuration")
    except Exception as e:
        print(f"❌ Error getting Brave info: {e}")
    
    # Test 2: Check all supported browsers
    print("\n📋 Testing all supported browsers...")
    try:
        browsers = get_supported_browsers()
        print(f"✅ Found {len(browsers)} supported browsers:")
        for browser in browsers:
            status = "✅" if browser.accessible else "❌"
            print(f"  {status} {browser.name}: {browser.path}")
    except Exception as e:
        print(f"❌ Error listing browsers: {e}")
    
    # Test 3: Test Brave history extraction
    print("\n📚 Testing Brave history extraction...")
    try:
        history_result = get_browser_history(browser="brave", limit=5)
        print("✅ Brave history result:")
        print(f"  Total items: {history_result.get('total_count', 'N/A')}")
        print(f"  Query time: {history_result.get('query_time', 'N/A')}")
        
        if history_result.get('items'):
            print(f"  Sample history items:")
            for i, item in enumerate(history_result['items'][:3]):
                print(f"    {i+1}. {item.get('title', 'No title')} - {item.get('url', 'No URL')}")
        else:
            print("  ❌ No history items found")
    except Exception as e:
        print(f"❌ Error getting Brave history: {e}")
    
    # Test 4: Test all browsers history
    print("\n📚 Testing all browsers history...")
    try:
        history_result = get_browser_history(limit=5)
        print("✅ All browsers history result:")
        print(f"  Total items: {history_result.get('total_count', 'N/A')}")
        print(f"  Query time: {history_result.get('query_time', 'N/A')}")
        
        if history_result.get('items'):
            print(f"  Sample history items:")
            for i, item in enumerate(history_result['items'][:3]):
                print(f"    {i+1}. {item.get('title', 'No title')} - {item.get('url', 'No URL')} ({item.get('browser', 'Unknown')})")
        else:
            print("  ❌ No history items found")
    except Exception as e:
        print(f"❌ Error getting all browsers history: {e}")
    
    # Test 5: Test statistics
    print("\n📈 Testing statistics with Brave...")
    try:
        stats_result = get_history_statistics()
        print("✅ Statistics result:")
        print(f"  Total items: {stats_result.get('total_items', 'N/A')}")
        print(f"  Browser distribution: {stats_result.get('browsers', 'N/A')}")
        print(f"  Date range: {stats_result.get('date_range', 'N/A')}")
        print(f"  Query time: {stats_result.get('query_time', 'N/A')}")
    except Exception as e:
        print(f"❌ Error getting statistics: {e}")


if __name__ == "__main__":
    test_brave_browser() 