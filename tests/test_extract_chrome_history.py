import os
import json
from datetime import datetime
import pytest
from historyhounder import extract_chrome_history

def test_normal_extraction(monkeypatch):
    # Patch os.path.exists, shutil.copy2, sqlite3.connect, os.remove
    monkeypatch.setattr(extract_chrome_history.os.path, 'exists', lambda x: True)
    monkeypatch.setattr(extract_chrome_history.shutil, 'copy2', lambda src, dst: None)
    class DummyCursor:
        def execute(self, *a, **kw):
            return None
        def fetchall(self):
            chrome_time = 13217452800000000
            return [
                ('http://example.com', 'Example', chrome_time),
                ('http://test.com', 'Test', 0),
            ]
    class DummyConn:
        def cursor(self):
            return DummyCursor()
        def close(self):
            pass
    monkeypatch.setattr(extract_chrome_history.sqlite3, 'connect', lambda x: DummyConn())
    monkeypatch.setattr(extract_chrome_history.os, 'remove', lambda x: None)
    # Capture print
    printed = {}
    def fake_print(val):
        printed['val'] = val
    monkeypatch.setattr('builtins.print', fake_print)
    extract_chrome_history.extract_history_from_sqlite('dummy_path', 'chrome')
    data = json.loads(printed['val'])
    assert len(data) == 2
    assert data[0]['url'] == 'http://example.com'
    assert data[0]['title'] == 'Example'
    assert isinstance(data[0]['last_visit_time'], str)
    assert data[1]['last_visit_time'] is None

def test_missing_database(monkeypatch):
    monkeypatch.setattr(extract_chrome_history.os.path, 'exists', lambda x: False)
    printed = {}
    def fake_print(val):
        printed['val'] = val
    monkeypatch.setattr('builtins.print', fake_print)
    # Simulate running main() with a missing file argument
    import sys
    monkeypatch.setattr(sys, 'argv', ['extract_chrome_history', 'not_a_real_browser'])
    extract_chrome_history.main()
    assert (
        'Unknown browser or file' in printed['val']
        or 'No supported browser history files found.' in printed['val']
        or 'Available browsers: []' in printed['val']
    )

def test_empty_database(monkeypatch):
    monkeypatch.setattr(extract_chrome_history.os.path, 'exists', lambda x: True)
    monkeypatch.setattr(extract_chrome_history.shutil, 'copy2', lambda src, dst: None)
    class DummyCursor:
        def execute(self, *a, **kw):
            return None
        def fetchall(self):
            return []
    class DummyConn:
        def cursor(self):
            return DummyCursor()
        def close(self):
            pass
    monkeypatch.setattr(extract_chrome_history.sqlite3, 'connect', lambda x: DummyConn())
    monkeypatch.setattr(extract_chrome_history.os, 'remove', lambda x: None)
    printed = {}
    def fake_print(val):
        printed['val'] = val
    monkeypatch.setattr('builtins.print', fake_print)
    extract_chrome_history.extract_history_from_sqlite('dummy_path', 'chrome')
    data = json.loads(printed['val'])
    assert data == []

def test_chrome_time_to_datetime():
    # 2023-01-01T00:00:00 UTC in Chrome timestamp
    chrome_time = 13317052800000000
    dt = extract_chrome_history.chrome_time_to_datetime(chrome_time)
    assert isinstance(dt, datetime)
    assert dt.year == 2023
    assert dt.month == 1
    assert dt.day == 1
    assert extract_chrome_history.chrome_time_to_datetime(0) is None 