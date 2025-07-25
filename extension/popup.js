// HistoryHounder Popup Script
// Handles UI interactions and communicates with background script

// DOM elements
const searchInput = document.getElementById('searchInput');
const searchBtn = document.getElementById('searchBtn');
const daysFilter = document.getElementById('daysFilter');
const ignoreDomains = document.getElementById('ignoreDomains');
const loading = document.getElementById('loading');
const results = document.getElementById('results');
const resultsList = document.getElementById('resultsList');
const qaSection = document.getElementById('qa-section');
const questionInput = document.getElementById('questionInput');
const askBtn = document.getElementById('askBtn');
const qaResult = document.getElementById('qaResult');
const error = document.getElementById('error');
const errorMessage = document.getElementById('errorMessage');
const settingsBtn = document.getElementById('settingsBtn');
const helpBtn = document.getElementById('helpBtn');

// State
let currentResults = [];
let currentFilters = {};

// Initialize popup
document.addEventListener('DOMContentLoaded', () => {
  loadSettings();
  setupEventListeners();
  showLoading('Loading your history...');
  loadRecentHistory();
});

// Setup event listeners
function setupEventListeners() {
  // Search functionality
  searchBtn.addEventListener('click', performSearch);
  searchInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') performSearch();
  });
  
  // Filters
  daysFilter.addEventListener('change', updateFilters);
  ignoreDomains.addEventListener('input', updateFilters);
  
  // Q&A functionality
  askBtn.addEventListener('click', askQuestion);
  questionInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') askQuestion();
  });
  
  // Navigation
  settingsBtn.addEventListener('click', openSettings);
  helpBtn.addEventListener('click', openHelp);
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
    if (result.autoSearch) {
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
    days: daysFilter.value ? parseInt(daysFilter.value) : null,
    ignoreDomains: ignoreDomains.value ? 
      ignoreDomains.value.split(',').map(d => d.trim()).filter(d => d) : []
  };
  
  saveSettings();
  
  // If there's a current search, re-run it with new filters
  if (searchInput.value.trim()) {
    performSearch();
  }
}

// Perform search
async function performSearch() {
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
      displayResults(response.stats.recent, 'Recent History');
    } else {
      showError(response.error);
    }
  } catch (error) {
    showError('Failed to load history: ' + error.message);
  }
}

// Display search results
function displayResults(historyItems, query) {
  hideLoading();
  hideError();
  
  if (historyItems.length === 0) {
    resultsList.innerHTML = '<p class="no-results">No history items found.</p>';
    results.classList.remove('hidden');
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
  results.classList.remove('hidden');
  
  // Show Q&A section if we have results
  if (historyItems.length > 0) {
    qaSection.classList.remove('hidden');
  }
  
  // Add click handlers to history items
  document.querySelectorAll('.history-item').forEach(item => {
    item.addEventListener('click', () => {
      chrome.tabs.create({ url: item.dataset.url });
    });
  });
}

// Ask AI question
async function askQuestion() {
  const question = questionInput.value.trim();
  
  if (!question) {
    showError('Please enter a question');
    return;
  }
  
  if (currentResults.length === 0) {
    showError('No history data available. Please search for something first.');
    return;
  }
  
  showLoading('Asking AI...');
  hideError();
  
  try {
    const response = await chrome.runtime.sendMessage({
      action: 'askQuestion',
      question: question,
      history: currentResults
    });
    
    if (response.success) {
      displayAnswer(response.answer, question);
    } else {
      showError(response.error);
    }
  } catch (error) {
    showError('Failed to get AI answer: ' + error.message);
  }
}

// Display AI answer
function displayAnswer(answer, question) {
  hideLoading();
  hideError();
  
  qaResult.innerHTML = `
    <div class="qa-question">
      <strong>Q:</strong> ${escapeHtml(question)}
    </div>
    <div class="qa-answer">
      <strong>A:</strong> ${escapeHtml(answer.answer)}
    </div>
    ${answer.sources ? `
      <div class="qa-sources">
        <strong>Sources:</strong>
        <ul>
          ${answer.sources.map(source => `
            <li><a href="${source.url}" target="_blank">${escapeHtml(source.title || source.url)}</a></li>
          `).join('')}
        </ul>
      </div>
    ` : ''}
  `;
  
  qaResult.classList.remove('hidden');
}

// Utility functions
function showLoading(message) {
  loading.querySelector('p').textContent = message;
  loading.classList.remove('hidden');
  results.classList.add('hidden');
  qaResult.classList.add('hidden');
}

function hideLoading() {
  loading.classList.add('hidden');
}

function showError(message) {
  errorMessage.textContent = message;
  error.classList.remove('hidden');
  hideLoading();
}

function hideError() {
  error.classList.add('hidden');
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function openSettings() {
  chrome.tabs.create({ url: chrome.runtime.getURL('settings.html') });
}

function openHelp() {
  chrome.tabs.create({ url: 'https://github.com/your-repo/historyhounder#browser-extension' });
} 