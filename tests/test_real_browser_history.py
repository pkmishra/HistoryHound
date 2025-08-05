#!/usr/bin/env python3
"""
Test browser history tools with real browser data.
"""

from historyhounder.mcp.tools import list_supported_browsers, get_browser_history, get_history_statistics


def test_real_browser_history():
    """Test browser history tools with real data."""
    
    print("🔍 Testing browser history tools with real data...")
    
    # Test 1: List supported browsers
    print("\n📋 Testing list_supported_browsers...")
    try:
        browsers_result = list_supported_browsers()
        print("✅ List browsers result:")
        print(f"  Platform: {browsers_result.get('platform', 'N/A')}")
        print(f"  Available browsers: {len(browsers_result.get('browsers', []))}")
        for browser in browsers_result.get('browsers', []):
            status = "✅" if browser.get('accessible') else "❌"
            print(f"    {status} {browser.get('name', 'Unknown')}: {browser.get('path', 'N/A')}")
    except Exception as e:
        print(f"❌ Error listing browsers: {e}")
    
    # Test 2: Get browser history
    print("\n📚 Testing get_browser_history...")
    try:
        history_result = get_browser_history(limit=5)
        print("✅ Get history result:")
        print(f"  Total items: {history_result.get('total_count', 'N/A')}")
        print(f"  Query time: {history_result.get('query_time', 'N/A')}")
        
        if history_result.get('items'):
            print(f"  Sample history items:")
            for i, item in enumerate(history_result['items'][:3]):
                print(f"    {i+1}. {item.get('title', 'No title')} - {item.get('url', 'No URL')}")
        else:
            print("  ❌ No history items found")
    except Exception as e:
        print(f"❌ Error getting history: {e}")
    
    # Test 3: Get history statistics
    print("\n📈 Testing get_history_statistics...")
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
    test_real_browser_history() 