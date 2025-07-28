// HistoryHounder Background Script
// Handles history access and communication with popup

// Store for history data
let historyCache = new Map();
let lastCacheTime = 0;
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

// Initialize extension
chrome.runtime.onInstalled.addListener(() => {
  console.log('HistoryHounder extension installed');
});

// Handle messages from popup and sidepanel
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  switch (request.action) {
    case 'searchHistory':
      searchHistory(request.text || request.query, request.filters || request)
        .then(results => sendResponse({ success: true, results }))
        .catch(error => sendResponse({ success: false, error: error.message }));
      return true; // Keep message channel open for async response
      
    case 'getHistoryStats':
      getHistoryStats(request.filters)
        .then(stats => sendResponse({ success: true, stats }))
        .catch(error => sendResponse({ success: false, error: error.message }));
      return true;
      
    case 'getStats':
      getHistoryStats(request.filters)
        .then(stats => sendResponse({ success: true, stats }))
        .catch(error => sendResponse({ success: false, error: error.message }));
      return true;
      
    case 'getHistoryData':
      getHistoryData(request.filters)
        .then(results => sendResponse({ success: true, results }))
        .catch(error => sendResponse({ success: false, error: error.message }));
      return true;
      
    case 'getFreshHistoryData':
      getFreshHistoryData(request.filters)
        .then(results => sendResponse({ success: true, results }))
        .catch(error => sendResponse({ success: false, error: error.message }));
      return true;
      
    case 'askQuestion':
      askQuestion(request.question, request.history)
        .then(result => sendResponse({ success: true, answer: result.answer, sources: result.sources }))
        .catch(error => sendResponse({ success: false, error: error.message }));
      return true;
      
    case 'syncHistoryToBackend':
      syncHistoryToBackend()
        .then(result => sendResponse({ success: true, ...result }))
        .catch(error => sendResponse({ success: false, error: error.message }));
      return true;
      
    case 'updateSettings':
      updateSettings(request.settings)
        .then(() => sendResponse({ success: true }))
        .catch(error => sendResponse({ success: false, error: error.message }));
      return true;
      
    case 'clearCache':
      clearCache()
        .then(() => sendResponse({ success: true }))
        .catch(error => sendResponse({ success: false, error: error.message }));
      return true;
      
    case 'storeSelection':
      storeSelection(request.text, request.url);
      return false; // No response needed
      
    case 'pageAnalyzed':
      handlePageAnalysis(request.pageInfo);
      return false; // No response needed
      
    case 'openPopup':
      // This would be handled by the popup itself
      return false;
      
    default:
      console.warn('Unknown action:', request.action);
      return false;
  }
});

// Search browser history with HistoryHounder semantic search
async function searchHistory(query, filters = {}) {
  try {
    // If there's a specific query, try HistoryHounder semantic search first
    if (query && query.trim() !== '') {
      const settings = await chrome.storage.sync.get(['useSemanticSearch', 'backendUrl']);
      const useSemanticSearch = settings.useSemanticSearch !== false; // Default to true
      const backendUrl = settings.backendUrl || 'http://localhost:8080';
      
      if (useSemanticSearch) {
        try {
          // Try semantic search with HistoryHounder backend
          const response = await fetch(`${backendUrl}/api/search?q=${encodeURIComponent(query.trim())}&top_k=20`);
          
          if (response.ok) {
            const result = await response.json();
            if (result.success) {
              // Convert HistoryHounder results to Chrome history format
              const semanticResults = result.results.map(item => ({
                id: item.url, // Use URL as ID
                url: item.url,
                title: item.title,
                lastVisitTime: new Date(item.visit_time).getTime(),
                visitCount: 1,
                typedCount: 0,
                domain: item.domain
              }));
              
              // Filter by ignored domains if specified
              if (filters.ignoreDomains && filters.ignoreDomains.length > 0) {
                return semanticResults.filter(item => {
                  const domain = new URL(item.url).hostname;
                  return !filters.ignoreDomains.some(ignoredDomain => 
                    domain.includes(ignoredDomain) || ignoredDomain.includes(domain)
                  );
                });
              }
              
              return semanticResults;
            }
          }
        } catch (error) {
          console.log('Semantic search failed, falling back to Chrome search:', error);
        }
      }
      
      // Fallback to Chrome's search API
      const searchQuery = {
        text: query.trim(),
        maxResults: 100
      };
      
      if (filters.days) {
        const cutoffTime = Date.now() - (filters.days * 24 * 60 * 60 * 1000);
        searchQuery.startTime = cutoffTime;
      }
      
      const results = await chrome.history.search(searchQuery);
      
      // Filter by ignored domains if specified
      if (filters.ignoreDomains && filters.ignoreDomains.length > 0) {
        return results.filter(item => {
          const domain = new URL(item.url).hostname;
          return !filters.ignoreDomains.some(ignoredDomain => 
            domain.includes(ignoredDomain) || ignoredDomain.includes(domain)
          );
        });
      }
      
      return results;
    } else {
      // If no query, get recent history
      const history = await getHistoryData(filters);
      return history.slice(0, 20); // Return recent history if no query
    }
  } catch (error) {
    console.error('Error searching history:', error);
    throw error;
  }
}

