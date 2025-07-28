import pytest
from datetime import datetime, timedelta
from historyhounder import history_extractor
import tempfile
import os

class DummyCursor:
    def __init__(self, rows):
        self._rows = rows
    def execute(self, *a, **kw):
        return None
    def fetchall(self):
        return self._rows

class DummyConn:
    def __init__(self, rows):
        self._rows = rows
    def cursor(self):
        return DummyCursor(self._rows)
    def close(self):
        pass

def make_temp_db():
    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp.close()
    return tmp.name

def test_chrome_history_all(monkeypatch):
    now = datetime(2024, 6, 1)
    chrome_time = int((now - datetime(1601, 1, 1)).total_seconds() * 1_000_000)
    rows = [
        ('http://a.com', 'A', chrome_time, 5),
        ('http://b.com', 'B', chrome_time - 10_000_000, 3),
    ]
    monkeypatch.setattr(history_extractor.sqlite3, 'connect', lambda path: DummyConn(rows))
    db_path = make_temp_db()
    try:
        result = history_extractor.extract_history('chrome', db_path, days=None, now=now)
        assert len(result) == 2
        assert result[0]['url'] == 'http://a.com'
    finally:
        os.remove(db_path)

def test_chrome_history_days(monkeypatch):
    now = datetime(2024, 6, 1)
    chrome_time_recent = int((now - datetime(1601, 1, 1)).total_seconds() * 1_000_000)
    chrome_time_old = int((now - timedelta(days=10) - datetime(1601, 1, 1)).total_seconds() * 1_000_000)
    rows = [
        ('http://recent.com', 'Recent', chrome_time_recent, 2),
        ('http://old.com', 'Old', chrome_time_old, 1),
    ]
    monkeypatch.setattr(history_extractor.sqlite3, 'connect', lambda path: DummyConn(rows))
    db_path = make_temp_db()
    try:
        result = history_extractor.extract_history('chrome', db_path, days=7, now=now)
        assert len(result) == 1
        assert result[0]['url'] == 'http://recent.com'
    finally:
        os.remove(db_path)

def test_firefox_history(monkeypatch):
    now = datetime(2024, 6, 1)
    ff_time = int((now - datetime(1970, 1, 1)).total_seconds() * 1_000_000)
    rows = [
        ('http://ff.com', 'FF', ff_time, 4),
    ]
    monkeypatch.setattr(history_extractor.sqlite3, 'connect', lambda path: DummyConn(rows))
    db_path = make_temp_db()
    try:
        result = history_extractor.extract_history('firefox:profile', db_path, days=None, now=now)
        assert len(result) == 1
        assert result[0]['url'] == 'http://ff.com'
    finally:
        os.remove(db_path)

def test_safari_history(monkeypatch):
    now = datetime(2024, 6, 1)
    safari_time = int((now - datetime(2001, 1, 1)).total_seconds())
    rows = [
        ('http://sf.com', 'SF', safari_time),
    ]
    monkeypatch.setattr(history_extractor.sqlite3, 'connect', lambda path: DummyConn(rows))
    db_path = make_temp_db()
    try:
        result = history_extractor.extract_history('safari', db_path, days=None, now=now)
        assert len(result) == 1
        assert result[0]['url'] == 'http://sf.com'
    finally:
        os.remove(db_path)

def test_days_filter(monkeypatch):
    now = datetime(2024, 6, 1)
    chrome_time_recent = int((now - datetime(1601, 1, 1)).total_seconds() * 1_000_000)
    chrome_time_old = int((now - timedelta(days=30) - datetime(1601, 1, 1)).total_seconds() * 1_000_000)
    rows = [
        ('http://recent.com', 'Recent', chrome_time_recent, 3),
        ('http://old.com', 'Old', chrome_time_old, 1),
    ]
    monkeypatch.setattr(history_extractor.sqlite3, 'connect', lambda path: DummyConn(rows))
    db_path = make_temp_db()
    try:
        result = history_extractor.extract_history('chrome', db_path, days=7, now=now)
        assert len(result) == 1
        assert result[0]['url'] == 'http://recent.com'
    finally:
        os.remove(db_path)


def test_empty_title(monkeypatch):
    now = datetime(2024, 6, 1)
    chrome_time = int((now - datetime(1601, 1, 1)).total_seconds() * 1_000_000)
    rows = [
        ('http://a.com', '', chrome_time, 1),
    ]
    monkeypatch.setattr(history_extractor.sqlite3, 'connect', lambda path: DummyConn(rows))
    db_path = make_temp_db()
    try:
        result = history_extractor.extract_history('chrome', db_path, days=None, now=now)
        assert len(result) == 1
        assert result[0]['title'] == ''
    finally:
        os.remove(db_path)


def test_duplicate_urls(monkeypatch):
    now = datetime(2024, 6, 1)
    chrome_time = int((now - datetime(1601, 1, 1)).total_seconds() * 1_000_000)
    rows = [
        ('http://dup.com', 'Dup', chrome_time, 2),
        ('http://dup.com', 'Dup', chrome_time, 1),
    ]
    monkeypatch.setattr(history_extractor.sqlite3, 'connect', lambda path: DummyConn(rows))
    db_path = make_temp_db()
    try:
        result = history_extractor.extract_history('chrome', db_path, days=None, now=now)
        assert len(result) == 2
        assert all(r['url'] == 'http://dup.com' for r in result)
    finally:
        os.remove(db_path) 