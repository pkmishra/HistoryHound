import pytest
import platform
import os
from unittest.mock import patch
from historyhounder.extract_chrome_history import get_browser_paths, available_browsers


class TestCrossPlatformBrowserPaths:
    """Test cross-platform browser path detection."""
    
    @patch('platform.system')
    def test_windows_browser_paths(self, mock_system):
        """Test Windows browser paths."""
        mock_system.return_value = "Windows"
        
        paths = get_browser_paths()
        
        # Check that Windows paths are returned
        assert 'chrome' in paths
        assert 'edge' in paths
        assert 'brave' in paths
        assert 'firefox' in paths
        
        # Check Windows-specific paths
        assert 'AppData/Local/Google/Chrome' in paths['chrome']
        assert 'AppData/Local/Microsoft/Edge' in paths['edge']
        assert 'AppData/Local/BraveSoftware' in paths['brave']
        assert 'AppData/Roaming/Mozilla/Firefox' in paths['firefox']
        
        # Safari should not be available on Windows
        assert 'safari' not in paths
    
    @patch('platform.system')
    def test_macos_browser_paths(self, mock_system):
        """Test macOS browser paths."""
        mock_system.return_value = "Darwin"
        
        paths = get_browser_paths()
        
        # Check that macOS paths are returned
        assert 'chrome' in paths
        assert 'edge' in paths
        assert 'brave' in paths
        assert 'firefox' in paths
        assert 'safari' in paths
        
        # Check macOS-specific paths
        assert 'Library/Application Support/Google/Chrome' in paths['chrome']
        assert 'Library/Application Support/Microsoft Edge' in paths['edge']
        assert 'Library/Application Support/BraveSoftware' in paths['brave']
        assert 'Library/Application Support/Firefox' in paths['firefox']
        assert 'Library/Safari/History.db' in paths['safari']
    
    @patch('platform.system')
    def test_linux_browser_paths(self, mock_system):
        """Test Linux browser paths."""
        mock_system.return_value = "Linux"
        
        paths = get_browser_paths()
        
        # Check that Linux paths are returned
        assert 'chrome' in paths
        assert 'edge' in paths
        assert 'brave' in paths
        assert 'firefox' in paths
        
        # Check Linux-specific paths
        assert '.config/google-chrome' in paths['chrome']
        assert '.config/microsoft-edge' in paths['edge']
        assert '.config/BraveSoftware' in paths['brave']
        assert '.mozilla/firefox' in paths['firefox']
        
        # Safari should not be available on Linux
        assert 'safari' not in paths
    
    @patch('platform.system')
    def test_unknown_platform(self, mock_system):
        """Test unknown platform returns empty dict."""
        mock_system.return_value = "UnknownOS"
        
        paths = get_browser_paths()
        
        assert paths == {}
    
    def test_actual_platform_detection(self):
        """Test that the actual platform detection works."""
        paths = get_browser_paths()
        
        # Should return a dict regardless of platform
        assert isinstance(paths, dict)
        
        # Should have at least some browser paths defined
        assert len(paths) > 0
    
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_available_browsers_windows(self, mock_listdir, mock_exists):
        """Test available browsers detection on Windows."""
        # Mock that some browsers exist
        mock_exists.side_effect = lambda path: 'chrome' in path or 'edge' in path
        
        # Mock Firefox profile directory listing
        mock_listdir.return_value = ['profile1', 'profile2']
        
        browsers = available_browsers()
        
        # Should detect available browsers
        assert isinstance(browsers, dict)
    
    @patch('os.path.exists')
    @patch('os.listdir')
    def test_available_browsers_macos(self, mock_listdir, mock_exists):
        """Test available browsers detection on macOS."""
        # Mock that some browsers exist
        mock_exists.side_effect = lambda path: 'chrome' in path or 'safari' in path
        
        # Mock Firefox profile directory listing
        mock_listdir.return_value = ['profile1']
        
        browsers = available_browsers()
        
        # Should detect available browsers
        assert isinstance(browsers, dict)
    
    def test_path_expansion(self):
        """Test that paths are properly expanded."""
        paths = get_browser_paths()
        
        for browser, path in paths.items():
            # Paths should be expanded (no ~ in the final path)
            assert '~' not in path
            # Paths should be absolute
            assert os.path.isabs(path) or path.startswith('~')


class TestWindowsEdgeSpecific:
    """Test Windows Edge browser specifically."""
    
    @patch('platform.system')
    def test_windows_edge_path(self, mock_system):
        """Test that Windows Edge path is correct."""
        mock_system.return_value = "Windows"
        
        paths = get_browser_paths()
        
        # Windows Edge should be in the paths
        assert 'edge' in paths
        
        # Path should contain Windows Edge specific components
        edge_path = paths['edge']
        assert 'Microsoft' in edge_path
        assert 'Edge' in edge_path
        assert 'User Data' in edge_path
        assert 'Default' in edge_path
        assert 'History' in edge_path
    
    @patch('platform.system')
    def test_windows_edge_vs_macos_edge(self, mock_system):
        """Test that Windows and macOS Edge paths are different."""
        # Test Windows
        mock_system.return_value = "Windows"
        windows_paths = get_browser_paths()
        
        # Test macOS
        mock_system.return_value = "Darwin"
        macos_paths = get_browser_paths()
        
        # Paths should be different
        assert windows_paths['edge'] != macos_paths['edge']
        
        # Windows should have AppData
        assert 'AppData' in windows_paths['edge']
        
        # macOS should have Library
        assert 'Library' in macos_paths['edge']


if __name__ == "__main__":
    pytest.main([__file__]) 