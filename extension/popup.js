// HistoryHounder Popup Script
// Handles UI interactions and communicates with background script

// DOM elements - will be initialized when DOM is ready
let searchInput, searchBtn, daysFilter, ignoreDomains, resultsList;
let questionInput, askBtn, chatHistory, settingsBtn;
let refreshRecent, recentList;
let totalVisits, uniqueDomains, todayVisits, weekVisits;

// Tab elements
let tabButtons, tabContents;

// State
let currentResults = [];
let currentFilters = {};
let chatMessages = [];
let currentTab = 'search';

// Initialize popup
document.addEventListener('DOMContentLoaded', () => {
    // Initialize DOM elements
    searchInput = document.getElementById('searchInput');
    searchBtn = document.getElementById('searchBtn');
    daysFilter = document.getElementById('daysFilter');
    ignoreDomains = document.getElementById('ignoreDomains');
    resultsList = document.getElementById('resultsList');
    questionInput = document.getElementById('questionInput');
    askBtn = document.getElementById('askBtn');
    chatHistory = document.getElementById('chatHistory');
    settingsBtn = document.getElementById('settingsBtn');
    refreshRecent = document.getElementById('refreshRecent');
    recentList = document.getElementById('recentList');
    
    // Tab elements
    tabButtons = document.querySelectorAll('.tab-btn');
    tabContents = document.querySelectorAll('.tab-content');
    
    // Stats elements
    totalVisits = document.getElementById('totalVisits');
    uniqueDomains = document.getElementById('uniqueDomains');
    todayVisits = document.getElementById('todayVisits');
    weekVisits = document.getElementById('weekVisits');
    
    // Initialize popup functionality
    loadSettings();
    setupEventListeners();
    setupTabNavigation();
    
    // Load initial data after everything is set up
    setTimeout(() => {
        loadInitialData();
    }, 100);
});

// Setup event listeners
function setupEventListeners() {
    // Search functionality
    if (searchBtn) searchBtn.addEventListener('click', performSearch);
    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') performSearch();
        });
    }
    
    // Filters
    if (daysFilter) daysFilter.addEventListener('change', updateFilters);
    if (ignoreDomains) ignoreDomains.addEventListener('input', updateFilters);
    
    // Chat functionality
    if (askBtn) askBtn.addEventListener('click', askQuestion);
    if (questionInput) {
        questionInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') askQuestion();
        });
    }
    
    // Navigation
    if (settingsBtn) settingsBtn.addEventListener('click', openSettings);
    if (refreshRecent) refreshRecent.addEventListener('click', loadRecentHistory);
}

// Setup tab navigation
function setupTabNavigation() {
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.dataset.tab;
            switchTab(tabName);
        });
    });
}

// Switch between tabs
function switchTab(tabName) {
    // Update tab buttons
    tabButtons.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    
    // Update tab contents
    tabContents.forEach(content => {
        content.classList.toggle('active', content.id === `${tabName}-tab`);
    });
    
    currentTab = tabName;
    
    // Load tab-specific data
    switch(tabName) {
        case 'search':
            if (currentResults.length === 0) {
                loadRecentHistory();
            }
            break;
        case 'recent':
            loadRecentHistory();
            break;
        case 'ai':
            // Chat is ready
            break;
        case 'stats':
            loadStats();
            break;
    }
}

// Load initial data
function loadInitialData() {
    loadRecentHistory();
    loadStats();
}

// Load user settings
function loadSettings() {
    chrome.storage.sync.get(['ignoreDomains', 'defaultDaysFilter', 'maxResults', 'includeVisits', 'autoSearch'], (result) => {
        if (result.ignoreDomains) {
            ignoreDomains.value = result.ignoreDomains;
        }
        if (result.defaultDaysFilter) {
            daysFilter.value = result.defaultDaysFilter;
        }
        updateFilters();
        
        // Auto-search if enabled
        if (result.autoSearch && currentTab === 'search') {
            loadRecentHistory();
        }
    });
}

// Save user settings
function saveSettings() {
    chrome.storage.sync.set({
        ignoreDomains: ignoreDomains.value,
        defaultDaysFilter: daysFilter.value
    });
}

// Update filters and trigger search
function updateFilters() {
    currentFilters = {
        days: daysFilter && daysFilter.value ? parseInt(daysFilter.value) : null,
        ignoreDomains: ignoreDomains && ignoreDomains.value ? 
            ignoreDomains.value.split(',').map(d => d.trim()).filter(d => d) : []
    };
    
    saveSettings();
    
    // If there's a current search, re-run it with new filters
    if (searchInput && searchInput.value.trim()) {
        performSearch();
    }
}

