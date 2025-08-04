"""
MCP (Model Context Protocol) tools for browser history access.

Provides tools for retrieving browser history data through the MCP protocol,
including filtering, statistics, and cross-platform browser support.
"""

import json
import sqlite3
import shutil
import tempfile
import platform
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse
import logging

from .config import config
from .browser_detection import (
    get_browser_info, 
    get_accessible_browsers, 
    extract_domain_from_url,
    validate_browser_access
)
from .models import (
    BrowserHistoryItem, 
    BrowserHistoryResult, 
    HistoryStatistics,
    SupportedBrowser,
    BrowserListResult
)

logger = logging.getLogger(__name__)


def chrome_time_to_datetime(chrome_time: int) -> Optional[datetime]:
    """Convert Chrome timestamp to datetime."""
    if chrome_time == 0:
        return None
    epoch_start = datetime(1601, 1, 1)
    return epoch_start + timedelta(microseconds=chrome_time)


def firefox_time_to_datetime(firefox_time: int) -> Optional[datetime]:
    """Convert Firefox timestamp to datetime."""
    if firefox_time == 0:
        return None
    epoch_start = datetime(1970, 1, 1)
    return epoch_start + timedelta(microseconds=firefox_time)


def safari_time_to_datetime(safari_time: int) -> Optional[datetime]:
    """Convert Safari timestamp to datetime."""
    if safari_time == 0:
        return None
    epoch_start = datetime(2001, 1, 1)
    return epoch_start + timedelta(seconds=safari_time)


