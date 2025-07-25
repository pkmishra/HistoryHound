import pytest
from historyhounder import content_fetcher

class DummyResp:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code
    def raise_for_status(self):
        if self.status_code != 200:
            raise Exception('HTTP error')


def test_youtube_metadata(monkeypatch):
    def dummy_run(cmd, capture_output, text, check):
        class DummyResult:
            stdout = '{"title": "Test Video", "description": "Desc", "channel": "Chan", "upload_date": "20240601", "duration": 123}'
        return DummyResult()
    monkeypatch.setattr(content_fetcher.subprocess, 'run', dummy_run)
    url = 'https://www.youtube.com/watch?v=abc123'
    result = content_fetcher.fetch_and_extract(url)
    assert result['type'] == 'video'
    assert result['title'] == 'Test Video'
    assert result['channel'] == 'Chan'


def test_article_content(monkeypatch):
    html = '<html><head><title>Test</title></head><body><h1>Headline</h1><p>Body</p></body></html>'
    def dummy_get(url, timeout):
        return DummyResp(html)
    monkeypatch.setattr(content_fetcher.requests, 'get', dummy_get)
    class DummyDoc:
        def __init__(self, text):
            pass
        def short_title(self):
            return 'Test'
        def summary(self):
            return '<h1>Headline</h1><p>Body</p>'
    monkeypatch.setattr(content_fetcher, 'Document', DummyDoc)
    url = 'https://example.com/article'
    result = content_fetcher.fetch_and_extract(url)
    assert result['type'] == 'article'
    assert 'Headline' in result['text']


def test_fallback_beautifulsoup(monkeypatch):
    html = '<html><head><title>Fallback</title><meta name="description" content="desc"></head><body></body></html>'
    def dummy_get(url, timeout):
        return DummyResp(html)
    monkeypatch.setattr(content_fetcher.requests, 'get', dummy_get)
    class DummyDoc:
        def __init__(self, text):
            raise Exception('fail')
    monkeypatch.setattr(content_fetcher, 'Document', DummyDoc)
    url = 'https://example.com/fallback'
    result = content_fetcher.fetch_and_extract(url)
    assert result['type'] == 'unknown'
    assert result['title'] == 'Fallback'
    assert result['text'] == 'desc'


def test_error_handling(monkeypatch):
    def dummy_get(url, timeout):
        raise Exception('network fail')
    monkeypatch.setattr(content_fetcher.requests, 'get', dummy_get)
    url = 'https://example.com/error'
    result = content_fetcher.fetch_and_extract(url)
    assert 'error' in result 


def test_malformed_html(monkeypatch):
    html = '<html><head><title>Malformed<title></head><body><h1>Headline'
    def dummy_get(url, timeout):
        return DummyResp(html)
    monkeypatch.setattr(content_fetcher.requests, 'get', dummy_get)
    class DummyDoc:
        def __init__(self, text):
            raise Exception('fail')
    monkeypatch.setattr(content_fetcher, 'Document', DummyDoc)
    url = 'https://example.com/malformed'
    result = content_fetcher.fetch_and_extract(url)
    assert result['type'] == 'unknown'
    assert 'title' in result


def test_request_timeout(monkeypatch):
    def dummy_get(url, timeout):
        raise Exception('timeout')
    monkeypatch.setattr(content_fetcher.requests, 'get', dummy_get)
    url = 'https://example.com/timeout'
    result = content_fetcher.fetch_and_extract(url)
    assert 'error' in result
    assert 'timeout' in result['error'] 