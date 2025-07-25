import sqlite3
from datetime import datetime, timedelta
import shutil
import tempfile
import os

# Helper: Chrome/Brave/Edge timestamp to datetime
def chrome_time_to_datetime(chrome_time):
    if chrome_time == 0:
        return None
    epoch_start = datetime(1601, 1, 1)
    return epoch_start + timedelta(microseconds=chrome_time)

# Helper: Firefox timestamp to datetime
def firefox_time_to_datetime(firefox_time):
    if not firefox_time:
        return None
    return datetime(1970, 1, 1) + timedelta(microseconds=firefox_time)

# Helper: Safari timestamp to datetime
def safari_time_to_datetime(safari_time):
    if not safari_time:
        return None
    return datetime(2001, 1, 1) + timedelta(seconds=safari_time)


def extract_history(browser, db_path, days=None, now=None):
    """
    Extracts browser history entries from the given db_path.
    If days is specified, only returns entries from the last N days.
    'now' can be passed for testing; defaults to datetime.now().
    Returns a list of dicts: {url, title, last_visit_time (datetime)}
    Always copies the DB to a temp file to avoid locking issues.
    """
    if now is None:
        now = datetime.now()
    tmp_dir = tempfile.mkdtemp()
    tmp_db_path = os.path.join(tmp_dir, "history_copy.sqlite")
    shutil.copy2(db_path, tmp_db_path)
    conn = sqlite3.connect(tmp_db_path)
    cursor = conn.cursor()
    min_time = None
    if days is not None:
        min_time = now - timedelta(days=days)
    history = []
    try:
        if browser.startswith('firefox'):
            cursor.execute('SELECT url, title, last_visit_date FROM moz_places ORDER BY last_visit_date DESC')
            for url, title, last_visit_date in cursor.fetchall():
                dt = firefox_time_to_datetime(last_visit_date)
                if min_time and (dt is None or dt < min_time):
                    continue
                history.append({'url': url, 'title': title, 'last_visit_time': dt})
        elif browser == 'safari':
            cursor.execute('SELECT url, title, visit_time FROM history_items LEFT JOIN history_visits ON history_items.id = history_visits.history_item')
            for url, title, visit_time in cursor.fetchall():
                dt = safari_time_to_datetime(visit_time)
                if min_time and (dt is None or dt < min_time):
                    continue
                history.append({'url': url, 'title': title, 'last_visit_time': dt})
        else:
            # Chrome/Brave/Edge
            cursor.execute('SELECT url, title, last_visit_time FROM urls ORDER BY last_visit_time DESC')
            for url, title, last_visit_time in cursor.fetchall():
                dt = chrome_time_to_datetime(last_visit_time)
                if min_time and (dt is None or dt < min_time):
                    continue
                history.append({'url': url, 'title': title, 'last_visit_time': dt})
    finally:
        conn.close()
        os.remove(tmp_db_path)
        os.rmdir(tmp_dir)
    return history 