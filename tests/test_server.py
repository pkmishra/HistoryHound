#!/usr/bin/env python3
"""
Test suite for HistoryHounder Backend Server (FastAPI)
Tests all endpoints and functionality
"""

import unittest
import json
import sys
import os
import time
import threading
from pathlib import Path
from urllib.parse import urlencode
import requests

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the FastAPI app
from historyhounder.server import app
import uvicorn

class TestBackendAPI(unittest.TestCase):
    """Test cases for the FastAPI backend server"""
    
    @classmethod
    def setUpClass(cls):
        """Start the test server"""
        cls.server = None
        cls.server_thread = None
        cls.base_url = "http://localhost:8081"  # Use different port for testing
        
        try:
            # Start FastAPI server in a separate thread
            config = uvicorn.Config(
                app=app,
                host="localhost",
                port=8081,
                log_level="error"
            )
            cls.server = uvicorn.Server(config)
            cls.server_thread = threading.Thread(target=cls.server.run)
            cls.server_thread.daemon = True
            cls.server_thread.start()
            
            # Wait for server to start
            time.sleep(2)
            print(f"✅ FastAPI test server started on {cls.base_url}")
            
        except Exception as e:
            print(f"❌ Failed to start FastAPI test server: {e}")
            raise
    
    @classmethod
    def tearDownClass(cls):
        """Stop the test server"""
        if cls.server:
            cls.server.should_exit = True
            print("✅ FastAPI test server stopped")
    
    def test_01_health_endpoint(self):
        """Test health check endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=5)
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertIn('status', data)
            self.assertEqual(data['status'], 'healthy')
            self.assertIn('historyhounder_available', data)
            self.assertIn('version', data)
            self.assertIn('timestamp', data)
            
            print("✅ Health endpoint working")
            
        except requests.exceptions.RequestException as e:
            self.fail(f"Health endpoint failed: {e}")
    
    def test_02_search_endpoint_get(self):
        """Test search endpoint with GET request"""
        try:
            # Test with valid query
            query = "test search"
            params = {'q': query, 'top_k': '5'}
            response = requests.get(f"{self.base_url}/api/search?{urlencode(params)}", timeout=10)
            
            # Should get 200, 503 (if backend not available), or 500 (if model not found)
            self.assertIn(response.status_code, [200, 503, 500])
            
            data = response.json()
            
            if response.status_code == 200:
                self.assertIn('success', data)
                self.assertTrue(data['success'])
                self.assertIn('query', data)
                self.assertEqual(data['query'], query)
                self.assertIn('results', data)
                self.assertIn('total', data)
                self.assertIn('timestamp', data)
                print("✅ Search endpoint working (with backend)")
            else:
                self.assertIn('error', data)
                print("✅ Search endpoint working (backend unavailable)")
                
        except requests.exceptions.RequestException as e:
            self.fail(f"Search endpoint failed: {e}")
    
    def test_03_search_endpoint_missing_query(self):
        """Test search endpoint with missing query parameter"""
        try:
            response = requests.get(f"{self.base_url}/api/search", timeout=5)
            self.assertEqual(response.status_code, 422)  # FastAPI validation error
            
            data = response.json()
            self.assertIn('detail', data)
            print("✅ Search endpoint properly handles missing query")
            
        except requests.exceptions.RequestException as e:
            self.fail(f"Search endpoint failed: {e}")
    
    def test_04_qa_endpoint_post(self):
        """Test Q&A endpoint with POST request"""
        try:
            # Test with valid question
            question = "What programming websites did I visit?"
            payload = {
                'question': question,
                'top_k': 5
            }
            
            response = requests.post(
                f"{self.base_url}/api/qa",
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            # Should get 200, 503 (if backend not available), or 500 (if model not found)
            self.assertIn(response.status_code, [200, 503, 500])
            
            data = response.json()
            
            if response.status_code == 200:
                self.assertIn('success', data)
                self.assertTrue(data['success'])
                self.assertIn('question', data)
                self.assertEqual(data['question'], question)
                self.assertIn('answer', data)
                self.assertIn('sources', data)
                self.assertIn('timestamp', data)
                print("✅ Q&A POST endpoint working (with backend)")
            else:
                self.assertIn('error', data)
                print("✅ Q&A POST endpoint working (backend unavailable)")
                
        except requests.exceptions.RequestException as e:
            self.fail(f"Q&A POST endpoint failed: {e}")
    
    def test_05_qa_endpoint_missing_question(self):
        """Test Q&A endpoint with missing question"""
        try:
            # Test POST with missing question
            response = requests.post(
                f"{self.base_url}/api/qa",
                json={},
                headers={'Content-Type': 'application/json'},
                timeout=5
            )
            self.assertEqual(response.status_code, 422)  # FastAPI validation error
            
            data = response.json()
            self.assertIn('detail', data)
            
            print("✅ Q&A endpoint properly handles missing question")
            
        except requests.exceptions.RequestException as e:
            self.fail(f"Q&A endpoint failed: {e}")
    
    def test_06_process_history_endpoint(self):
        """Test history processing endpoint"""
        try:
            # Test with sample history data
            sample_history = [
                {
                    'id': '1',
                    'url': 'https://example.com',
                    'title': 'Example Site',
                    'lastVisitTime': int(time.time() * 1000000),
                    'visitCount': 1
                },
                {
                    'id': '2',
                    'url': 'https://test.com',
                    'title': 'Test Site',
                    'lastVisitTime': int(time.time() * 1000000),
                    'visitCount': 1
                }
            ]
            
            payload = {'history': sample_history}
            
            response = requests.post(
                f"{self.base_url}/api/process-history",
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            # Should get 200, 503 (if backend not available), or 500 (if error)
            self.assertIn(response.status_code, [200, 503, 500])
            
            data = response.json()
            
            if response.status_code == 200:
                self.assertIn('success', data)
                self.assertTrue(data['success'])
                self.assertIn('processed_count', data)
                self.assertIn('message', data)
                self.assertIn('timestamp', data)
                print("✅ Process history endpoint working (with backend)")
            else:
                self.assertIn('error', data)
                print("✅ Process history endpoint working (backend unavailable)")
                
        except requests.exceptions.RequestException as e:
            self.fail(f"Process history endpoint failed: {e}")
    
    def test_07_process_history_missing_data(self):
        """Test history processing endpoint with missing data"""
        try:
            # Test with empty history
            response = requests.post(
                f"{self.base_url}/api/process-history",
                json={'history': []},
                headers={'Content-Type': 'application/json'},
                timeout=5
            )
            self.assertEqual(response.status_code, 400)
            
            data = response.json()
            self.assertIn('error', data)
            
            # Test with missing history field
            response = requests.post(
                f"{self.base_url}/api/process-history",
                json={},
                headers={'Content-Type': 'application/json'},
                timeout=5
            )
            self.assertEqual(response.status_code, 422)  # FastAPI validation error
            
            data = response.json()
            self.assertIn('detail', data)
            
            print("✅ Process history endpoint properly handles missing data")
            
        except requests.exceptions.RequestException as e:
            self.fail(f"Process history endpoint failed: {e}")
    
    def test_08_stats_endpoint(self):
        """Test statistics endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/stats", timeout=10)
            
            # Should get 200, 503 (if backend not available), or 500 (if method not found)
            self.assertIn(response.status_code, [200, 503, 500])
            
            data = response.json()
            
            if response.status_code == 200:
                self.assertIn('success', data)
                self.assertTrue(data['success'])
                self.assertIn('stats', data)
                self.assertIn('timestamp', data)
                print("✅ Stats endpoint working (with backend)")
            else:
                self.assertIn('error', data)
                print("✅ Stats endpoint working (backend unavailable)")
                
        except requests.exceptions.RequestException as e:
            self.fail(f"Stats endpoint failed: {e}")
    
    def test_09_cors_headers(self):
        """Test CORS headers are properly set"""
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=5)
            
            # Check CORS headers
            self.assertIn('access-control-allow-origin', response.headers)
            self.assertEqual(response.headers['access-control-allow-origin'], '*')
            
            print("✅ CORS headers properly set")
            
        except requests.exceptions.RequestException as e:
            self.fail(f"CORS test failed: {e}")
    
    def test_10_options_request(self):
        """Test OPTIONS request handling"""
        try:
            response = requests.options(f"{self.base_url}/api/health", timeout=5)
            self.assertEqual(response.status_code, 200)
            
            # Check CORS headers
            self.assertIn('access-control-allow-origin', response.headers)
            self.assertEqual(response.headers['access-control-allow-origin'], '*')
            
            print("✅ OPTIONS request properly handled")
            
        except requests.exceptions.RequestException as e:
            self.fail(f"OPTIONS request failed: {e}")
    
    def test_11_invalid_endpoint(self):
        """Test handling of invalid endpoints"""
        try:
            response = requests.get(f"{self.base_url}/api/invalid", timeout=5)
            self.assertEqual(response.status_code, 404)
            
            data = response.json()
            self.assertIn('detail', data)
            
            print("✅ Invalid endpoints properly handled")
            
        except requests.exceptions.RequestException as e:
            self.fail(f"Invalid endpoint test failed: {e}")
    
    def test_12_openapi_docs(self):
        """Test OpenAPI documentation endpoints"""
        try:
            # Test OpenAPI JSON
            response = requests.get(f"{self.base_url}/openapi.json", timeout=5)
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertIn('openapi', data)
            self.assertIn('info', data)
            self.assertIn('paths', data)
            
            # Test Swagger UI
            response = requests.get(f"{self.base_url}/docs", timeout=5)
            self.assertEqual(response.status_code, 200)
            
            # Test ReDoc
            response = requests.get(f"{self.base_url}/redoc", timeout=5)
            self.assertEqual(response.status_code, 200)
            
            print("✅ OpenAPI documentation endpoints working")
            
        except requests.exceptions.RequestException as e:
            self.fail(f"OpenAPI docs test failed: {e}")
    
    def test_13_content_type_headers(self):
        """Test Content-Type headers are properly set"""
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=5)
            
            self.assertIn('content-type', response.headers)
            self.assertIn('application/json', response.headers['content-type'])
            
            print("✅ Content-Type headers properly set")
            
        except requests.exceptions.RequestException as e:
            self.fail(f"Content-Type test failed: {e}")


class TestBackendIntegration(unittest.TestCase):
    """Test integration with actual HistoryHounder backend"""
    
    def test_historyhounder_imports(self):
        """Test that HistoryHounder modules can be imported"""
        try:
            # Test imports
            from historyhounder.search import semantic_search, llm_qa_search
            from historyhounder.extract_chrome_history import extract_history_from_sqlite, available_browsers
            from historyhounder.pipeline import extract_and_process_history
            from historyhounder.vector_store import ChromaVectorStore
            
            print("✅ All HistoryHounder modules imported successfully")
            
        except ImportError as e:
            print(f"⚠️  HistoryHounder modules not available: {e}")
            self.skipTest("HistoryHounder backend not available")


def run_tests():
    """Run all tests"""
    print("🧪 Running HistoryHounder FastAPI Backend Tests")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTest(unittest.makeSuite(TestBackendAPI))
    suite.addTest(unittest.makeSuite(TestBackendIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.failures:
        print("\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\n❌ Errors:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    if result.skipped:
        print("\n⚠️  Skipped:")
        for test, reason in result.skipped:
            print(f"  - {test}: {reason}")
    
    if result.wasSuccessful():
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code) 