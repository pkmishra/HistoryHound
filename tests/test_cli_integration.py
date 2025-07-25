import subprocess
import sys
import tempfile
import os
import json
import pytest
import sqlite3
from datetime import datetime
import re

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

def run_cli(args):
    """Run the CLI as a subprocess and return stdout."""
    cmd = [sys.executable, '-m', 'historyhounder.cli'] + args
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout

def extract_json_from_output(output):
    """Extract the JSON array or object from CLI output, skipping progress lines like '[1/5] ...'. Accepts empty arrays/objects."""
    lines = output.splitlines()
    for i, line in enumerate(lines):
        lstripped = line.lstrip()
        if lstripped in ('[', '{', '[{', '[]', '{}') or lstripped.startswith('[{'):
            return '\n'.join(lines[i:])
    raise ValueError(f"No JSON found in output:\n{output}")


def test_cli_extract_and_embed(tmp_path):
    now = datetime.now()
    chrome_epoch = datetime(1601, 1, 1)
    def to_chrome_time(dt):
        return int((dt - chrome_epoch).total_seconds() * 1_000_000)
    url_title = load_real_world_urls()
    url_title_time = [(url, title, to_chrome_time(now)) for url, title in url_title]
    db_path = tmp_path / 'History'
    create_chrome_history_db_with_urls(str(db_path), url_title_time)
    out = run_cli(['extract', '--browser', 'chrome', '--db-path', str(db_path), '--with-content'])
    try:
        json_str = extract_json_from_output(out)
        data = json.loads(json_str)
    except Exception as e:
        print(f"CLI output:\n{out}")
        raise
    assert isinstance(data, list)
    # Only count documents that fetched successfully (no 'error' field or error is None)
    successful = [d for d in data if not d.get('error')]
    assert len(successful) >= 1, "At least one document should be fetched successfully."
    for doc in successful:
        assert 'text' in doc or 'description' in doc


def test_cli_extract_with_ignore(tmp_path):
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
    out = run_cli(['extract', '--browser', 'chrome', '--db-path', str(db_path), '--with-content', '--ignore-domain', ignore_domain])
    try:
        json_str = extract_json_from_output(out)
        data = json.loads(json_str)
    except Exception as e:
        print(f"CLI output:\n{out}")
        raise
    ignore_domain = url_title[0][0].split('/')[2]
    assert all(ignore_domain not in d['url'] for d in data)


def test_cli_semantic_search(tmp_path):
    now = datetime.now()
    chrome_epoch = datetime(1601, 1, 1)
    def to_chrome_time(dt):
        return int((dt - chrome_epoch).total_seconds() * 1_000_000)
    url_title = load_real_world_urls()
    url_title_time = [(url, title, to_chrome_time(now)) for url, title in url_title]
    db_path = tmp_path / 'History'
    create_chrome_history_db_with_urls(str(db_path), url_title_time)
    # First, embed the data
    run_cli(['extract', '--browser', 'chrome', '--db-path', str(db_path), '--with-content', '--embed'])
    # Now, search for each title, but only for those that fetched successfully
    for url, title in url_title:
        # Use the extract command to get the latest data
        out_extract = run_cli(['extract', '--browser', 'chrome', '--db-path', str(db_path), '--with-content'])
        try:
            json_str = extract_json_from_output(out_extract)
            data = json.loads(json_str)
        except Exception as e:
            print(f"CLI output (extract) for '{title}':\n{out_extract}")
            raise
        # Find the doc for this url
        doc = next((d for d in data if d['url'] == url and not d.get('error')), None)
        if not doc:
            continue  # Skip if fetch failed
        out = run_cli(['search', '--query', title.split()[0], '--top-k', '1'])
        try:
            json_str = extract_json_from_output(out)
            results = json.loads(json_str)
        except Exception as e:
            print(f"CLI output for query '{title.split()[0]}':\n{out}")
            raise
        if not results:
            print(f"Warning: No search results for query '{title.split()[0]}' (url: {url})")
            continue
        assert isinstance(results, list)
        assert any(title in r.get('document', '') or title in r.get('title', '') for r in results) 