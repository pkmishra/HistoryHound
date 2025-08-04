"""
FastMCP Server Implementation for Browser History

Replaces custom MCP implementation with FastMCP 2.0 for improved
development efficiency and production-ready features.
"""

import logging
from typing import Optional, Dict, Any

from fastmcp import FastMCP
from .tools import get_browser_history, get_history_statistics, list_supported_browsers

logger = logging.getLogger(__name__)


def create_mcp_server() -> FastMCP:
    """Create and configure FastMCP server for browser history access."""
    
    mcp = FastMCP("HistoryHounder 🕵️")
    
    @mcp.tool
    def get_browser_history_tool(
        browser: Optional[str] = None,
        limit: int = 100,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        domain: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve browser history with optional filtering by browser, date range, domain, and limit.
        
        Args:
            browser: Specific browser to query (chrome, firefox, safari, edge)
            limit: Maximum number of history items to return (default: 100)
            start_date: Start date for filtering (ISO format: YYYY-MM-DDTHH:MM:SS)
            end_date: End date for filtering (ISO format: YYYY-MM-DDTHH:MM:SS)
            domain: Filter by domain (e.g., "google.com")
            
        Returns:
            Dictionary containing browser history items and metadata
        """
        try:
            return get_browser_history(
                browser=browser,
                limit=limit,
                start_date=start_date,
                end_date=end_date,
                domain=domain
            )
        except Exception as e:
            logger.error(f"Error in get_browser_history: {e}")
            raise
    
    @mcp.tool
    def get_history_statistics_tool() -> Dict[str, Any]:
        """
        Get statistics about browser history including total items, browser distribution,
        top domains, and date ranges.
        
        Returns:
            Dictionary containing history statistics and analytics
        """
        try:
            return get_history_statistics()
        except Exception as e:
            logger.error(f"Error in get_history_statistics: {e}")
            raise
    
    @mcp.tool
    def list_supported_browsers_tool() -> Dict[str, Any]:
        """
        List all supported browsers and their accessibility status.
        Provides cross-platform browser detection and path information.
        
        Returns:
            Dictionary containing browser information and platform details
        """
        try:
            return list_supported_browsers()
        except Exception as e:
            logger.error(f"Error in list_supported_browsers: {e}")
            raise
    
    return mcp


def create_websocket_server() -> FastMCP:
    """Create and return a FastMCP server instance."""
    return create_mcp_server() 