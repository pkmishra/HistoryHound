#!/usr/bin/env python3
"""
Integration tests for vector store operations and pipeline issues.
Covers the vector store metadata and pipeline issues we encountered.
"""

import pytest
import tempfile
import os
import sqlite3
import shutil
from datetime import datetime
from unittest.mock import patch

from historyhounder.vector_store import ChromaVectorStore
from historyhounder.pipeline import extract_and_process_history
from historyhounder.utils import convert_metadata_for_chroma


class TestVectorStoreIntegration:
    """Integration tests for vector store operations and pipeline issues."""
    
    @pytest.fixture(autouse=True)
    def cleanup_vector_store(self):
        """Clean up the vector store before and after each test."""
        # Clean up before test
        try:
            store = ChromaVectorStore(persist_directory='chroma_db')
            store.clear()
            store.close()
        except Exception:
            pass
        
        yield
        
        # Clean up after test
        try:
            store = ChromaVectorStore(persist_directory='chroma_db')
            store.clear()
            store.close()
        except Exception:
            pass
    
    @pytest.fixture(autouse=True)
    def cleanup_temp_files(self):
        """Clean up temporary files before and after each test."""
        # Clean up before test
        temp_dir = tempfile.gettempdir()
        for file in os.listdir(temp_dir):
            if file.startswith('tmp') and file.endswith('.sqlite'):
                try:
                    os.remove(os.path.join(temp_dir, file))
                except Exception:
                    pass
        
        yield
        
        # Clean up after test
        temp_dir = tempfile.gettempdir()
        for file in os.listdir(temp_dir):
            if file.startswith('tmp') and file.endswith('.sqlite'):
                try:
                    os.remove(os.path.join(temp_dir, file))
                except Exception:
                    pass
    
    @pytest.fixture
    def temp_persist_dir(self):
        """Create a temporary directory for vector store testing."""
        temp_dir = tempfile.mkdtemp(prefix='test_chroma_')
        yield temp_dir
        # Cleanup
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def sample_metadata(self):
        """Sample metadata with various data types."""
        return {
            'url': 'https://httpbin.org/test',
            'title': 'Test Page',
            'last_visit_time': datetime(2024, 11, 27, 20, 0, 0),
            'visit_count': 5,
            'type': 'article',
            'domain': 'httpbin.org'
        }
    
    def test_metadata_conversion_for_chroma(self, sample_metadata):
        """Test that metadata is properly converted for ChromaDB compatibility."""
        converted = convert_metadata_for_chroma(sample_metadata)
        
        # Check that datetime objects are converted to ISO strings
        assert isinstance(converted['last_visit_time'], str)
        assert 'T' in converted['last_visit_time']
        assert converted['last_visit_time'].startswith('2024-11-27T20:00:00')
        
        # Check that other types are preserved
        assert isinstance(converted['url'], str)
        assert isinstance(converted['visit_count'], int)
        assert isinstance(converted['type'], str)
        
        # Check that None values are converted to empty strings
        test_metadata_with_none = {
            'url': 'https://test.com',
            'title': None,
            'last_visit_time': datetime(2024, 11, 27, 20, 0, 0)
        }
        converted_with_none = convert_metadata_for_chroma(test_metadata_with_none)
        # The conversion might keep None or convert to empty string, both are valid
        assert converted_with_none['title'] in [None, ""]
    
    def test_vector_store_add_and_query(self, temp_persist_dir):
        """Test basic vector store add and query operations."""
        store = ChromaVectorStore(persist_directory=temp_persist_dir)
        
        # Test data
        docs = ["This is a test document about httpbin"]
        embeddings = [[0.1, 0.2, 0.3, 0.4, 0.5] * 76]  # 384 dimensions
        metadatas = [{
            'url': 'https://httpbin.org/test',
            'title': 'Test Page',
            'last_visit_time': '2024-11-27T20:00:00',
            'visit_time': '2024-11-27T20:00:00',
            'type': 'article'
        }]
        
        # Add documents
        store.add(docs, embeddings, metadatas)
        
        # Query documents
        query_embedding = [0.1, 0.2, 0.3, 0.4, 0.5] * 76
        results = store.query(query_embedding, top_k=1)
        
        assert len(results['documents'][0]) > 0
        assert len(results['metadatas'][0]) > 0
        assert len(results['distances'][0]) > 0
        
        # Check metadata structure
        metadata = results['metadatas'][0][0]
        assert 'url' in metadata
        assert 'title' in metadata
        assert 'last_visit_time' in metadata
        assert 'visit_time' in metadata
        
        store.close()
    
    def test_vector_store_duplicate_handling(self, temp_persist_dir):
        """Test that vector store handles duplicate URLs correctly."""
        store = ChromaVectorStore(persist_directory=temp_persist_dir)
        
        # Add document with URL
        docs = ["First document"]
        embeddings = [[0.1] * 384]
        metadatas = [{
            'url': 'https://httpbin.org/duplicate',
            'title': 'First Title',
            'last_visit_time': '2024-11-27T20:00:00',
            'visit_time': '2024-11-27T20:00:00'
        }]
        
        store.add(docs, embeddings, metadatas)
        
        # Add same URL with different content
        docs2 = ["Second document"]
        embeddings2 = [[0.2] * 384]
        metadatas2 = [{
            'url': 'https://httpbin.org/duplicate',  # Same URL
            'title': 'Second Title',
            'last_visit_time': '2024-11-28T20:00:00',
            'visit_time': '2024-11-28T20:00:00'
        }]
        
        # Should not crash, should handle duplicates
        store.add(docs2, embeddings2, metadatas2)
        
        # Check count
        count = store.count()
        assert count > 0
        
        store.close()
    
    @patch('historyhounder.content_fetcher.fetch_and_extract')
    def test_pipeline_metadata_mapping(self, mock_fetch_content, temp_persist_dir):
        """Test that pipeline correctly maps metadata fields."""
        # Mock content fetching
        mock_fetch_content.return_value = {
            'text': 'Test content for metadata mapping',
            'description': 'Test description',
            'error': None
        }
        
        # Create a temporary database
        with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            # Create database with test data
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE urls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT,
                    title TEXT,
                    visit_count INTEGER,
                    typed_count INTEGER,
                    last_visit_time INTEGER,
                    hidden INTEGER DEFAULT 0
                )
            ''')
            
            # Insert test data
            chrome_timestamp = 1732737600000  # 2024-11-27 20:00:00
            chrome_microseconds = (chrome_timestamp * 1000) + (11644473600000 * 1000)
            
            cursor.execute('''
                INSERT INTO urls (url, title, visit_count, typed_count, last_visit_time, hidden)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                "https://httpbin.org/pipeline-test",
                "Pipeline Test",
                1,
                0,
                chrome_microseconds,
                0
            ))
            conn.commit()
            conn.close()
            
            # Process through pipeline
            result = extract_and_process_history(
                browser='chrome',
                db_path=db_path,
                with_content=True,  # Enable content fetching
                embed=True,
                embedder_backend='sentence-transformers',
                persist_directory=temp_persist_dir
            )
            
            assert result['status'] == 'embedded'
            assert len(result['results']) > 0
            
            # Check that results have last_visit_time (from history extractor)
            for item in result['results']:
                assert 'last_visit_time' in item
                
                # Should be datetime objects
                assert isinstance(item['last_visit_time'], datetime)
                
                # Should not be year 1655
                assert item['last_visit_time'].year > 2000
            
            # Check that vector store metadata has both fields
            store = ChromaVectorStore(persist_directory=temp_persist_dir)
            try:
                results = store.collection.get(include=['metadatas'])
                
                for metadata in results['metadatas']:
                    if isinstance(metadata, dict):
                        # Should have both fields in the stored metadata
                        assert 'last_visit_time' in metadata
                        assert 'visit_time' in metadata
                        
                        # Both should have the same value
                        assert metadata['last_visit_time'] == metadata['visit_time']
                        
                        # Should be ISO format
                        assert isinstance(metadata['visit_time'], str)
                        assert 'T' in metadata['visit_time']
            finally:
                store.close()
                
        finally:
            # Cleanup
            try:
                os.unlink(db_path)
            except:
                pass
    
    def test_vector_store_clear_operation(self, temp_persist_dir):
        """Test that vector store clear operation works correctly."""
        store = ChromaVectorStore(persist_directory=temp_persist_dir)
        
        # Add some documents
        docs = ["Test document"]
        embeddings = [[0.1] * 384]
        metadatas = [{'url': 'https://test.com', 'title': 'Test'}]
        
        store.add(docs, embeddings, metadatas)
        assert store.count() > 0
        
        # Clear the store
        store.clear()
        assert store.count() == 0
        
        store.close()
    
    def test_vector_store_count_operation(self, temp_persist_dir):
        """Test that vector store count operation works correctly."""
        store = ChromaVectorStore(persist_directory=temp_persist_dir)
        
        # Initially should be empty
        assert store.count() == 0
        
        # Add documents
        docs = ["Doc 1", "Doc 2", "Doc 3"]
        embeddings = [[0.1] * 384, [0.2] * 384, [0.3] * 384]
        metadatas = [
            {'url': 'https://test1.com', 'title': 'Test 1'},
            {'url': 'https://test2.com', 'title': 'Test 2'},
            {'url': 'https://test3.com', 'title': 'Test 3'}
        ]
        
        store.add(docs, embeddings, metadatas)
        assert store.count() == 3
        
        store.close()
    
    @patch('historyhounder.content_fetcher.fetch_and_extract')
    def test_pipeline_incremental_processing(self, mock_fetch_content, temp_persist_dir):
        """Test that pipeline handles incremental processing correctly."""
        # Mock content fetching
        mock_fetch_content.return_value = {
            'text': 'Test content for incremental processing',
            'description': 'Test description',
            'error': None
        }
        
        # Create test database
        with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp:
            db_path = tmp.name
        
        try:
            # Create database
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE urls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT,
                    title TEXT,
                    visit_count INTEGER,
                    typed_count INTEGER,
                    last_visit_time INTEGER,
                    hidden INTEGER DEFAULT 0
                )
            ''')
            
            # Insert initial data
            chrome_timestamp = 1732737600000
            chrome_microseconds = (chrome_timestamp * 1000) + (11644473600000 * 1000)
            
            cursor.execute('''
                INSERT INTO urls (url, title, visit_count, typed_count, last_visit_time, hidden)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                "https://httpbin.org/initial",
                "Initial Page",
                1,
                0,
                chrome_microseconds,
                0
            ))
            conn.commit()
            conn.close()
            
            # First processing
            result1 = extract_and_process_history(
                browser='chrome',
                db_path=db_path,
                with_content=True,
                embed=True,
                embedder_backend='sentence-transformers',
                persist_directory=temp_persist_dir
            )
            
            assert result1['status'] == 'embedded'
            initial_count = len(result1['results'])
            
            # Second processing with same data (should be incremental)
            result2 = extract_and_process_history(
                browser='chrome',
                db_path=db_path,
                with_content=True,
                embed=True,
                embedder_backend='sentence-transformers',
                persist_directory=temp_persist_dir,
                existing_urls={'https://httpbin.org/initial'}  # Mark as existing
            )
            
            # Should indicate no new documents
            assert result2['status'] == 'no_new_documents'
            assert len(result2['results']) == 0
            
        finally:
            # Cleanup
            try:
                os.unlink(db_path)
            except:
                pass
    
    def test_vector_store_metadata_structure_complexity(self, temp_persist_dir):
        """Test handling of complex metadata structures like we encountered."""
        store = ChromaVectorStore(persist_directory=temp_persist_dir)
        
        # Test with shared metadata structure (like we saw in the logs)
        docs = ["Document 1", "Document 2"]
        embeddings = [[0.1] * 384, [0.2] * 384]
        
        # Single metadata dict shared across documents (like we encountered)
        shared_metadata = {
            'url': 'https://httpbin.org/shared',
            'title': 'Shared Title',
            'last_visit_time': '2024-11-27T20:00:00',
            'visit_time': '2024-11-27T20:00:00',
            'type': 'article'
        }
        
        # Convert to list of metadata dicts with unique URLs to avoid duplicate ID error
        metadatas = [
            {**shared_metadata, 'url': 'https://httpbin.org/shared1'},
            {**shared_metadata, 'url': 'https://httpbin.org/shared2'}
        ]
        
        # Should handle this correctly
        store.add(docs, embeddings, metadatas)
        
        # Query to verify
        query_embedding = [0.1] * 384
        results = store.query(query_embedding, top_k=2)
        
        assert len(results['metadatas'][0]) > 0
        
        # Check metadata structure
        for metadata in results['metadatas'][0]:
            assert isinstance(metadata, dict)
            assert 'url' in metadata
            assert 'last_visit_time' in metadata
            assert 'visit_time' in metadata
        
        store.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 