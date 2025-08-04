#!/usr/bin/env python3
"""
Simple test for FastMCP server using HTTP requests.
"""

import requests
import json


def test_fastmcp_http():
    """Test FastMCP server with HTTP requests."""
    
    base_url = "http://localhost:8087"
    
    print("🔍 Testing FastMCP server with HTTP requests...")
    
    # Test 1: Check if server is running
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        print(f"✅ Server response: {response.status_code}")
        print(f"📄 Response text: {response.text[:200]}...")
    except requests.exceptions.RequestException as e:
        print(f"❌ Could not connect to server: {e}")
        return
    
    # Test 2: Try to get server info
    try:
        response = requests.get(f"{base_url}/docs", timeout=5)
        print(f"✅ Docs response: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Could not get docs: {e}")


if __name__ == "__main__":
    test_fastmcp_http() 