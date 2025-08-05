"""
Configuration for the MCP (Model Context Protocol) Server

Provides cross-platform configuration for browser paths, server settings,
and MCP protocol parameters.
"""

import os
import platform
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class MCPConfig(BaseModel):
    """Configuration for the MCP server and browser detection."""
    
    # Server settings
    host: str = Field(default="localhost", description="MCP server host")
    port: int = Field(default=8081, description="MCP server port")
    
    # Browser paths by platform
    browser_paths: Dict[str, Dict[str, str]] = Field(
        default_factory=lambda: {
            "darwin": {  # macOS
                "chrome": "~/Library/Application Support/Google/Chrome/Default/History",
                "firefox": "~/Library/Application Support/Firefox/Profiles/*/places.sqlite",
                "safari": "~/Library/Safari/History.db",
                "edge": "~/Library/Application Support/Microsoft Edge/Default/History",
                "brave": "~/Library/Application Support/BraveSoftware/Brave-Browser/Default/History"
            },
            "linux": {  # Linux
                "chrome": "~/.config/google-chrome/Default/History",
                "firefox": "~/.mozilla/firefox/*.default*/places.sqlite",
                "edge": "~/.config/microsoft-edge/Default/History",
                "brave": "~/.config/BraveSoftware/Brave-Browser/Default/History"
            },
            "win32": {  # Windows
                "chrome": "~/AppData/Local/Google/Chrome/User Data/Default/History",
                "firefox": "~/AppData/Roaming/Mozilla/Firefox/Profiles/*/places.sqlite",
                "edge": "~/AppData/Local/Microsoft/Edge/User Data/Default/History",
                "brave": "~/AppData/Local/BraveSoftware/Brave-Browser/User Data/Default/History"
            }
        },
        description="Browser history file paths by platform and browser"
    )
    
    # MCP protocol settings
    protocol_version: str = Field(default="2024-11-05", description="MCP protocol version")
    server_name: str = Field(default="historyhounder-mcp", description="MCP server name")
    server_version: str = Field(default="1.0.0", description="MCP server version")
    
    # Tool settings
    max_history_items: int = Field(default=1000, description="Maximum history items to return")
    default_limit: int = Field(default=100, description="Default limit for history queries")
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    enable_debug: bool = Field(default=False, description="Enable debug mode")
    
    @classmethod
    def from_env(cls) -> "MCPConfig":
        """Create configuration from environment variables."""
        return cls(
            host=os.getenv("MCP_HOST", "localhost"),
            port=int(os.getenv("MCP_PORT", "8081")),
            max_history_items=int(os.getenv("MCP_MAX_HISTORY_ITEMS", "1000")),
            default_limit=int(os.getenv("MCP_DEFAULT_LIMIT", "100")),
            log_level=os.getenv("MCP_LOG_LEVEL", "INFO"),
            enable_debug=os.getenv("MCP_DEBUG", "false").lower() == "true"
        )
    
    def get_browser_path(self, browser: str) -> Optional[str]:
        """Get the history file path for a specific browser on current platform."""
        system = platform.system().lower()
        platform_key = "darwin" if system == "darwin" else "win32" if system == "windows" else "linux"
        
        if platform_key not in self.browser_paths:
            return None
            
        if browser not in self.browser_paths[platform_key]:
            return None
            
        path = self.browser_paths[platform_key][browser]
        expanded_path = os.path.expanduser(path)
        
        # Handle glob patterns (like Firefox profiles)
        if "*" in expanded_path:
            import glob
            matches = glob.glob(expanded_path)
            return matches[0] if matches else None
            
        return expanded_path
    
    def get_supported_browsers(self) -> List[str]:
        """Get list of browsers supported on current platform."""
        system = platform.system().lower()
        platform_key = "darwin" if system == "darwin" else "win32" if system == "windows" else "linux"
        
        if platform_key not in self.browser_paths:
            return []
            
        return list(self.browser_paths[platform_key].keys())
    
    def validate_browser_paths(self) -> Dict[str, bool]:
        """Validate that browser history files exist and are accessible."""
        results = {}
        for browser in self.get_supported_browsers():
            path = self.get_browser_path(browser)
            if path:
                results[browser] = Path(path).exists()
            else:
                results[browser] = False
        return results


# Global configuration instance
config = MCPConfig.from_env() 