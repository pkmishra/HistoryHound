#!/usr/bin/env python3
"""
Test script to verify vector store update functionality
"""

import requests
import json
import time

def test_vector_store_update():
    """Test the vector store update functionality"""
    
    base_url = "http://localhost:8080"
    
    print("🧪 Testing Vector Store Update Functionality")
    print("=" * 50)
    
    # Test 1: Check initial stats
    print("\n1. Checking initial vector store status...")
    try:
        response = requests.get(f"{base_url}/api/stats", timeout=10)
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Initial stats: {stats['stats']['documents']} documents")
            if stats['stats'].get('sample_documents'):
                print("Sample documents:")
                for doc in stats['stats']['sample_documents'][:3]:
                    print(f"  - {doc['title']} ({doc['url']})")
        else:
            print(f"❌ Failed to get stats: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Error getting stats: {e}")
        return
    
    # Test 2: Simulate history sync
    print("\n2. Simulating history sync...")
    sample_history = [
        {
            "id": "1",
            "url": "https://example.com",
            "title": "Example Domain",
            "lastVisitTime": int(time.time() * 1000000),
            "visitCount": 1
        },
        {
            "id": "2", 
            "url": "https://test.com",
            "title": "Test Page",
            "lastVisitTime": int(time.time() * 1000000),
            "visitCount": 1
        },
        {
            "id": "3",
            "url": "https://github.com",
            "title": "GitHub",
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
            print(f"✅ Sync successful: {result['processed_count']} items processed")
            print(f"Message: {result['message']}")
        else:
            print(f"❌ Sync failed: {response.status_code}")
            print(f"Error: {response.text}")
            return
    except Exception as e:
        print(f"❌ Error during sync: {e}")
        return
    
    # Test 3: Check updated stats
    print("\n3. Checking updated vector store status...")
    try:
        response = requests.get(f"{base_url}/api/stats", timeout=10)
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Updated stats: {stats['stats']['documents']} documents")
            if stats['stats'].get('sample_documents'):
                print("Updated sample documents:")
                for doc in stats['stats']['sample_documents'][:3]:
                    print(f"  - {doc['title']} ({doc['url']})")
        else:
            print(f"❌ Failed to get updated stats: {response.status_code}")
    except Exception as e:
        print(f"❌ Error getting updated stats: {e}")
    
    # Test 4: Test search functionality
    print("\n4. Testing search functionality...")
    try:
        response = requests.get(
            f"{base_url}/api/search?q=example&top_k=3",
            timeout=10
        )
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Search successful: {len(result['results'])} results found")
            for i, item in enumerate(result['results'][:3], 1):
                print(f"  {i}. {item['title']} ({item['url']})")
        else:
            print(f"❌ Search failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error during search: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Vector store update test completed!")

if __name__ == "__main__":
    test_vector_store_update() 