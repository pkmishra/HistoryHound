import pytest
from historyhounder.utils import should_ignore, parse_comma_separated_values
import argparse
from unittest.mock import Mock

def test_parse_comma_separated_values():
    # Test basic comma separation
    assert parse_comma_separated_values("a,b,c") == ["a", "b", "c"]
    
    # Test with whitespace
    assert parse_comma_separated_values(" a , b , c ") == ["a", "b", "c"]
    
    # Test with empty values
    assert parse_comma_separated_values("a,,b,c") == ["a", "b", "c"]
    assert parse_comma_separated_values("a, ,b,c") == ["a", "b", "c"]
    
    # Test edge cases
    assert parse_comma_separated_values("") == []
    assert parse_comma_separated_values(None) == []
    assert parse_comma_separated_values("   ") == []
    assert parse_comma_separated_values("single") == ["single"]

def test_ignore_domain():
    url = 'https://www.example.com/page'
    assert should_ignore(url, ['example.com'], [])
    assert not should_ignore(url, ['other.com'], [])

def test_ignore_pattern():
    url = 'https://www.site.com/ads/page'
    assert should_ignore(url, [], ['/ads/'])
    assert should_ignore(url, [], ['site\\.com/ads'])  # regex
    assert not should_ignore(url, [], ['/blog/'])

def test_ignore_both():
    url = 'https://www.foo.com/special'
    assert should_ignore(url, ['foo.com'], ['/ads/'])
    assert should_ignore(url, [], ['special'])
    assert not should_ignore(url, ['bar.com'], ['other'])

def test_ignore_empty():
    url = 'https://www.site.com/page'
    assert not should_ignore(url, [], [])

def test_cli_argument_parsing():
    """Test that CLI arguments are correctly parsed for comma-separated values."""
    from historyhounder.utils import parse_comma_separated_values
    
    # Simulate CLI argument parsing
    mock_args = Mock()
    mock_args.ignore_domain = "google.com,facebook.com,youtube.com"
    mock_args.ignore_pattern = "login,logout,/admin"
    
    # Test parsing
    ignore_domains = parse_comma_separated_values(mock_args.ignore_domain)
    ignore_patterns = parse_comma_separated_values(mock_args.ignore_pattern)
    
    assert ignore_domains == ["google.com", "facebook.com", "youtube.com"]
    assert ignore_patterns == ["login", "logout", "/admin"]
    
    # Test filtering logic
    test_urls = [
        "https://www.google.com/search",
        "https://www.facebook.com/profile",
        "https://www.youtube.com/watch",
        "https://www.example.com/login",
        "https://www.example.com/page"
    ]
    
    filtered_urls = [
        url for url in test_urls 
        if not should_ignore(url, ignore_domains, ignore_patterns)
    ]
    
    # Should only keep the last URL (example.com/page)
    assert len(filtered_urls) == 1
    assert filtered_urls[0] == "https://www.example.com/page" 