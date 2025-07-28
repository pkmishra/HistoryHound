#!/usr/bin/env python3
"""
Test script to demonstrate the source links fix in QA responses
"""

import requests
import json
import time

def test_source_links():
    """Test that QA responses now include source links"""
    
    base_url = "http://localhost:8080"
    
    print("🧪 Testing Source Links in QA Responses")
    print("=" * 50)
    
    # Test 1: Check if server is running
    print("\n1. Checking server status...")
    try:
        response = requests.get(f"{base_url}/api/health", timeout=10)
        if response.status_code == 200:
            print("✅ Server is running")
        else:
            print(f"❌ Server not responding: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        return
    
    # Test 2: Process some sample history
    print("\n2. Processing sample history...")
    sample_history = [
        {
            "id": "1",
            "url": "https://httpbin.org/get",
            "title": "HTTPBin - GET Request",
            "lastVisitTime": int(time.time() * 1000000),
            "visitCount": 1
        },
        {
            "id": "2",
            "url": "https://httpbin.org/post",
            "title": "HTTPBin - POST Request",
            "lastVisitTime": int(time.time() * 1000000),
            "visitCount": 1
        }
    ]
    
    try:
        response = requests.post(
            f"{base_url}/api/process-history",
            json={"history": sample_history},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ History processed: {result['processed_count']} items")
        else:
            print(f"❌ History processing failed: {response.status_code}")
            print(f"Error: {response.text}")
            return
    except Exception as e:
        print(f"❌ Error during history processing: {e}")
        return
    
    # Test 3: Ask a question and check source links
    print("\n3. Testing QA with source links...")
    try:
        response = requests.post(
            f"{base_url}/api/qa",
            json={
                "question": "What is httpbin?",
                "top_k": 3
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ QA response received")
            print(f"Question: {result['question']}")
            print(f"Answer: {result['answer'][:100]}...")
            
            # Check source links
            sources = result.get('sources', [])
            print(f"\n📚 Source Links ({len(sources)} sources):")
            
            for i, source in enumerate(sources, 1):
                print(f"\n  Source {i}:")
                # Handle both old string format and new object format
                if isinstance(source, dict):
                    print(f"    Title: {source.get('title', 'N/A')}")
                    print(f"    URL: {source.get('url', 'N/A')}")
                    print(f"    Domain: {source.get('domain', 'N/A')}")
                    print(f"    Visit Time: {source.get('visit_time', 'N/A')}")
                    print(f"    Content: {source.get('content', '')[:50]}...")
                else:
                    # Old string format
                    print(f"    Content: {str(source)[:50]}...")
            
            # Verify that sources have URLs (for new format)
            sources_with_urls = [s for s in sources if isinstance(s, dict) and s.get('url')]
            if sources_with_urls:
                print(f"\n✅ SUCCESS: {len(sources_with_urls)} sources have URLs!")
            else:
                print("\n⚠️  Note: Sources are in string format (old format) or have no URLs")
                
        else:
            print(f"❌ QA failed: {response.status_code}")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Error during QA: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Source Links Test Complete!")

if __name__ == "__main__":
    test_source_links() 