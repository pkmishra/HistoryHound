"""
Cross-platform browser detection and history file validation.

Provides functionality to detect installed browsers and validate
their history files across different operating systems.
"""

import os
import platform
import glob
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
import sqlite3
import logging

from .config import config
from .models import SupportedBrowser

logger = logging.getLogger(__name__)


def get_platform_key() -> str:
    """Get the platform key for browser path lookup."""
    system = platform.system().lower()
    if system == "darwin":
        return "darwin"
    elif system == "windows":
        return "win32"
    else:
        return "linux"


def expand_browser_path(path: str) -> List[str]:
    """Expand a browser path pattern to actual file paths."""
    expanded_path = os.path.expanduser(path)
    
    if "*" in expanded_path:
        # Handle glob patterns (like Firefox profiles)
        matches = glob.glob(expanded_path)
        return [match for match in matches if os.path.isfile(match)]
    else:
        # Single file path
        return [expanded_path] if os.path.isfile(expanded_path) else []


def validate_sqlite_file(file_path: str) -> bool:
    """Validate that a file is a valid SQLite database."""
    try:
        # Try to open the file as SQLite
        conn = sqlite3.connect(file_path)
        cursor = conn.cursor()
        
        # Check if it has the expected tables (basic validation)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        # Basic validation - should have some tables
        return len(tables) > 0
        
    except (sqlite3.Error, OSError) as e:
        logger.debug(f"Failed to validate SQLite file {file_path}: {e}")
        return False


def get_browser_info(browser_name: str) -> Optional[SupportedBrowser]:
    """Get information about a specific browser installation."""
    platform_key = get_platform_key()
    
    if platform_key not in config.browser_paths:
        return None
        
    if browser_name not in config.browser_paths[platform_key]:
        return None
        
    path_pattern = config.browser_paths[platform_key][browser_name]
    expanded_paths = expand_browser_path(path_pattern)
    
    if not expanded_paths:
        return SupportedBrowser(
            name=browser_name,
            path=path_pattern,
            exists=False,
            accessible=False
        )
    
    # Use the first valid path found
    file_path = expanded_paths[0]
    exists = os.path.isfile(file_path)
    accessible = validate_sqlite_file(file_path) if exists else False
    
    return SupportedBrowser(
        name=browser_name,
        path=file_path,
        exists=exists,
        accessible=accessible
    )


def get_supported_browsers() -> List[SupportedBrowser]:
    """Get information about all supported browsers on the current platform."""
    browsers = []
    platform_key = get_platform_key()
    
    if platform_key not in config.browser_paths:
        return browsers
    
    for browser_name in config.browser_paths[platform_key]:
        browser_info = get_browser_info(browser_name)
        if browser_info:
            browsers.append(browser_info)
    
    return browsers


def get_accessible_browsers() -> List[str]:
    """Get list of browsers with accessible history files."""
    browsers = get_supported_browsers()
    return [browser.name for browser in browsers if browser.accessible]


def extract_domain_from_url(url: str) -> str:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except Exception:
        return ""


def get_browser_history_path(browser_name: str) -> Optional[str]:
    """Get the history file path for a specific browser."""
    browser_info = get_browser_info(browser_name)
    if browser_info and browser_info.accessible:
        return browser_info.path
    return None


def validate_browser_access(browser_name: str) -> Tuple[bool, str]:
    """Validate access to a browser's history file."""
    browser_info = get_browser_info(browser_name)
    
    if not browser_info:
        return False, f"Browser '{browser_name}' not supported on this platform"
    
    if not browser_info.exists:
        return False, f"History file not found for {browser_name}: {browser_info.path}"
    
    if not browser_info.accessible:
        return False, f"History file not accessible for {browser_name}: {browser_info.path}"
    
    return True, f"Browser {browser_name} is accessible"


def get_platform_info() -> Dict[str, str]:
    """Get detailed platform information."""
    return {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version()
    }


def detect_browser_installations() -> Dict[str, Dict[str, any]]:
    """Detect all browser installations and their status."""
    browsers = get_supported_browsers()
    result = {}
    
    for browser in browsers:
        result[browser.name] = {
            "path": browser.path,
            "exists": browser.exists,
            "accessible": browser.accessible,
            "status": "accessible" if browser.accessible else "not_found" if not browser.exists else "inaccessible"
        }
    
    return result 