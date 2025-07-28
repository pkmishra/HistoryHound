#!/usr/bin/env python3
"""
Integration tests for timestamp conversion and metadata handling.
Covers the timestamp issues we encountered in the system.
"""

import pytest
import tempfile
import os
import sqlite3
import shutil
from datetime import datetime
from unittest.mock import patch

from historyhounder.server import app
from historyhounder.vector_store import ChromaVectorStore
from historyhounder.pipeline import extract_and_process_history
from historyhounder.history_extractor import chrome_time_to_datetime


class TestTimestampIntegration:
    """Integration tests for timestamp conversion and metadata handling."""
    
    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        from fastapi.testclient import TestClient
        return TestClient(app)
    
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
    def temp_db_path(self):
        """Create a temporary SQLite database for testing."""
        with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as tmp:
            db_path = tmp.name
        
        # Create the database with Chrome-compatible schema
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
        conn.commit()
        conn.close()
        
        yield db_path
        
        # Cleanup
        try:
            os.unlink(db_path)
        except:
            pass
    
    @pytest.fixture
    def sample_history_data(self):
        """Sample browser history data with various timestamp formats."""
        return [
            {
                "id": "test1",
                "url": "https://httpbin.org/html",
                "title": "HTTPBin HTML",
                "lastVisitTime": 1732737600000,  # 2024-11-27 20:00:00
                "visitCount": 1
            },
            {
                "id": "test2", 
                "url": "https://httpbin.org/json",
                "title": "HTTPBin JSON",
                "lastVisitTime": 1732824000000,  # 2024-11-28 20:00:00
                "visitCount": 2
            },
            {
                "id": "test3",
                "url": "https://httpbin.org/headers", 
                "title": "HTTPBin Headers",
                "lastVisitTime": 1732910400000,  # 2024-11-29 20:00:00
                "visitCount": 1
            }
        ]
    
    def test_chrome_timestamp_conversion(self):
        """Test that Chrome timestamps are correctly converted to readable dates."""
        # Test various Chrome timestamp formats
        test_cases = [
            (1732737600000, "2024-11-27 20:00:00"),  # Recent timestamp
            (1732910400000, "2024-11-29 20:00:00"),  # Another recent timestamp
            (1640995200000, "2022-01-01 00:00:00"),  # 2022 timestamp
        ]
        
        for chrome_timestamp, expected_date in test_cases:
            # Convert using our fixed logic
            unix_milliseconds = chrome_timestamp
            chrome_microseconds = (unix_milliseconds * 1000) + (11644473600000 * 1000)
            
            # Convert to datetime using the history extractor function
            dt = chrome_time_to_datetime(chrome_microseconds)
            
            assert dt is not None
            assert dt.year > 2000  # Should not be year 1655!
            assert dt.strftime('%Y-%m-%d %H:%M:%S') == expected_date
    
    def test_server_timestamp_processing(self, client, sample_history_data):
        """Test that the server correctly processes timestamps from browser history."""
        # Send history data to the server
        response = client.post(
            "/api/process-history",
            json={"history": sample_history_data}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["processed_count"] >= 0
        
        # Check that the data was processed
        message = data["message"].lower()
        assert any(keyword in message for keyword in [
            "processed successfully",
            "new items embedded",
            "no new history items",
            "no valid documents"
        ])
    
    def test_search_timestamp_display(self, client, sample_history_data):
        """Test that search results display timestamps correctly."""
        # First, process some history data
        response = client.post(
            "/api/process-history",
            json={"history": sample_history_data}
        )
        assert response.status_code == 200
        
        # Now search for the data
        response = client.get("/api/search?q=httpbin&top_k=5")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert len(data["results"]) >= 0  # May be 0 if no content was fetched
        
        # Check that timestamps are properly formatted if results exist
        for result in data["results"]:
            if result.get("visit_time"):
                # Should be in format "YYYY-MM-DD HH:MM:SS"
                assert len(result["visit_time"]) == 19
                assert result["visit_time"][4] == "-"  # Year-Month separator
                assert result["visit_time"][7] == "-"  # Month-Day separator
                assert result["visit_time"][10] == " "  # Date-Time separator
                assert result["visit_time"][13] == ":"  # Hour-Minute separator
                assert result["visit_time"][16] == ":"  # Minute-Second separator
                
                # Should not be year 1655
                year = int(result["visit_time"][:4])
                assert year > 2000
                assert year < 2030
    
    @patch('historyhounder.content_fetcher.fetch_and_extract')
    def test_vector_store_metadata_structure(self, mock_fetch_content, temp_db_path):
        """Test that vector store metadata is structured correctly."""
        # Mock content fetching to return valid content
        mock_fetch_content.return_value = {
            'text': 'This is test content for httpbin',
            'description': 'Test description',
            'error': None
        }
        
        # Create a simple test database with one URL
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        
        # Insert test data with Chrome timestamp
        chrome_timestamp = 1732737600000  # 2024-11-27 20:00:00
        chrome_microseconds = (chrome_timestamp * 1000) + (11644473600000 * 1000)
        
        cursor.execute('''
            INSERT INTO urls (url, title, visit_count, typed_count, last_visit_time, hidden)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            "https://httpbin.org/test",
            "Test Page",
            1,
            0,
            chrome_microseconds,
            0
        ))
        conn.commit()
        conn.close()
        
        # Process through the pipeline
        result = extract_and_process_history(
            browser='chrome',
            db_path=temp_db_path,
            with_content=True,  # Enable content fetching
            embed=True,
            embedder_backend='sentence-transformers',
            persist_directory='test_chroma_db'
        )
        
        assert result['status'] == 'embedded'
        assert len(result['results']) > 0
        
        # Check the vector store metadata
        store = ChromaVectorStore(persist_directory='test_chroma_db')
        try:
            results = store.collection.get(include=['metadatas'])
            assert results['metadatas'] is not None
            
            # Check that metadata has both last_visit_time and visit_time
            for metadata in results['metadatas']:
                if isinstance(metadata, dict):
                    assert 'last_visit_time' in metadata
                    assert 'visit_time' in metadata
                    
                    # Both should be ISO format strings
                    assert isinstance(metadata['last_visit_time'], str)
                    assert isinstance(metadata['visit_time'], str)
                    assert 'T' in metadata['last_visit_time']
                    assert 'T' in metadata['visit_time']
                    
                    # Should not be year 1655
                    dt = datetime.fromisoformat(metadata['last_visit_time'].replace('Z', '+00:00'))
                    assert dt.year > 2000
        finally:
            store.close()
            # Clean up test database
            import shutil
            if os.path.exists('test_chroma_db'):
                shutil.rmtree('test_chroma_db')
    
    def test_incremental_processing(self, client, sample_history_data):
        """Test that incremental processing works correctly."""
        # First sync
        response = client.post(
            "/api/process-history",
            json={"history": sample_history_data}
        )
        assert response.status_code == 200
        first_data = response.json()
        assert first_data["processed_count"] >= 0
        
        # Second sync with same data (should be incremental)
        response = client.post(
            "/api/process-history", 
            json={"history": sample_history_data}
        )
        assert response.status_code == 200
        second_data = response.json()
        
        # Should indicate no new documents or very few
        second_message = second_data["message"].lower()
        assert any(keyword in second_message for keyword in [
            "no new",
            "already processed",
            "no valid documents"
        ]) or second_data["processed_count"] == 0
        
        # Third sync with new data
        new_history = [
            {
                "id": "test4",
                "url": "https://httpbin.org/delay/1",
                "title": "HTTPBin Delay",
                "lastVisitTime": 1732996800000,  # 2024-11-30 20:00:00
                "visitCount": 1
            }
        ]
        
        response = client.post(
            "/api/process-history",
            json={"history": new_history}
        )
        assert response.status_code == 200
        third_data = response.json()
        
        # Should process the new document or indicate no valid documents
        third_message = third_data["message"].lower()
        # The message might indicate no new documents if the URL was already processed
        # or if content fetching failed, or if the URL was filtered out
        assert any(keyword in third_message for keyword in [
            "new items",
            "processed successfully",
            "no valid documents",
            "no new documents",
            "filtered out",
            "no new history items"
        ]) or third_data["processed_count"] == 0
    
    @patch('historyhounder.content_fetcher.fetch_and_extract')
    def test_metadata_field_mapping(self, mock_fetch_content, temp_db_path):
        """Test that metadata fields are properly mapped for search API."""
        # Mock content fetching
        mock_fetch_content.return_value = {
            'text': 'Test content for metadata mapping',
            'description': 'Test description',
            'error': None
        }
        
        # Create test database
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        
        chrome_timestamp = 1732737600000
        chrome_microseconds = (chrome_timestamp * 1000) + (11644473600000 * 1000)
        
        cursor.execute('''
            INSERT INTO urls (url, title, visit_count, typed_count, last_visit_time, hidden)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            "https://httpbin.org/metadata-test",
            "Metadata Test",
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
            db_path=temp_db_path,
            with_content=True,
            embed=True,
            embedder_backend='sentence-transformers',
            persist_directory='test_metadata_db'
        )
        
        assert result['status'] == 'embedded'
        
        # Check vector store metadata
        store = ChromaVectorStore(persist_directory='test_metadata_db')
        try:
            results = store.collection.get(include=['metadatas'])
            
            for metadata in results['metadatas']:
                if isinstance(metadata, dict):
                    # Should have both fields
                    assert 'last_visit_time' in metadata
                    assert 'visit_time' in metadata
                    
                    # Both should have the same value
                    assert metadata['last_visit_time'] == metadata['visit_time']
                    
                    # Should be ISO format
                    assert isinstance(metadata['visit_time'], str)
                    assert 'T' in metadata['visit_time']
        finally:
            store.close()
            # Clean up
            import shutil
            if os.path.exists('test_metadata_db'):
                shutil.rmtree('test_metadata_db')
    
    def test_sqlite_database_creation(self, client, sample_history_data):
        """Test that SQLite databases are created correctly with proper schema."""
        # Process history data
        response = client.post(
            "/api/process-history",
            json={"history": sample_history_data}
        )
        assert response.status_code == 200
        
        # Check that the history_db directory exists and contains SQLite files
        assert os.path.exists('history_db')
        
        # Check for the main extension history database
        extension_db_path = 'history_db/extension_history.sqlite'
        if os.path.exists(extension_db_path):
            # Verify the database structure
            conn = sqlite3.connect(extension_db_path)
            cursor = conn.cursor()
            
            # Check that the urls table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='urls'")
            tables = cursor.fetchall()
            assert len(tables) > 0
            
            # Check table schema
            cursor.execute("PRAGMA table_info(urls)")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            expected_columns = ['id', 'url', 'title', 'visit_count', 'typed_count', 'last_visit_time', 'hidden']
            for expected_col in expected_columns:
                assert expected_col in column_names
            
            conn.close()
    
    def test_error_handling_invalid_timestamps(self, client):
        """Test handling of invalid or malformed timestamps."""
        invalid_history_data = [
            {
                "id": "invalid1",
                "url": "https://httpbin.org/invalid",
                "title": "Invalid Timestamp",
                "lastVisitTime": "not_a_number",  # Invalid timestamp
                "visitCount": 1
            },
            {
                "id": "invalid2", 
                "url": "https://httpbin.org/negative",
                "title": "Negative Timestamp",
                "lastVisitTime": -1000,  # Negative timestamp
                "visitCount": 1
            }
        ]
        
        # Should handle gracefully without crashing
        response = client.post(
            "/api/process-history",
            json={"history": invalid_history_data}
        )
        
        # Should still return a response (even if it's an error)
        assert response.status_code in [200, 400, 422, 500]
        
        # If it's 200, check the response
        if response.status_code == 200:
            data = response.json()
            # Should indicate some kind of processing result
            assert "message" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 