// Perform search
async function performSearch() {
    if (!searchInput) {
        console.error('searchInput element not found');
        return;
    }
    
    const query = searchInput.value.trim();
    
    if (!query && !currentFilters.days) {
        // Show recent history if no query and no time filter
        loadRecentHistory();
        return;
    }
    
    showLoading('Searching your history...');
    hideError();
    
    try {
        const response = await chrome.runtime.sendMessage({
            action: 'searchHistory',
            query: query,
            filters: currentFilters
        });
        
        if (response.success) {
            currentResults = response.results;
            displayResults(response.results, query);
        } else {
            showError(response.error);
        }
    } catch (error) {
        showError('Failed to search history: ' + error.message);
    }
}

// Load recent history
async function loadRecentHistory() {
    try {
        const response = await chrome.runtime.sendMessage({
            action: 'getHistoryStats',
            filters: currentFilters
        });
        
        if (response.success) {
            if (currentTab === 'search') {
                displayResults(response.stats.recent, 'Recent History');
            } else if (currentTab === 'recent') {
                displayRecentList(response.stats.recent);
            }
        } else {
            showError(response.error);
        }
    } catch (error) {
        showError('Failed to load history: ' + error.message);
    }
}

// Load statistics
async function loadStats() {
    try {
        const response = await chrome.runtime.sendMessage({
            action: 'getHistoryStats',
            filters: {}
        });
        
        if (response.success) {
            displayStats(response.stats);
        } else {
            showError(response.error);
        }
    } catch (error) {
        showError('Failed to load statistics: ' + error.message);
    }
}

// Display search results
function displayResults(historyItems, query) {
    hideLoading();
    hideError();
    
    if (!resultsList) {
        console.error('resultsList element not found');
        return;
    }
    
    if (historyItems.length === 0) {
        resultsList.innerHTML = '<div class="empty-state"><p>No history items found.</p></div>';
        return;
    }
    
    const resultsHtml = historyItems.map(item => {
        const domain = new URL(item.url).hostname;
        const date = new Date(item.lastVisitTime).toLocaleDateString();
        const time = new Date(item.lastVisitTime).toLocaleTimeString();
        
        return `
            <div class="history-item" data-url="${item.url}">
                <div class="item-header">
                    <h4 class="item-title">${escapeHtml(item.title || 'Untitled')}</h4>
                    <span class="item-domain">${domain}</span>
                </div>
                <div class="item-url">${escapeHtml(item.url)}</div>
                <div class="item-meta">
                    <span class="item-date">${date} at ${time}</span>
                    <span class="item-visits">${item.visitCount || 1} visit${item.visitCount !== 1 ? 's' : ''}</span>
                </div>
            </div>
        `;
    }).join('');
    
            resultsList.innerHTML = resultsHtml;
    
    // Add click handlers to history items
    document.querySelectorAll('.history-item').forEach(item => {
        item.addEventListener('click', () => {
            chrome.tabs.create({ url: item.dataset.url });
        });
    });
}

// Display recent list
function displayRecentList(historyItems) {
    if (!recentList) {
        console.error('recentList element not found');
        return;
    }
    
    if (historyItems.length === 0) {
        recentList.innerHTML = '<div class="empty-state"><p>No recent history found.</p></div>';
        return;
    }
    
    const recentHtml = historyItems.map(item => {
        const domain = new URL(item.url).hostname;
        const date = new Date(item.lastVisitTime).toLocaleDateString();
        const time = new Date(item.lastVisitTime).toLocaleTimeString();
        
        return `
            <div class="history-item" data-url="${item.url}">
                <div class="item-header">
                    <h4 class="item-title">${escapeHtml(item.title || 'Untitled')}</h4>
                    <span class="item-domain">${domain}</span>
                </div>
                <div class="item-url">${escapeHtml(item.url)}</div>
                <div class="item-meta">
                    <span class="item-date">${date} at ${time}</span>
                    <span class="item-visits">${item.visitCount || 1} visit${item.visitCount !== 1 ? 's' : ''}</span>
                </div>
            </div>
        `;
    }).join('');
    
    recentList.innerHTML = recentHtml;
    
    // Add click handlers
    document.querySelectorAll('.history-item').forEach(item => {
        item.addEventListener('click', () => {
            chrome.tabs.create({ url: item.dataset.url });
        });
    });
}

