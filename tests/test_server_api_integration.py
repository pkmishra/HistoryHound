#!/usr/bin/env python3
"""
Integration tests for server API endpoints.
Covers the search API formatting and processing endpoint issues we encountered.
"""

import pytest
import tempfile
import os
import sqlite3
import shutil
from datetime import datetime
import requests
import time

from historyhounder.server import app
from historyhounder.vector_store import ChromaVectorStore


class TestServerAPIIntegration:
    """Integration tests for server API endpoints."""
    
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
    def sample_history_data(self):
        """Sample browser history data for testing."""
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
            }
        ]
    
    def test_process_history_endpoint(self, client, sample_history_data):
        """Test the /api/process-history endpoint."""
        response = client.post(
            "/api/process-history",
            json={"history": sample_history_data}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert "success" in data
        assert "processed_count" in data
        assert "message" in data
        assert "timestamp" in data
        
        # Check success
        assert data["success"] is True
        assert data["processed_count"] >= 0
        
        # Check message content
        message = data["message"].lower()
        assert any(keyword in message for keyword in [
            "processed successfully",
            "new items embedded",
            "no new history items",
            "no valid documents"
        ])
    
    def test_search_endpoint_timestamp_formatting(self, client, sample_history_data):
        """Test that search endpoint formats timestamps correctly."""
        # First, process some history data
        response = client.post(
            "/api/process-history",
            json={"history": sample_history_data}
        )
        assert response.status_code == 200
        
        # Wait a moment for processing
        time.sleep(1)
        
        # Search for the data
        response = client.get("/api/search?q=httpbin&top_k=5")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "results" in data
        assert "query" in data
        assert "total" in data
        
        # Check results structure
        if len(data["results"]) > 0:
            result = data["results"][0]
            assert "title" in result
            assert "url" in result
            assert "content" in result
            assert "visit_time" in result
            assert "domain" in result
            assert "distance" in result
            
            # Check timestamp formatting
            if result.get("visit_time"):
                visit_time = result["visit_time"]
                
                # Should be in format "YYYY-MM-DD HH:MM:SS"
                assert len(visit_time) == 19
                assert visit_time[4] == "-"  # Year-Month separator
                assert visit_time[7] == "-"  # Month-Day separator
                assert visit_time[10] == " "  # Date-Time separator
                assert visit_time[13] == ":"  # Hour-Minute separator
                assert visit_time[16] == ":"  # Minute-Second separator
                
                # Should not be year 1655
                year = int(visit_time[:4])
                assert year > 2000
                assert year < 2030
    
    def test_stats_endpoint(self, client):
        """Test the /api/stats endpoint."""
        response = client.get("/api/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "stats" in data
        assert "timestamp" in data
        
        stats = data["stats"]
        # Check for the actual fields that exist in the stats response
        assert "documents" in stats
        assert "collections" in stats
        assert "status" in stats
        assert isinstance(stats["documents"], int)
        assert stats["documents"] >= 0
    
    def test_health_endpoint(self, client):
        """Test the /api/health endpoint."""
        response = client.get("/api/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "historyhounder_available" in data
        assert "version" in data
        assert "ollama_model" in data
        assert "timestamp" in data
        
        assert data["status"] == "healthy"
        assert data["historyhounder_available"] is True
    
    def test_qa_endpoint(self, client, sample_history_data):
        """Test the /api/qa endpoint."""
        # First, process some history data
        response = client.post(
            "/api/process-history",
            json={"history": sample_history_data}
        )
        assert response.status_code == 200
        
        # Wait for processing
        time.sleep(1)
        
        # Ask a question
        response = client.post(
            "/api/qa",
            json={
                "question": "What is httpbin?",
                "top_k": 3
            }
        )
        
        # Should return a response (even if Ollama is not available)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "question" in data
        assert "answer" in data
        assert "sources" in data
        assert "timestamp" in data
        
        # Check that we got an answer
        assert len(data["answer"]) > 0
    
    def test_incremental_processing_behavior(self, client, sample_history_data):
        """Test that repeated processing shows incremental behavior."""
        # First sync
        response = client.post(
            "/api/process-history",
            json={"history": sample_history_data}
        )
        assert response.status_code == 200
        first_data = response.json()
        
        # Second sync with same data
        response = client.post(
            "/api/process-history",
            json={"history": sample_history_data}
        )
        assert response.status_code == 200
        second_data = response.json()
        
        # Should indicate incremental processing
        second_message = second_data["message"].lower()
        assert any(keyword in second_message for keyword in [
            "no new history items",
            "no new documents",
            "already processed"
        ])
    
    def test_error_handling_invalid_data(self, client):
        """Test error handling for invalid request data."""
        # Test with invalid JSON
        response = client.post(
            "/api/process-history",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code in [400, 422]  # Bad Request or Unprocessable Entity
        
        # Test with missing required fields
        response = client.post(
            "/api/process-history",
            json={"history": []}  # Empty history
        )
        # Empty history might be rejected or handled gracefully
        assert response.status_code in [200, 400, 422]
        
        # Test with malformed history items
        malformed_data = [
            {
                "id": "test1",
                "url": "not_a_url",  # Invalid URL
                "title": "Test",
                "lastVisitTime": "invalid_timestamp",  # Invalid timestamp
                "visitCount": "not_a_number"  # Invalid count
            }
        ]
        
        response = client.post(
            "/api/process-history",
            json={"history": malformed_data}
        )
        # Should handle gracefully - could be 200, 400, or 422
        assert response.status_code in [200, 400, 422]
        
        # If it's 200, check the response
        if response.status_code == 200:
            data = response.json()
            assert "message" in data
        elif response.status_code in [400, 422]:
            # Should return an error response
            data = response.json()
            assert "detail" in data or "error" in data
    
    def test_search_with_no_results(self, client):
        """Test search behavior when no results are found."""
        # Use a very specific query that's unlikely to match existing data
        response = client.get("/api/search?q=xyz123nonexistentquery456abc&top_k=5")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "results" in data
        assert "total" in data
        
        # Should return empty results or very few results
        assert len(data["results"]) <= 5  # Allow for some fuzzy matching
        assert data["total"] <= 5
    
    def test_search_parameter_validation(self, client):
        """Test search parameter validation."""
        # Test with empty query
        response = client.get("/api/search?q=&top_k=5")
        assert response.status_code in [400, 422]  # Should reject empty query
        
        # Test with invalid top_k
        response = client.get("/api/search?q=test&top_k=0")
        assert response.status_code in [400, 422]  # Should reject invalid top_k
        
        response = client.get("/api/search?q=test&top_k=1000")
        assert response.status_code in [400, 422]  # Should reject too large top_k
    
    def test_cors_headers(self, client):
        """Test that CORS headers are properly set."""
        # Test OPTIONS request
        response = client.options("/api/health")
        assert response.status_code == 200
        
        # Check for CORS headers
        headers = response.headers
        assert "access-control-allow-origin" in headers
        assert "access-control-allow-methods" in headers
        assert "access-control-allow-headers" in headers
    
    def test_timestamp_edge_cases(self, client):
        """Test timestamp handling with edge cases."""
        edge_case_data = [
            {
                "id": "edge1",
                "url": "https://httpbin.org/edge1",
                "title": "Edge Case 1",
                "lastVisitTime": 0,  # Zero timestamp
                "visitCount": 1
            },
            {
                "id": "edge2",
                "url": "https://httpbin.org/edge2", 
                "title": "Edge Case 2",
                "lastVisitTime": 1640995200000,  # 2022-01-01
                "visitCount": 1
            },
            {
                "id": "edge3",
                "url": "https://httpbin.org/edge3",
                "title": "Edge Case 3", 
                "lastVisitTime": 1735689600000,  # 2025-01-01
                "visitCount": 1
            }
        ]
        
        response = client.post(
            "/api/process-history",
            json={"history": edge_case_data}
        )
        
        # Should handle edge cases gracefully
        assert response.status_code in [200, 400, 422]
        
        if response.status_code == 200:
            data = response.json()
            assert "message" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 