// Get history statistics
async function getHistoryStats(filters = {}) {
  try {
    // Use Chrome's history search API with empty text to get all history
    const searchQuery = {
      text: '', // Required property
      maxResults: 1000 // Get more results for better stats
    };
    
    if (filters.days) {
      const cutoffTime = Date.now() - (filters.days * 24 * 60 * 60 * 1000);
      searchQuery.startTime = cutoffTime;
    }
    
    const history = await chrome.history.search(searchQuery);
    
    // Filter by ignored domains if specified
    let filteredHistory = history;
    if (filters.ignoreDomains && filters.ignoreDomains.length > 0) {
      filteredHistory = history.filter(item => {
        const domain = new URL(item.url).hostname;
        return !filters.ignoreDomains.some(ignoredDomain => 
          domain.includes(ignoredDomain) || ignoredDomain.includes(domain)
        );
      });
    }
    
    const now = Date.now();
    const dayMs = 24 * 60 * 60 * 1000;
    const weekMs = 7 * dayMs;
    const monthMs = 30 * dayMs;
    
    // Calculate statistics
    let totalVisits = 0;
    let todayVisits = 0;
    let weekVisits = 0;
    const domainCounts = {};
    
    filteredHistory.forEach(item => {
      totalVisits += item.visitCount || 1;
      
      // Count by domain
      const domain = new URL(item.url).hostname;
      domainCounts[domain] = (domainCounts[domain] || 0) + (item.visitCount || 1);
      
      // Count by time range
      const visitTime = item.lastVisitTime;
      if (now - visitTime < dayMs) todayVisits += (item.visitCount || 1);
      if (now - visitTime < weekMs) weekVisits += (item.visitCount || 1);
    });
    
    // Get unique domains count
    const uniqueDomains = Object.keys(domainCounts).length;
    
    // Get top domains
    const topDomains = Object.entries(domainCounts)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 10)
      .map(([domain, count]) => ({ domain, count }));
    
    const stats = {
      totalVisits,
      uniqueDomains,
      todayVisits,
      weekVisits,
      recent: filteredHistory.slice(0, 10),
      topDomains
    };
    
    return stats;
  } catch (error) {
    console.error('Error getting history stats:', error);
    throw error;
  }
}

// Get history data with caching
async function getHistoryData(filters = {}) {
  const cacheKey = JSON.stringify(filters);
  const now = Date.now();
  
  // Return cached data if still valid
  if (historyCache.has(cacheKey) && (now - lastCacheTime) < CACHE_DURATION) {
    return historyCache.get(cacheKey);
  }
  
  return await fetchHistoryData(filters, true);
}

// Get fresh history data without caching
async function getFreshHistoryData(filters = {}) {
  return await fetchHistoryData(filters, false);
}

// Fetch history data from Chrome API
async function fetchHistoryData(filters = {}, shouldCache = true) {
  const now = Date.now();
  
  // Build search query - Chrome history API requires 'text' property
  const searchQuery = {
    text: '', // Required property, empty string for all history
    maxResults: 1000 // Limit results for performance
  };
  
  if (filters.days) {
    const cutoffTime = now - (filters.days * 24 * 60 * 60 * 1000);
    searchQuery.startTime = cutoffTime;
  }
  
  // Note: Chrome history API doesn't support URL filtering in the query
  // We'll filter domains after fetching the data
  
  // Fetch history from Chrome API
  const history = await chrome.history.search(searchQuery);
  
  // Filter by ignored domains if specified
  let filteredHistory = history;
  if (filters.ignoreDomains && filters.ignoreDomains.length > 0) {
    filteredHistory = history.filter(item => {
      const domain = new URL(item.url).hostname;
      return !filters.ignoreDomains.some(ignoredDomain => 
        domain.includes(ignoredDomain) || ignoredDomain.includes(domain)
      );
    });
  }
  
  // Cache the results if requested
  if (shouldCache) {
    const cacheKey = JSON.stringify(filters);
    historyCache.set(cacheKey, filteredHistory);
    lastCacheTime = now;
  }
  
  return filteredHistory;
}

