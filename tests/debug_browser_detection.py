#!/usr/bin/env python3
"""
Debug browser detection step by step.
"""

from historyhounder.mcp.browser_detection import (
    get_platform_key, 
    expand_browser_path, 
    validate_sqlite_file,
    get_browser_info,
    get_supported_browsers
)
from historyhounder.mcp.config import config


def debug_browser_detection():
    """Debug browser detection step by step."""
    
    print("🔍 Debugging browser detection...")
    
    # Step 1: Check platform
    platform_key = get_platform_key()
    print(f"\n📋 Platform key: {platform_key}")
    
    # Step 2: Check browser paths configuration
    if platform_key in config.browser_paths:
        print(f"✅ Platform {platform_key} found in config")
        for browser_name, path_pattern in config.browser_paths[platform_key].items():
            print(f"  {browser_name}: {path_pattern}")
    else:
        print(f"❌ Platform {platform_key} not found in config")
        return
    
    # Step 3: Test path expansion for each browser
    print(f"\n🔍 Testing path expansion...")
    for browser_name, path_pattern in config.browser_paths[platform_key].items():
        print(f"\n📱 Testing {browser_name}:")
        print(f"  Pattern: {path_pattern}")
        
        expanded_paths = expand_browser_path(path_pattern)
        print(f"  Expanded paths: {expanded_paths}")
        
        if expanded_paths:
            for path in expanded_paths:
                exists = os.path.isfile(path)
                accessible = validate_sqlite_file(path) if exists else False
                print(f"    Path: {path}")
                print(f"    Exists: {exists}")
                print(f"    Accessible: {accessible}")
        else:
            print(f"    ❌ No paths found")
    
    # Step 4: Test browser info
    print(f"\n📊 Testing browser info...")
    for browser_name in config.browser_paths[platform_key].keys():
        browser_info = get_browser_info(browser_name)
        if browser_info:
            print(f"  {browser_name}:")
            print(f"    Path: {browser_info.path}")
            print(f"    Exists: {browser_info.exists}")
            print(f"    Accessible: {browser_info.accessible}")
        else:
            print(f"  {browser_name}: ❌ No info")
    
    # Step 5: Test supported browsers
    print(f"\n📋 Testing supported browsers...")
    browsers = get_supported_browsers()
    for browser in browsers:
        print(f"  {browser.name}:")
        print(f"    Path: {browser.path}")
        print(f"    Exists: {browser.exists}")
        print(f"    Accessible: {browser.accessible}")


if __name__ == "__main__":
    import os
    debug_browser_detection() 