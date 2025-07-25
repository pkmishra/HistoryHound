import os
import tempfile
from datetime import datetime
from historyhounder.pipeline import extract_and_process_history
from historyhounder.utils import parse_comma_separated_values
import sqlite3
import pytest

# Helper to create a minimal Chrome history DB for testing

def create_chrome_history_db_with_urls(db_path, url_title_time_tuples):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE urls (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT,
        title TEXT,
        visit_count INTEGER,
        typed_count INTEGER,
        last_visit_time INTEGER,
        hidden INTEGER DEFAULT 0
    )''')
    for url, title, chrome_time in url_title_time_tuples:
        c.execute('INSERT INTO urls (url, title, visit_count, typed_count, last_visit_time, hidden) VALUES (?, ?, 1, 0, ?, 0)', (url, title, chrome_time))
    conn.commit()
    conn.close()

# Use the same URLs as in real_world_urls.txt for realism
URLS_FILE = os.path.join(os.path.dirname(__file__), 'real_world_urls.txt')
def load_real_world_urls():
    urls = []
    with open(URLS_FILE, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            url, title = line.split('|', 1)
            urls.append((url, title))
    return urls

@pytest.mark.parametrize('with_content,embed', [
    (False, False),
    (True, False),
    (True, True),
])
def test_extract_and_process_history(tmp_path, with_content, embed):
    now = datetime.now()
    chrome_epoch = datetime(1601, 1, 1)
    def to_chrome_time(dt):
        return int((dt - chrome_epoch).total_seconds() * 1_000_000)
    url_title = load_real_world_urls()
    url_title_time = [(url, title, to_chrome_time(now)) for url, title in url_title]
    db_path = tmp_path / 'History'
    create_chrome_history_db_with_urls(str(db_path), url_title_time)
    result = extract_and_process_history(
        browser='chrome',
        db_path=str(db_path),
        days=None,
        ignore_domains=[],
        ignore_patterns=[],
        with_content=with_content,
        embed=embed,
        embedder_backend='sentence-transformers',
    )
    assert result['status'] in ('fetched', 'embedded')
    assert isinstance(result['results'], list)
    if embed:
        assert 'num_embedded' in result
        assert result['num_embedded'] >= 1
    else:
        assert len(result['results']) == len(url_title)


def test_extract_and_process_history_with_filter(tmp_path):
    now = datetime.now()
    chrome_epoch = datetime(1601, 1, 1)
    def to_chrome_time(dt):
        return int((dt - chrome_epoch).total_seconds() * 1_000_000)
    url_title = load_real_world_urls()
    url_title_time = [(url, title, to_chrome_time(now)) for url, title in url_title]
    db_path = tmp_path / 'History'
    create_chrome_history_db_with_urls(str(db_path), url_title_time)
    # Ignore the first domain
    ignore_domain = url_title[0][0].split('/')[2]
    result = extract_and_process_history(
        browser='chrome',
        db_path=str(db_path),
        days=None,
        ignore_domains=[ignore_domain],
        ignore_patterns=[],
        with_content=False,
        embed=False,
        embedder_backend='sentence-transformers',
    )
    assert all(ignore_domain not in r['url'] for r in result['results']) 


def test_extract_and_process_history_db_failure(tmp_path, monkeypatch):
    # Simulate DB connection failure
    def fail_connect(*a, **kw):
        raise Exception("DB connection failed")
    import sqlite3
    monkeypatch.setattr(sqlite3, 'connect', fail_connect)
    db_path = tmp_path / 'History'
    # Create an empty file so FileNotFoundError is not raised
    db_path.write_text('')
    try:
        with pytest.raises(Exception) as excinfo:
            extract_and_process_history(
                browser='chrome',
                db_path=str(db_path),
                days=None,
                ignore_domains=[],
                ignore_patterns=[],
                with_content=True,
                embed=True,
                embedder_backend='sentence-transformers',
            )
        assert 'DB connection failed' in str(excinfo.value)
    finally:
        pass 


def test_extract_and_process_history_with_url_limit(tmp_path):
    now = datetime.now()
    chrome_epoch = datetime(1601, 1, 1)
    def to_chrome_time(dt):
        return int((dt - chrome_epoch).total_seconds() * 1_000_000)
    url_title = load_real_world_urls()
    url_title_time = [(url, title, to_chrome_time(now)) for url, title in url_title]
    db_path = tmp_path / 'History'
    create_chrome_history_db_with_urls(str(db_path), url_title_time)
    
    # Test with URL limit
    result = extract_and_process_history(
        browser='chrome',
        db_path=str(db_path),
        days=None,
        ignore_domains=[],
        ignore_patterns=[],
        with_content=False,
        embed=False,
        embedder_backend='sentence-transformers',
        url_limit=3
    )
    assert result['status'] == 'fetched'
    assert len(result['results']) == 3
    assert len(result['results']) <= 3  # Should not exceed limit


def test_extract_and_process_history_with_url_limit_and_content(tmp_path):
    now = datetime.now()
    chrome_epoch = datetime(1601, 1, 1)
    def to_chrome_time(dt):
        return int((dt - chrome_epoch).total_seconds() * 1_000_000)
    url_title = load_real_world_urls()
    url_title_time = [(url, title, to_chrome_time(now)) for url, title in url_title]
    db_path = tmp_path / 'History'
    create_chrome_history_db_with_urls(str(db_path), url_title_time)
    
    # Test with URL limit and content fetching
    result = extract_and_process_history(
        browser='chrome',
        db_path=str(db_path),
        days=None,
        ignore_domains=[],
        ignore_patterns=[],
        with_content=True,
        embed=False,
        embedder_backend='sentence-transformers',
        url_limit=2
    )
    assert result['status'] == 'fetched'
    assert len(result['results']) == 2
    # Should have content for the limited URLs
    for r in result['results']:
        assert 'url' in r
        assert 'title' in r


def test_extract_and_process_history_with_url_limit_and_embedding(tmp_path):
    now = datetime.now()
    chrome_epoch = datetime(1601, 1, 1)
    def to_chrome_time(dt):
        return int((dt - chrome_epoch).total_seconds() * 1_000_000)
    url_title = load_real_world_urls()
    url_title_time = [(url, title, to_chrome_time(now)) for url, title in url_title]
    db_path = tmp_path / 'History'
    create_chrome_history_db_with_urls(str(db_path), url_title_time)
    
    # Test with URL limit and embedding
    result = extract_and_process_history(
        browser='chrome',
        db_path=str(db_path),
        days=None,
        ignore_domains=[],
        ignore_patterns=[],
        with_content=True,
        embed=True,
        embedder_backend='sentence-transformers',
        url_limit=1
    )
    assert result['status'] == 'embedded'
    assert 'num_embedded' in result
    assert result['num_embedded'] >= 1
    assert len(result['results']) <= 1  # Should respect limit


def test_extract_and_process_history_url_limit_none(tmp_path):
    now = datetime.now()
    chrome_epoch = datetime(1601, 1, 1)
    def to_chrome_time(dt):
        return int((dt - chrome_epoch).total_seconds() * 1_000_000)
    url_title = load_real_world_urls()
    url_title_time = [(url, title, to_chrome_time(now)) for url, title in url_title]
    db_path = tmp_path / 'History'
    create_chrome_history_db_with_urls(str(db_path), url_title_time)
    
    # Test with no URL limit (should process all URLs)
    result = extract_and_process_history(
        browser='chrome',
        db_path=str(db_path),
        days=None,
        ignore_domains=[],
        ignore_patterns=[],
        with_content=False,
        embed=False,
        embedder_backend='sentence-transformers',
        url_limit=None
    )
    assert result['status'] == 'fetched'
    assert len(result['results']) == len(url_title)  # Should process all URLs


def test_extract_and_process_history_url_limit_zero(tmp_path):
    now = datetime.now()
    chrome_epoch = datetime(1601, 1, 1)
    def to_chrome_time(dt):
        return int((dt - chrome_epoch).total_seconds() * 1_000_000)
    url_title = load_real_world_urls()
    url_title_time = [(url, title, to_chrome_time(now)) for url, title in url_title]
    db_path = tmp_path / 'History'
    create_chrome_history_db_with_urls(str(db_path), url_title_time)
    
    # Test with URL limit of 0 (should return no results)
    result = extract_and_process_history(
        browser='chrome',
        db_path=str(db_path),
        days=None,
        ignore_domains=[],
        ignore_patterns=[],
        with_content=False,
        embed=False,
        embedder_backend='sentence-transformers',
        url_limit=0
    )
    assert result['status'] == 'fetched'
    assert len(result['results']) == 0  # Should return no results 