// Display statistics
function displayStats(stats) {
    if (totalVisits) totalVisits.textContent = stats.totalVisits || '0';
    if (uniqueDomains) uniqueDomains.textContent = stats.uniqueDomains || '0';
    if (todayVisits) todayVisits.textContent = stats.todayVisits || '0';
    if (weekVisits) weekVisits.textContent = stats.weekVisits || '0';
    
    // Display top domains
    if (stats.topDomains && stats.topDomains.length > 0) {
        const domainsHtml = stats.topDomains.map(domain => `
            <div class="domain-item">
                <span class="domain-name">${escapeHtml(domain.domain)}</span>
                <span class="domain-count">${domain.count}</span>
            </div>
        `).join('');
        topDomainsList.innerHTML = domainsHtml;
    } else {
        topDomainsList.innerHTML = '<div class="empty-state"><p>No domain data available.</p></div>';
    }
}

// Ask AI question
async function askQuestion() {
    const question = questionInput.value.trim();
    
    if (!question) {
        showError('Please enter a question');
        return;
    }
    
    // Add user message to chat
    addChatMessage('user', question);
    questionInput.value = '';
    
    // Show loading in chat
    const loadingMessageId = addChatMessage('assistant', 'Thinking...', true);
    
    try {
        const response = await chrome.runtime.sendMessage({
            action: 'askQuestion',
            question: question,
            history: currentResults.length > 0 ? currentResults : null
        });
        
        if (response.success) {
            // Replace loading message with actual response
            updateChatMessage(loadingMessageId, response.answer);
            
            // Add sources if available
            if (response.sources && response.sources.length > 0) {
                const sourcesHtml = `
                    <div class="sources-section">
                        <strong>Sources:</strong>
                        <ul>
                            ${response.sources.map(source => {
                                const title = source.title || source.url || 'Untitled';
                                const url = source.url || '#';
                                const displayText = title.length > 50 ? title.substring(0, 50) + '...' : title;
                                
                                return `<li>
                                    <a href="${url}" target="_blank" title="${escapeHtml(title)}">
                                        ${escapeHtml(displayText)}
                                    </a>
                                    ${source.content ? `<br><small>${escapeHtml(source.content.substring(0, 100))}...</small>` : ''}
                                </li>`;
                            }).join('')}
                        </ul>
                    </div>
                `;
                addChatMessage('assistant', sourcesHtml);
            }
        } else {
            updateChatMessage(loadingMessageId, `Error: ${response.error}`);
        }
    } catch (error) {
        updateChatMessage(loadingMessageId, `Failed to get AI answer: ${error.message}`);
    }
}

// Add chat message
function addChatMessage(type, content, isLoading = false) {
    const messageId = Date.now() + Math.random();
    
    // Check if content contains HTML tags (more reliable detection)
    const hasHtml = content && (content.includes('<div') || content.includes('<ul') || content.includes('<li') || content.includes('<a') || content.includes('<strong'));
    
    const messageHtml = `
        <div class="chat-message ${type}" data-message-id="${messageId}">
            <div class="message-content">
                ${isLoading ? '<div class="loading-dots">...</div>' : (hasHtml ? content : escapeHtml(content))}
            </div>
        </div>
    `;
    
    chatHistory.insertAdjacentHTML('beforeend', messageHtml);
    chatHistory.scrollTop = chatHistory.scrollHeight;
    
    return messageId;
}

// Update chat message
function updateChatMessage(messageId, content) {
    const messageElement = document.querySelector(`[data-message-id="${messageId}"] .message-content`);
    if (messageElement) {
        messageElement.innerHTML = content;
    }
}

// Utility functions
function showLoading(message) {
    // Show loading state in results area
    if (resultsList) {
        resultsList.innerHTML = `
            <div class="loading-state">
                <div class="loading-spinner"></div>
                <p class="loading-text">${message}</p>
            </div>
        `;
    }
}

function hideLoading() {
    // Loading is hidden when results are displayed
}

function showError(message) {
    if (resultsList) {
        resultsList.innerHTML = `
            <div class="error-state">
                <p class="error-text">${escapeHtml(message)}</p>
            </div>
        `;
    }
}

function hideError() {
    // Error is hidden when results are displayed
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function openSettings() {
    chrome.tabs.create({ url: chrome.runtime.getURL('settings.html') });
} 