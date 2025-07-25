import os
import shutil
import sqlite3
import json
from datetime import datetime, timedelta
import sys
import platform

# Cross-platform browser history paths
def get_browser_paths():
    """Get browser paths based on the current operating system."""
    system = platform.system().lower()
    
    if system == "darwin":  # macOS
        return {
            'chrome': os.path.expanduser('~/Library/Application Support/Google/Chrome/Default/History'),
            'brave': os.path.expanduser('~/Library/Application Support/BraveSoftware/Brave-Browser/Default/History'),
            'edge': os.path.expanduser('~/Library/Application Support/Microsoft Edge/Default/History'),
            'firefox': os.path.expanduser('~/Library/Application Support/Firefox/Profiles'),  # Needs special handling
            'safari': os.path.expanduser('~/Library/Safari/History.db'),
        }
    elif system == "windows":  # Windows
        return {
            'chrome': os.path.expanduser('~/AppData/Local/Google/Chrome/User Data/Default/History'),
            'brave': os.path.expanduser('~/AppData/Local/BraveSoftware/Brave-Browser/User Data/Default/History'),
            'edge': os.path.expanduser('~/AppData/Local/Microsoft/Edge/User Data/Default/History'),
            'firefox': os.path.expanduser('~/AppData/Roaming/Mozilla/Firefox/Profiles'),  # Needs special handling
        }
    elif system == "linux":  # Linux
        return {
            'chrome': os.path.expanduser('~/.config/google-chrome/Default/History'),
            'brave': os.path.expanduser('~/.config/BraveSoftware/Brave-Browser/Default/History'),
            'edge': os.path.expanduser('~/.config/microsoft-edge/Default/History'),
            'firefox': os.path.expanduser('~/.mozilla/firefox'),  # Needs special handling
        }
    else:
        return {}

# Get browser paths for current platform
BROWSER_PATHS = get_browser_paths()

def available_browsers():
    browsers = {}
    for name, path in BROWSER_PATHS.items():
        if name == 'firefox':
            # Firefox can have multiple profiles
            if os.path.exists(path):
                for profile in os.listdir(path):
                    hist_path = os.path.join(path, profile, 'places.sqlite')
                    if os.path.exists(hist_path):
                        browsers[f'firefox:{profile}'] = hist_path
        else:
            if os.path.exists(path):
                browsers[name] = path
    return browsers

def chrome_time_to_datetime(chrome_time):
    if chrome_time == 0:
        return None
    epoch_start = datetime(1601, 1, 1)
    return epoch_start + timedelta(microseconds=chrome_time)

def extract_history_from_sqlite(db_path, browser):
    tmp_path = 'History_tmp'
    shutil.copy2(db_path, tmp_path)
    conn = sqlite3.connect(tmp_path)
    cursor = conn.cursor()
    if browser.startswith('firefox'):
        # Firefox uses 'places.sqlite' and different schema
        cursor.execute('SELECT url, title, last_visit_date FROM moz_places ORDER BY last_visit_date DESC')
        rows = cursor.fetchall()
        history = []
        for url, title, last_visit_date in rows:
            # Firefox last_visit_date is in microseconds since Unix epoch
            dt = None
            if last_visit_date:
                dt = datetime(1970, 1, 1) + timedelta(microseconds=last_visit_date)
            history.append({
                'url': url,
                'title': title,
                'last_visit_time': dt.isoformat() if dt else None
            })
    elif browser == 'safari':
        # Safari uses History.db
        cursor.execute('SELECT url, title, visit_time FROM history_items LEFT JOIN history_visits ON history_items.id = history_visits.history_item')
        rows = cursor.fetchall()
        history = []
        for url, title, visit_time in rows:
            # Safari visit_time is in seconds since 2001-01-01
            dt = None
            if visit_time:
                dt = datetime(2001, 1, 1) + timedelta(seconds=visit_time)
            history.append({
                'url': url,
                'title': title,
                'last_visit_time': dt.isoformat() if dt else None
            })
    else:
        # Chrome/Brave/Edge
        cursor.execute('SELECT url, title, last_visit_time FROM urls ORDER BY last_visit_time DESC')
        rows = cursor.fetchall()
        history = []
        for url, title, last_visit_time in rows:
            dt = chrome_time_to_datetime(last_visit_time)
            history.append({
                'url': url,
                'title': title,
                'last_visit_time': dt.isoformat() if dt else None
            })
    conn.close()
    os.remove(tmp_path)
    print(json.dumps(history, indent=2))

def main():
    browsers = available_browsers()
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    if arg:
        if os.path.exists(arg):
            # Custom path
            extract_history_from_sqlite(arg, 'custom')
            return
        elif arg in browsers:
            extract_history_from_sqlite(browsers[arg], arg)
            return
        else:
            print(f"Unknown browser or file: {arg}")
            print(f"Available browsers: {list(browsers.keys())}")
            return
    if not browsers:
        print("No supported browser history files found.")
        print(f"Checked: {BROWSER_PATHS}")
        return
    # Prompt user to select
    print("Available browsers:")
    for i, (name, path) in enumerate(browsers.items()):
        print(f"  {i+1}. {name} ({path})")
    try:
        choice = int(input("Select browser [1]: ") or "1")
        name = list(browsers.keys())[choice-1]
        extract_history_from_sqlite(browsers[name], name)
    except (ValueError, IndexError):
        print("Invalid selection.")

if __name__ == '__main__':
    main() 