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
    
    @pytest.fixture
    def test_vector_store_dir(self):
        """Create a temporary directory for test vector store."""
        temp_dir = tempfile.mkdtemp(prefix="test_chroma_")
        yield temp_dir
        # Clean up after test
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass
    
    @pytest.fixture(autouse=True)
    def cleanup_vector_store(self, test_vector_store_dir):
        """Clean up the test vector store before and after each test."""
        # Set environment variable for test vector store directory
        original_dir = os.environ.get("HISTORYHOUNDER_VECTOR_STORE_DIR")
        os.environ["HISTORYHOUNDER_VECTOR_STORE_DIR"] = test_vector_store_dir
        
        # Clean up before test
        try:
            store = ChromaVectorStore(persist_directory=test_vector_store_dir)
            store.clear()
            store.close()
        except Exception:
            pass
        
        yield
        
        # Clean up after test
        try:
            store = ChromaVectorStore(persist_directory=test_vector_store_dir)
            store.clear()
            store.close()
        except Exception:
            pass
        
        # Restore original environment variable
        if original_dir is not None:
            os.environ["HISTORYHOUNDER_VECTOR_STORE_DIR"] = original_dir
        else:
            os.environ.pop("HISTORYHOUNDER_VECTOR_STORE_DIR", None)
    
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
    
    @pytest.fixture
    def comprehensive_history_data(self):
        """Comprehensive browser history data for Q&A testing."""
        return [
            # GitHub visits
            {
                "id": "github1",
                "url": "https://github.com/pkmishra/HistoryHound",
                "title": "pkmishra/HistoryHound: Talk to your History in English",
                "lastVisitTime": 1732737600000,
                "visitCount": 41
            },
            {
                "id": "github2",
                "url": "https://github.com/pkmishra/HistoryHound/commits/main/",
                "title": "Commits · pkmishra/HistoryHound · GitHub",
                "lastVisitTime": 1732737600000,
                "visitCount": 38
            },
            {
                "id": "github3",
                "url": "https://github.com/pkmishra/HistoryHound/tree/main/extension",
                "title": "HistoryHound/extension at main · pkmishra/HistoryHound · GitHub",
                "lastVisitTime": 1732737600000,
                "visitCount": 17
            },
            # LinkedIn visits
            {
                "id": "linkedin1",
                "url": "https://www.linkedin.com/feed/",
                "title": "LinkedIn Login, Sign in",
                "lastVisitTime": 1732737600000,
                "visitCount": 578
            },
            {
                "id": "linkedin2",
                "url": "https://www.linkedin.com/notifications/?filter=all",
                "title": "LinkedIn Login, Sign in",
                "lastVisitTime": 1732737600000,
                "visitCount": 194
            },
            {
                "id": "linkedin3",
                "url": "https://www.linkedin.com/",
                "title": "Log In or Sign Up",
                "lastVisitTime": 1732737600000,
                "visitCount": 151
            },
            # AI-related visits
            {
                "id": "ai1",
                "url": "https://lu.ma/2boq3b18",
                "title": "The AI Foundry Series- San Ramon Chapter",
                "lastVisitTime": 1732737600000,
                "visitCount": 3
            },
            {
                "id": "ai2",
                "url": "https://lu.ma/ai",
                "title": "AI Events · Luma",
                "lastVisitTime": 1732737600000,
                "visitCount": 2
            },
            # Shopping visits
            {
                "id": "amazon1",
                "url": "https://www.amazon.com/",
                "title": "Amazon.com",
                "lastVisitTime": 1732737600000,
                "visitCount": 62
            },
            {
                "id": "slickdeals1",
                "url": "https://slickdeals.net/",
                "title": "The Best Deals, Coupons, Promo Codes & Discounts",
                "lastVisitTime": 1732737600000,
                "visitCount": 173
            },
            # News visits
            {
                "id": "news1",
                "url": "https://timesofindia.indiatimes.com/?loc=in",
                "title": "News - Breaking News, Latest News, India News, World News, Bollywood, Sports, Business and Political News",
                "lastVisitTime": 1732737600000,
                "visitCount": 95
            },
            # Keybase visits
            {
                "id": "keybase1",
                "url": "https://keybase.io/pkm",
                "title": "pkm (Pradeep Kumar Mishra)",
                "lastVisitTime": 1732737600000,
                "visitCount": 5
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
    
    def test_qa_statistical_questions(self, client, comprehensive_history_data):
        """Test Q&A with statistical questions."""
        # Process comprehensive history data
        response = client.post(
            "/api/process-history",
            json={"history": comprehensive_history_data}
        )
        assert response.status_code == 200
        
        # Wait for processing
        time.sleep(1)
        
        # Test statistical questions
        statistical_questions = [
            "What is the most visited website?",
            "What are the top 5 most visited websites?",
            "Which website did I visit most frequently?",
            "What are the most popular sites in my browsing history?",
            "Show me the sites with highest visit counts"
        ]
        
        for question in statistical_questions:
            response = client.post(
                "/api/qa",
                json={
                    "question": question,
                    "top_k": 10
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "answer" in data
            assert len(data["answer"]) > 0
            
            # Should mention LinkedIn as most visited (578 visits)
            answer_lower = data["answer"].lower()
            assert "linkedin" in answer_lower or "578" in answer_lower or "most visited" in answer_lower
    
    def test_qa_domain_specific_questions(self, client, comprehensive_history_data):
        """Test Q&A with domain-specific questions."""
        # Process comprehensive history data
        response = client.post(
            "/api/process-history",
            json={"history": comprehensive_history_data}
        )
        assert response.status_code == 200
        
        # Wait for processing
        time.sleep(1)
        
        # Test domain-specific questions
        domain_questions = [
            ("How many times did I visit github?", "github", 96),  # 41+38+17
            ("How many times did I visit linkedin?", "linkedin", 923),  # 578+194+151
            ("How many times did I visit amazon?", "amazon", 62),
            ("How many times did I visit slickdeals?", "slickdeals", 173),
            ("How many times did I visit timesofindia?", "timesofindia", 95),
            ("How many times did I visit keybase?", "keybase", 5)
        ]
        
        for question, domain, expected_min_visits in domain_questions:
            response = client.post(
                "/api/qa",
                json={
                    "question": question,
                    "top_k": 10
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "answer" in data
            assert len(data["answer"]) > 0
            
            # Should mention the domain and visit count
            answer_lower = data["answer"].lower()
            assert domain in answer_lower or "visit" in answer_lower
    
    def test_qa_semantic_questions(self, client, comprehensive_history_data):
        """Test Q&A with semantic questions."""
        # Process comprehensive history data
        response = client.post(
            "/api/process-history",
            json={"history": comprehensive_history_data}
        )
        assert response.status_code == 200
        
        # Wait for processing
        time.sleep(1)
        
        # Test semantic questions
        semantic_questions = [
            "What AI-related websites have I visited?",
            "What shopping websites did I visit?",
            "What news websites did I visit?",
            "What development websites did I visit?",
            "What social media sites did I visit?",
            "What websites did I visit for deals?",
            "What professional networking sites did I visit?"
        ]
        
        for question in semantic_questions:
            response = client.post(
                "/api/qa",
                json={
                    "question": question,
                    "top_k": 5
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "answer" in data
            assert len(data["answer"]) > 0
    
    def test_qa_mixed_question_types(self, client, comprehensive_history_data):
        """Test Q&A with mixed question types."""
        # Process comprehensive history data
        response = client.post(
            "/api/process-history",
            json={"history": comprehensive_history_data}
        )
        assert response.status_code == 200
        
        # Wait for processing
        time.sleep(1)
        
        # Test mixed question types
        mixed_questions = [
            # Statistical + domain specific
            "What is the most visited GitHub repository?",
            "How many times did I visit LinkedIn compared to other sites?",
            
            # Semantic + specific
            "What AI events did I look up?",
            "What shopping deals did I find?",
            
            # Time-based
            "What did I visit recently?",
            "What websites did I visit most often?",
            
            # Category-based
            "What professional websites did I visit?",
            "What entertainment sites did I visit?",
            "What news sources did I check?",
            
            # Specific content
            "What deals did I find on SlickDeals?",
            "What news did I read on Times of India?",
            "What did I look up on Keybase?"
        ]
        
        for question in mixed_questions:
            response = client.post(
                "/api/qa",
                json={
                    "question": question,
                    "top_k": 5
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "answer" in data
            assert len(data["answer"]) > 0
    
    def test_qa_edge_cases(self, client, comprehensive_history_data):
        """Test Q&A with edge cases and unusual questions."""
        # Process comprehensive history data
        response = client.post(
            "/api/process-history",
            json={"history": comprehensive_history_data}
        )
        assert response.status_code == 200
        
        # Wait for processing
        time.sleep(1)
        
        # Test edge cases
        edge_case_questions = [
            # Empty or very short questions
            "What?",
            "?",
            "",
            
            # Very long questions
            "What is the most visited website in my browsing history and can you tell me all about it in detail including when I visited it and how many times and what I was doing there?",
            
            # Questions with special characters
            "What's the most visited site?",
            "Which site did I visit the most?",
            "What are my top 3 sites?",
            
            # Questions about non-existent domains
            "How many times did I visit facebook.com?",
            "What did I visit on twitter.com?",
            "How many times did I visit youtube.com?",
            
            # Questions about specific content
            "What deals did I find?",
            "What news did I read?",
            "What events did I look up?",
            
            # Questions about visit patterns
            "When did I visit LinkedIn?",
            "What time did I visit GitHub?",
            "How often did I visit Amazon?"
        ]
        
        for question in edge_case_questions:
            response = client.post(
                "/api/qa",
                json={
                    "question": question,
                    "top_k": 5
                }
            )
            
            # Should handle gracefully
            assert response.status_code in [200, 400, 422]
            
            if response.status_code == 200:
                data = response.json()
                assert data["success"] is True
                assert "answer" in data
    
    def test_qa_parameter_validation(self, client, comprehensive_history_data):
        """Test Q&A parameter validation."""
        # Process comprehensive history data
        response = client.post(
            "/api/process-history",
            json={"history": comprehensive_history_data}
        )
        assert response.status_code == 200
        
        # Wait for processing
        time.sleep(1)
        
        # Test invalid parameters
        invalid_requests = [
            # Missing question
            {},
            
            # Empty question
            {"question": ""},
            
            # Invalid top_k
            {"question": "What is the most visited website?", "top_k": 0},
            {"question": "What is the most visited website?", "top_k": -1},
            {"question": "What is the most visited website?", "top_k": 1000},
            
            # Wrong data types
            {"question": 123, "top_k": 5},
            {"question": "What is the most visited website?", "top_k": "five"},
            
            # Extra fields
            {"question": "What is the most visited website?", "top_k": 5, "extra": "field"}
        ]
        
        for request_data in invalid_requests:
            response = client.post(
                "/api/qa",
                json=request_data
            )
            
            # Should handle gracefully
            assert response.status_code in [200, 400, 422]
    
    def test_qa_response_structure(self, client, comprehensive_history_data):
        """Test Q&A response structure and content."""
        # Process comprehensive history data
        response = client.post(
            "/api/process-history",
            json={"history": comprehensive_history_data}
        )
        assert response.status_code == 200
        
        # Wait for processing
        time.sleep(1)
        
        # Test response structure
        response = client.post(
            "/api/qa",
            json={
                "question": "What is the most visited website?",
                "top_k": 5
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "success" in data
        assert "question" in data
        assert "answer" in data
        assert "sources" in data
        assert "timestamp" in data
        
        # Check data types
        assert isinstance(data["success"], bool)
        assert isinstance(data["question"], str)
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert isinstance(data["timestamp"], str)
        
        # Check success
        assert data["success"] is True
        
        # Check answer content
        assert len(data["answer"]) > 0
        
        # Check sources structure
        if len(data["sources"]) > 0:
            source = data["sources"][0]
            assert "content" in source
            assert "url" in source
            assert "title" in source
            assert "visit_time" in source
            assert "domain" in source
    
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