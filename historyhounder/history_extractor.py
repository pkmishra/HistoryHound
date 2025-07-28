import sqlite3
from datetime import datetime, timedelta
import shutil
import tempfile
import os
import contextlib

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


@contextlib.contextmanager
def secure_temp_db_copy(db_path):
    """
    Context manager for securely creating and cleaning up a temporary database copy.
    """
    tmp_dir = None
    tmp_db_path = None
    try:
        # Create temporary directory with secure permissions
        tmp_dir = tempfile.mkdtemp(prefix='historyhounder_', suffix='_tmp')
        tmp_db_path = os.path.join(tmp_dir, "history_copy.sqlite")
        
        # Copy the database file
        shutil.copy2(db_path, tmp_db_path)
        
        # Set restrictive permissions on the temporary file
        os.chmod(tmp_db_path, 0o600)
        
        yield tmp_db_path
        
    finally:
        # Clean up temporary files
        if tmp_db_path and os.path.exists(tmp_db_path):
            try:
                os.remove(tmp_db_path)
            except OSError:
                pass  # File might already be removed
        
        if tmp_dir and os.path.exists(tmp_dir):
            try:
                os.rmdir(tmp_dir)
            except OSError:
                pass  # Directory might not be empty or already removed


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
    
    min_time = None
    if days is not None:
        min_time = now - timedelta(days=days)
    
    history = []
    
    # Use secure context manager for temporary file handling
    with secure_temp_db_copy(db_path) as tmp_db_path:
        conn = sqlite3.connect(tmp_db_path)
        cursor = conn.cursor()
        
        try:
            if browser.startswith('firefox'):
                cursor.execute('SELECT url, title, last_visit_date, visit_count FROM moz_places ORDER BY last_visit_date DESC')
                for url, title, last_visit_date, visit_count in cursor.fetchall():
                    dt = firefox_time_to_datetime(last_visit_date)
                    if min_time and (dt is None or dt < min_time):
                        continue
                    history.append({
                        'url': url, 
                        'title': title, 
                        'last_visit_time': dt,
                        'visit_count': visit_count or 1
                    })
            elif browser == 'safari':
                cursor.execute('SELECT url, title, visit_time FROM history_items LEFT JOIN history_visits ON history_items.id = history_visits.history_item')
                for url, title, visit_time in cursor.fetchall():
                    dt = safari_time_to_datetime(visit_time)
                    if min_time and (dt is None or dt < min_time):
                        continue
                    history.append({
                        'url': url, 
                        'title': title, 
                        'last_visit_time': dt,
                        'visit_count': 1  # Safari doesn't have visit_count in the same way
                    })
            else:
                # Chrome/Brave/Edge
                cursor.execute('SELECT url, title, last_visit_time, visit_count FROM urls ORDER BY last_visit_time DESC')
                for url, title, last_visit_time, visit_count in cursor.fetchall():
                    dt = chrome_time_to_datetime(last_visit_time)
                    if min_time and (dt is None or dt < min_time):
                        continue
                    history.append({
                        'url': url, 
                        'title': title, 
                        'last_visit_time': dt,
                        'visit_count': visit_count or 1
                    })
        finally:
            conn.close()
    
    return history 