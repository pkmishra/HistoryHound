// HistoryHounder Settings Script
// Handles all settings functionality and user interactions

// Default settings
const DEFAULT_SETTINGS = {
  // Search settings
  defaultDaysFilter: '',
  ignoreDomains: '',
  maxResults: '25',
  includeVisits: true,
  autoSearch: false,
  
  // HistoryHounder backend settings
  backendUrl: 'http://localhost:8080',
  useSemanticSearch: true,
  enableQa: true,
  maxContext: '10',
  
  // Privacy settings
  cacheHistory: true,
  cacheDuration: '5',
  analytics: false,
  debugMode: false
};

// DOM elements
const status = document.getElementById('status');
const saveBtn = document.getElementById('saveSettings');
const resetBtn = document.getElementById('resetSettings');
const exportBtn = document.getElementById('exportSettings');
const importBtn = document.getElementById('importSettings');
const clearCacheBtn = document.getElementById('clearCache');

// Initialize settings page
document.addEventListener('DOMContentLoaded', () => {
  loadSettings();
  loadStatistics();
  setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
  // Save settings
  saveBtn.addEventListener('click', saveSettings);
  
  // Reset settings
  resetBtn.addEventListener('click', resetSettings);
  
  // Export settings
  exportBtn.addEventListener('click', exportSettings);
  
  // Import settings
  importBtn.addEventListener('click', importSettings);
  
  // Clear cache
  clearCacheBtn.addEventListener('click', clearCache);
  
  // Backend test
  document.getElementById('testBackend').addEventListener('click', testBackendConnection);
  
  // Sync history
  document.getElementById('syncHistory').addEventListener('click', syncHistoryToBackend);
  
  // Auto-search change
  document.getElementById('autoSearch').addEventListener('change', updateAutoSearchHelp);
}

// Load current settings
async function loadSettings() {
  try {
    const result = await chrome.storage.sync.get(DEFAULT_SETTINGS);
    
    // Populate form fields
    Object.keys(result).forEach(key => {
      const element = document.getElementById(key);
      if (element) {
        if (element.type === 'checkbox') {
          element.checked = result[key];
        } else {
          element.value = result[key];
        }
      }
    });
    
    // Handle special cases
    updateAutoSearchHelp();
    
  } catch (error) {
    showStatus('Error loading settings: ' + error.message, 'error');
  }
}

// Save settings
async function saveSettings() {
  try {
    const settings = {};
    
    // Collect all form values
    Object.keys(DEFAULT_SETTINGS).forEach(key => {
      const element = document.getElementById(key);
      if (element) {
        if (element.type === 'checkbox') {
          settings[key] = element.checked;
        } else {
          settings[key] = element.value;
        }
      }
    });
    
    // Validate settings
    if (settings.backendUrl && !settings.backendUrl.startsWith('http')) {
      showStatus('Backend URL must start with http:// or https://', 'error');
      return;
    }
    
    // Save to storage
    await chrome.storage.sync.set(settings);
    
    // Update background script cache duration
    chrome.runtime.sendMessage({
      action: 'updateSettings',
      settings: settings
    });
    
    showStatus('Settings saved successfully!', 'success');
    
  } catch (error) {
    showStatus('Error saving settings: ' + error.message, 'error');
  }
}

// Reset settings to defaults
async function resetSettings() {
  if (confirm('Are you sure you want to reset all settings to defaults?')) {
    try {
      await chrome.storage.sync.clear();
      await chrome.storage.sync.set(DEFAULT_SETTINGS);
      
      // Reload form
      loadSettings();
      
      showStatus('Settings reset to defaults', 'success');
      
    } catch (error) {
      showStatus('Error resetting settings: ' + error.message, 'error');
    }
  }
}

// Export settings
function exportSettings() {
  chrome.storage.sync.get(null, (settings) => {
    const dataStr = JSON.stringify(settings, null, 2);
    const dataBlob = new Blob([dataStr], {type: 'application/json'});
    
    const link = document.createElement('a');
    link.href = URL.createObjectURL(dataBlob);
    link.download = 'historyhounder-settings.json';
    link.click();
    
    showStatus('Settings exported successfully', 'success');
  });
}

// Import settings
function importSettings() {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = '.json';
  
  input.onchange = (event) => {
    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = async (e) => {
        try {
          const settings = JSON.parse(e.target.result);
          
          // Validate settings
          const validSettings = {};
          Object.keys(DEFAULT_SETTINGS).forEach(key => {
            if (settings.hasOwnProperty(key)) {
              validSettings[key] = settings[key];
            }
          });
          
          await chrome.storage.sync.set(validSettings);
          loadSettings();
          
          showStatus('Settings imported successfully', 'success');
          
        } catch (error) {
          showStatus('Error importing settings: ' + error.message, 'error');
        }
      };
      reader.readAsText(file);
    }
  };
  
  input.click();
}

// Clear cache
async function clearCache() {
  if (confirm('Are you sure you want to clear the history cache? This will not delete your browser history.')) {
    try {
      await chrome.runtime.sendMessage({ action: 'clearCache' });
      showStatus('Cache cleared successfully', 'success');
    } catch (error) {
      showStatus('Error clearing cache: ' + error.message, 'error');
    }
  }
}

