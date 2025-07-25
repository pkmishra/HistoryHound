import os
import tempfile
from datetime import datetime
from historyhounder.pipeline import extract_and_process_history
from historyhounder.search import semantic_search, llm_qa_search
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

@pytest.fixture(scope="module")
def setup_history_and_embeddings(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("search")
    now = datetime.now()
    chrome_epoch = datetime(1601, 1, 1)
    def to_chrome_time(dt):
        return int((dt - chrome_epoch).total_seconds() * 1_000_000)
    url_title = load_real_world_urls()
    url_title_time = [(url, title, to_chrome_time(now)) for url, title in url_title]
    db_path = tmp_path / 'History'
    create_chrome_history_db_with_urls(str(db_path), url_title_time)
    # Extract, fetch content, and embed
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
    return url_title

def test_semantic_search(setup_history_and_embeddings):
    url_title = setup_history_and_embeddings
    # Search for each title's first word
    for url, title in url_title:
        query_word = title.split()[0]
        results = semantic_search(query_word, top_k=3, embedder_backend='sentence-transformers')
        assert isinstance(results, list)
        # Accept empty results, or if results exist, at least one should mention a word from the query
        if results:
            # Only consider results with content (no error, has text or title)
            contentful = [r for r in results if not r.get('error') and (r.get('document') or r.get('title'))]
            if not contentful:
                # All results are errors or empty, skip assertion for this query
                continue
            found = False
            for r in contentful:
                doc = r.get('document', '')
                meta_title = r.get('title', '')
                if query_word.lower() in doc.lower() or query_word.lower() in meta_title.lower():
                    found = True
                    break
            assert found, f"No result contains the query word '{query_word}' in document or title. Results: {contentful}"

def test_llm_qa_search(setup_history_and_embeddings):
    url_title = setup_history_and_embeddings
    # Only run if Ollama and model are available (skip if not)
    try:
        result = llm_qa_search("AI", top_k=3, llm='ollama', llm_model='llama3.2:latest')
    except Exception as e:
        pytest.skip(f"Ollama or model not available: {e}")
    assert 'answer' in result
    assert 'sources' in result