def extract_history_from_browser(browser_name: str, limit: int = 100, 
                               start_date: Optional[datetime] = None,
                               end_date: Optional[datetime] = None,
                               domain_filter: Optional[str] = None) -> BrowserHistoryResult:
    """Extract history from a specific browser with filtering options."""
    
    # Validate browser access
    is_accessible, message = validate_browser_access(browser_name)
    if not is_accessible:
        raise ValueError(f"Cannot access {browser_name}: {message}")
    
    browser_info = get_browser_info(browser_name)
    if not browser_info or not browser_info.accessible:
        raise ValueError(f"Browser {browser_name} is not accessible")
    
    # Create temporary copy of database (browsers lock the original)
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        tmp_path = tmp_file.name
    
    try:
        shutil.copy2(browser_info.path, tmp_path)
        
        conn = sqlite3.connect(tmp_path)
        cursor = conn.cursor()
        
        history_items = []
        
        if browser_name.startswith('firefox'):
            # Firefox uses 'places.sqlite' and different schema
            query = """
                SELECT url, title, last_visit_date, visit_count 
                FROM moz_places 
                WHERE last_visit_date IS NOT NULL
                ORDER BY last_visit_date DESC
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            
            for url, title, last_visit_date, visit_count in rows:
                if not url:
                    continue
                    
                # Apply domain filter
                if domain_filter and domain_filter.lower() not in url.lower():
                    continue
                
                # Convert timestamp
                dt = firefox_time_to_datetime(last_visit_date) if last_visit_date else None
                
                # Apply date filters
                if start_date and dt and dt < start_date:
                    continue
                if end_date and dt and dt > end_date:
                    continue
                
                domain = extract_domain_from_url(url)
                
                history_items.append(BrowserHistoryItem(
                    id=str(len(history_items) + 1),
                    url=url,
                    title=title or "Untitled",
                    last_visit_time=dt or datetime.now(),
                    visit_count=visit_count or 1,
                    browser=browser_name,
                    domain=domain
                ))
                
                if len(history_items) >= limit:
                    break
                    
        elif browser_name == 'safari':
            # Safari uses History.db
            query = """
                SELECT url, title, visit_time 
                FROM history_items 
                LEFT JOIN history_visits ON history_items.id = history_visits.history_item
                WHERE visit_time IS NOT NULL
                ORDER BY visit_time DESC
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            
            for url, title, visit_time in rows:
                if not url:
                    continue
                    
                # Apply domain filter
                if domain_filter and domain_filter.lower() not in url.lower():
                    continue
                
                # Convert timestamp
                dt = safari_time_to_datetime(visit_time) if visit_time else None
                
                # Apply date filters
                if start_date and dt and dt < start_date:
                    continue
                if end_date and dt and dt > end_date:
                    continue
                
                domain = extract_domain_from_url(url)
                
                history_items.append(BrowserHistoryItem(
                    id=str(len(history_items) + 1),
                    url=url,
                    title=title or "Untitled",
                    last_visit_time=dt or datetime.now(),
                    visit_count=1,
                    browser=browser_name,
                    domain=domain
                ))
                
                if len(history_items) >= limit:
                    break
                    
        else:
            # Chrome/Brave/Edge
            query = """
                SELECT url, title, last_visit_time, visit_count 
                FROM urls 
                WHERE last_visit_time IS NOT NULL
                ORDER BY last_visit_time DESC
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            
            for url, title, last_visit_time, visit_count in rows:
                if not url:
                    continue
                    
                # Apply domain filter
                if domain_filter and domain_filter.lower() not in url.lower():
                    continue
                
                # Convert timestamp
                dt = chrome_time_to_datetime(last_visit_time) if last_visit_time else None
                
                # Apply date filters
                if start_date and dt and dt < start_date:
                    continue
                if end_date and dt and dt > end_date:
                    continue
                
                domain = extract_domain_from_url(url)
                
                history_items.append(BrowserHistoryItem(
                    id=str(len(history_items) + 1),
                    url=url,
                    title=title or "Untitled",
                    last_visit_time=dt or datetime.now(),
                    visit_count=visit_count or 1,
                    browser=browser_name,
                    domain=domain
                ))
                
                if len(history_items) >= limit:
                    break
        
        conn.close()
        
        return BrowserHistoryResult(
            items=history_items,
            total_count=len(history_items),
            browser=browser_name,
            query_time=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Error extracting history from {browser_name}: {e}")
        raise ValueError(f"Failed to extract history from {browser_name}: {str(e)}")
        
    finally:
        # Clean up temporary file
        try:
            import os
            os.unlink(tmp_path)
        except OSError:
            pass


def get_browser_history(browser: Optional[str] = None, 
                       limit: int = 100,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None,
                       domain: Optional[str] = None) -> Dict[str, Any]:
    """Get browser history with filtering options."""
    
    # Parse date parameters
    start_dt = None
    end_dt = None
    
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError(f"Invalid start_date format: {start_date}")
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError(f"Invalid end_date format: {end_date}")
    
    # Determine which browsers to query
    if browser:
        browsers = [browser]
    else:
        browsers = get_accessible_browsers()
    
    if not browsers:
        raise ValueError("No accessible browsers found")
    
    # Extract history from each browser
    all_results = []
    for browser_name in browsers:
        try:
            result = extract_history_from_browser(
                browser_name, 
                limit=limit,
                start_date=start_dt,
                end_date=end_dt,
                domain_filter=domain
            )
            all_results.append(result)
        except Exception as e:
            logger.warning(f"Failed to extract from {browser_name}: {e}")
            continue
    
    if not all_results:
        raise ValueError("No history data could be extracted from any browser")
    
    # Combine results
    combined_items = []
    for result in all_results:
        combined_items.extend(result.items)
    
    # Sort by visit time (most recent first)
    combined_items.sort(key=lambda x: x.last_visit_time, reverse=True)
    
    # Apply limit to combined results
    if len(combined_items) > limit:
        combined_items = combined_items[:limit]
    
    return {
        "items": [item.model_dump() for item in combined_items],
        "total_count": len(combined_items),
        "browsers_queried": [r.browser for r in all_results],
        "query_time": datetime.now().isoformat()
    }


def get_history_statistics() -> Dict[str, Any]:
    """Get statistics about browser history."""
    
    browsers = get_accessible_browsers()
    if not browsers:
        return {
            "total_items": 0,
            "browsers": {},
            "domains": {},
            "date_range": {},
            "query_time": datetime.now().isoformat()
        }
    
    all_items = []
    domain_counts = {}
    
    for browser_name in browsers:
        try:
            result = extract_history_from_browser(browser_name, limit=config.max_history_items)
            all_items.extend(result.items)
            
            # Count domains
            for item in result.items:
                if item.domain:
                    domain_counts[item.domain] = domain_counts.get(item.domain, 0) + 1
                    
        except Exception as e:
            logger.warning(f"Failed to get statistics from {browser_name}: {e}")
            continue
    
    # Calculate statistics
    browser_counts = {}
    for item in all_items:
        browser_counts[item.browser] = browser_counts.get(item.browser, 0) + 1
    
    # Get date range
    dates = [item.last_visit_time for item in all_items if item.last_visit_time]
    date_range = {}
    if dates:
        date_range = {
            "earliest": min(dates).isoformat(),
            "latest": max(dates).isoformat()
        }
    
    # Get top domains
    top_domains = dict(sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:10])
    
    return {
        "total_items": len(all_items),
        "browsers": browser_counts,
        "domains": top_domains,
        "date_range": date_range,
        "query_time": datetime.now().isoformat()
    }


def list_supported_browsers() -> Dict[str, Any]:
    """List all supported browsers and their status."""
    
    from .browser_detection import get_supported_browsers
    
    browsers = get_supported_browsers()
    platform_info = {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version()
    }
    
    return {
        "browsers": [browser.model_dump() for browser in browsers],
        "platform": platform_info,
        "query_time": datetime.now().isoformat()
    } 