// Load statistics
async function loadStatistics() {
  try {
    const response = await chrome.runtime.sendMessage({
      action: 'getHistoryStats',
      filters: {}
    });
    
    if (response.success) {
      const stats = response.stats;
      
      document.getElementById('totalVisits').textContent = stats.total.toLocaleString();
      document.getElementById('uniqueDomains').textContent = Object.keys(stats.domains).length.toLocaleString();
      document.getElementById('todayVisits').textContent = stats.timeRanges.today.toLocaleString();
      document.getElementById('weekVisits').textContent = stats.timeRanges.week.toLocaleString();
    }
    
  } catch (error) {
    console.error('Error loading statistics:', error);
  }
}

// Test backend connection
async function testBackendConnection() {
  const backendUrl = document.getElementById('backendUrl').value;
  
  if (!backendUrl) {
    showStatus('Please enter a backend URL', 'error');
    return;
  }
  
  try {
    const response = await fetch(`${backendUrl}/api/health`);
    const result = await response.json();
    
    if (result.status === 'healthy') {
      showStatus(`✅ Backend connected successfully! HistoryHounder available: ${result.historyhounder_available}`, 'success');
    } else {
      showStatus('❌ Backend responded but status is not healthy', 'error');
    }
  } catch (error) {
    showStatus(`❌ Backend connection failed: ${error.message}`, 'error');
  }
}

// Sync history to backend
async function syncHistoryToBackend() {
  const backendUrl = document.getElementById('backendUrl').value;
  
  if (!backendUrl) {
    showStatus('Please enter a backend URL', 'error');
    return;
  }
  
  try {
    showStatus('Clearing cache and fetching latest history...', 'info');
    
    // Clear cache first to ensure we get the latest history
    await chrome.runtime.sendMessage({
      action: 'clearCache'
    });
    
    // Get fresh history data from Chrome (bypasses 5-minute cache)
    const historyResponse = await chrome.runtime.sendMessage({
      action: 'getFreshHistoryData',
      filters: {}
    });
    
    if (!historyResponse.success) {
      throw new Error(historyResponse.error || 'Failed to get history data');
    }
    
    let history = historyResponse.results;
    console.log('Raw history:', history);
    
    if (!history || history.length === 0) {
      showStatus('No history data found. Please check your browser history.', 'error');
      return;
    }
    
    // Validate and filter history data
    const filteredHistory = history
      .filter(item => {
        // Ensure required fields exist
        if (!item.url || !item.title) {
          console.warn('Skipping item with missing required fields:', item);
          return false;
        }
        return true;
      })
      .map(item => {
        // Convert lastVisitTime to integer (remove decimal part) and ensure microseconds
        let lastVisitTime = Math.floor(Number(item.lastVisitTime ?? 0));
        
        // Ensure it's in microseconds (Chrome uses microseconds)
        if (lastVisitTime < 1000000000000) {
          // If it's in milliseconds, convert to microseconds
          lastVisitTime = lastVisitTime * 1000;
        }
        
        return {
          id: String(item.id ?? item.url ?? ''),
          url: String(item.url ?? ''),
          title: String(item.title ?? ''),
          lastVisitTime: lastVisitTime,
          visitCount: Number(item.visitCount ?? 1)
        };
      });
    
    console.log('Filtered history:', filteredHistory);
    console.log('Sample item:', filteredHistory[0]);
    
    if (filteredHistory.length === 0) {
      showStatus('No valid history items found to sync', 'error');
      return;
    }
    
    // Send to backend
    console.log('Sending history to backend:', {
      history: filteredHistory,
      count: filteredHistory.length,
      sample: filteredHistory[0]
    });
    
    const response = await fetch(`${backendUrl}/api/process-history`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        history: filteredHistory
      })
    });
    
    console.log('Backend response status:', response.status);
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('Backend error response:', errorText);
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }
    
    const result = await response.json();
    console.log('Backend response:', result);
    
    if (result.success) {
      const message = `✅ History synced successfully! 
Processed ${result.processed_count} items from ${filteredHistory.length} total history entries.`;
      showStatus(message, 'success');
    } else {
      showStatus(`❌ History sync failed: ${result.error}`, 'error');
    }
  } catch (error) {
    console.error('Sync error:', error);
    showStatus(`❌ History sync failed: ${error.message}`, 'error');
  }
}

// Update auto-search help text
function updateAutoSearchHelp() {
  const autoSearch = document.getElementById('autoSearch').checked;
  const helpText = autoSearch ? 
    'Popup will automatically search for recent history when opened' :
    'Popup will show empty search interface when opened';
  
  // You could add a help text element to show this
}

// Show status message
function showStatus(message, type = 'success') {
  status.textContent = message;
  status.className = `status ${type}`;
  status.style.display = 'block';
  
  // Auto-hide after 3 seconds
  setTimeout(() => {
    status.style.display = 'none';
  }, 3000);
}

// Handle page visibility change
document.addEventListener('visibilitychange', () => {
  if (!document.hidden) {
    loadStatistics(); // Refresh stats when page becomes visible
  }
}); 