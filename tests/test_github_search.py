#!/usr/bin/env python3
"""
Test script to check GitHub URLs in the database
"""

import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from historyhounder.vector_store import ChromaVectorStore

def test_github_urls():
    """Test what GitHub URLs are in the database"""
    print("=== Testing GitHub URLs in Database ===")
    
    store = ChromaVectorStore(persist_directory='chroma_db')
    collection = store.collection
    
    if collection:
        all_results = collection.get()
        if all_results and all_results['documents']:
            github_urls = []
            for i, (doc, meta) in enumerate(zip(all_results['documents'], all_results['metadatas'])):
                url = meta.get('url', '')
                if 'github.com' in url:
                    visit_count = meta.get('visit_count', 1)
                    title = meta.get('title', 'No title')
                    github_urls.append({
                        'url': url,
                        'title': title,
                        'visit_count': visit_count,
                        'content': doc[:100] + '...' if len(doc) > 100 else doc
                    })
            
            print(f"Found {len(github_urls)} GitHub URLs:")
            for i, item in enumerate(github_urls, 1):
                print(f"{i}. {item['title']}")
                print(f"   URL: {item['url']}")
                print(f"   Visits: {item['visit_count']}")
                print(f"   Content: {item['content']}")
                print()
        else:
            print("No documents found in collection")
    else:
        print("No collection found")

if __name__ == "__main__":
    test_github_urls() 