// Ask AI question about history using HistoryHounder backend
async function askQuestion(question, history) {
  try {
    // Get backend URL from settings or use default
    const settings = await chrome.storage.sync.get(['backendUrl']);
    const backendUrl = settings.backendUrl || 'http://localhost:8080';
    
    // Send question to HistoryHounder backend
    const response = await fetch(`${backendUrl}/api/qa`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        question: question,
        top_k: 5
      })
    });
    
    if (!response.ok) {
      throw new Error(`Backend error: ${response.status} ${response.statusText}`);
    }
    
    const result = await response.json();
    
    if (result.success) {
      // Handle new source format with metadata
      const sources = result.sources || [];
      const formattedSources = sources.map(source => {
        // If source is already an object with metadata, use it
        if (typeof source === 'object' && source.url) {
          return {
            title: source.title || source.url,
            url: source.url,
            content: source.content || ''
          };
        }
        // If source is a string (old format), convert to object
        else if (typeof source === 'string') {
          return {
            title: source.substring(0, 50) + '...',
            url: '',
            content: source
          };
        }
        // Default fallback
        else {
          return {
            title: 'Unknown source',
            url: '',
            content: String(source)
          };
        }
      });
      
      return {
        answer: result.answer,
        sources: formattedSources
      };
    } else {
      throw new Error(result.error || 'Unknown backend error');
    }
    
  } catch (error) {
    console.error('HistoryHounder backend error:', error);
    
    // Fallback to local response if backend is unavailable
    return {
      answer: `I found ${history.length} relevant history items for your question: "${question}". The HistoryHounder backend is currently unavailable - please start the backend server.`,
      sources: history.slice(0, 5).map(item => ({
        title: item.title || 'Untitled',
        url: item.url,
        content: `Visited on ${new Date(item.lastVisitTime).toLocaleDateString()}`
      }))
    };
  }
}

// Update settings
async function updateSettings(settings) {
  // Update cache duration if changed
  if (settings.cacheDuration) {
    CACHE_DURATION = parseInt(settings.cacheDuration) * 60 * 1000;
  }
  
  // Clear cache if cache settings changed
  if (settings.cacheHistory === false) {
    historyCache.clear();
    lastCacheTime = 0;
  }
}

// Clear cache
async function clearCache() {
  try {
    // Clear local cache
    historyCache.clear();
    lastCacheTime = 0;
    
    // Clear backend cache
    const settings = await chrome.storage.sync.get(['backendUrl']);
    const backendUrl = settings.backendUrl || 'http://localhost:8080';
    
    const response = await fetch(`${backendUrl}/api/clear-cache`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      }
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('Backend clear cache error:', errorText);
      throw new Error(`Backend clear cache failed: ${response.status} ${response.statusText}`);
    }
    
    const result = await response.json();
    console.log('Cache cleared successfully:', result.message);
    
  } catch (error) {
    console.error('Clear cache failed:', error);
    // Still clear local cache even if backend fails
    historyCache.clear();
    lastCacheTime = 0;
    throw error;
  }
}

// Store selected text
function storeSelection(text, url) {
  // Store selected text for potential use in Q&A
  chrome.storage.local.set({
    lastSelection: {
      text: text,
      url: url,
      timestamp: Date.now()
    }
  });
}

// Handle page analysis
function handlePageAnalysis(pageInfo) {
  // Store page info for potential use
  chrome.storage.local.set({
    lastPageInfo: pageInfo
  });
}

// Sync history to backend
async function syncHistoryToBackend() {
  try {
    const settings = await chrome.storage.sync.get(['backendUrl']);
    const backendUrl = settings.backendUrl || 'http://localhost:8080';
    
    // Get fresh history data
    const historyData = await getFreshHistoryData();
    
    if (!historyData || historyData.length === 0) {
      return { message: 'No history data to sync' };
    }
    
    // Transform Chrome history data to backend format
    const transformedHistory = historyData.map(item => {
      // Ensure we have a valid ID
      const id = item.id || String(Date.now() + Math.random());
      
      // Handle timestamp - Chrome returns milliseconds since Unix epoch, backend expects the same
      let lastVisitTime = item.lastVisitTime;
      if (lastVisitTime) {
        // Chrome history API returns milliseconds since Unix epoch
        // Backend expects milliseconds since Unix epoch (not microseconds)
        // Just ensure it's an integer
        lastVisitTime = Math.floor(lastVisitTime);
      } else {
        lastVisitTime = Math.floor(Date.now()); // Current time in milliseconds
      }
      
      return {
        id: id,
        url: item.url,
        title: item.title || 'Untitled',
        lastVisitTime: lastVisitTime,
        visitCount: item.visitCount || 1
      };
    });
    
    console.log('Sending history data:', transformedHistory.slice(0, 3)); // Log first 3 items for debugging
    
    // Send to backend
    const response = await fetch(`${backendUrl}/api/process-history`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        history: transformedHistory
      })
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('Backend error response:', errorText);
      throw new Error(`Backend sync failed: ${response.status} ${response.statusText} - ${errorText}`);
    }
    
    const result = await response.json();
    
    // Clear cache after successful sync
    await clearCache();
    
    return {
      message: 'History synced successfully',
      processed_count: result.processed_count || 0,
      status: result.status || 'unknown'
    };
    
  } catch (error) {
    console.error('Sync to backend failed:', error);
    throw new Error(`Failed to sync history: ${error.message}`);
  }
} 