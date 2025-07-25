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