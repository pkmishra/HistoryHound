// HistoryHounder Sidepanel JavaScript
// Provides enhanced functionality for the browser sidepanel

class HistoryHounderSidepanel {
    constructor() {
        this.currentTab = 'search';
        this.chatHistory = [];
        this.isLoading = false;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadStats();
        this.setupTabNavigation();
    }

    setupEventListeners() {
        // Tab navigation
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.switchTab(e.target.dataset.tab);
            });
        });

        // Search functionality
        const searchBtn = document.getElementById('searchBtn');
        const searchInput = document.getElementById('searchInput');
        
        searchBtn.addEventListener('click', () => this.performSearch());
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.performSearch();
        });

        // Quick action buttons
        document.getElementById('searchToday').addEventListener('click', () => this.quickSearch('today'));
        document.getElementById('searchWeek').addEventListener('click', () => this.quickSearch('week'));
        document.getElementById('searchMonth').addEventListener('click', () => this.quickSearch('month'));

        // AI Chat functionality
        const askBtn = document.getElementById('askBtn');
        const questionInput = document.getElementById('questionInput');
        
        askBtn.addEventListener('click', () => this.askQuestion());
        questionInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.askQuestion();
        });

        // Quick AI actions
        document.getElementById('askPatterns').addEventListener('click', () => this.quickQuestion('patterns'));
        document.getElementById('askRecent').addEventListener('click', () => this.quickQuestion('recent'));
        document.getElementById('askProductivity').addEventListener('click', () => this.quickQuestion('productivity'));

        // Sync functionality
        document.getElementById('syncBtn').addEventListener('click', () => this.syncHistory());
    }

    setupTabNavigation() {
        // Initialize with search tab active
        this.switchTab('search');
    }

    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}-tab`).classList.add('active');

        this.currentTab = tabName;

        // Load tab-specific data
        if (tabName === 'stats') {
            this.loadStats();
        }
    }

    async performSearch() {
        const query = document.getElementById('searchInput').value.trim();
        const daysFilter = document.getElementById('daysFilter').value;
        const ignoreDomains = document.getElementById('ignoreDomains').value;

        if (!query) {
            this.showError('Please enter a search query');
            return;
        }

        this.showLoading('Searching...');
        
        try {
            const filters = {
                text: query,
                days: daysFilter ? parseInt(daysFilter) : null,
                ignoreDomains: ignoreDomains ? ignoreDomains.split(',').map(d => d.trim()) : []
            };

            const response = await this.sendMessage('searchHistory', filters);
            
            if (response.success) {
                this.displaySearchResults(response.results);
            } else {
                this.showError(response.error || 'Search failed');
            }
        } catch (error) {
            this.showError('Search failed: ' + error.message);
        }
    }

    quickSearch(timeRange) {
        const searchInput = document.getElementById('searchInput');
        let query = '';
        
        switch (timeRange) {
            case 'today':
                query = 'sites visited today';
                document.getElementById('daysFilter').value = '1';
                break;
            case 'week':
                query = 'sites visited this week';
                document.getElementById('daysFilter').value = '7';
                break;
            case 'month':
                query = 'sites visited this month';
                document.getElementById('daysFilter').value = '30';
                break;
        }
        
        searchInput.value = query;
        this.performSearch();
    }

    displaySearchResults(results) {
        const resultsList = document.getElementById('resultsList');
        
        if (!results || results.length === 0) {
            resultsList.innerHTML = '<div class="empty-state"><p>No results found</p></div>';
            return;
        }

        const resultsHtml = results.map(item => `
            <div class="history-item" onclick="window.open('${item.url}', '_blank')">
                <div class="item-header">
                    <h3 class="item-title">${this.escapeHtml(item.title)}</h3>
                    <span class="item-domain">${this.extractDomain(item.url)}</span>
                </div>
                <div class="item-url">${this.escapeHtml(item.url)}</div>
                <div class="item-meta">
                    <span>${this.formatDate(item.visit_time || item.lastVisitTime)}</span>
                    <span class="item-visits">${item.visit_count || item.visitCount || 1} visits</span>
                </div>
            </div>
        `).join('');

        resultsList.innerHTML = resultsHtml;
    }

    async askQuestion() {
        const question = document.getElementById('questionInput').value.trim();
        
        if (!question) {
            this.showError('Please enter a question');
            return;
        }

        this.addChatMessage('user', question);
        document.getElementById('questionInput').value = '';
        
        this.showLoading('Thinking...');
        
        try {
            const response = await this.sendMessage('askQuestion', { question });
            
            if (response.success) {
                // Handle different response formats
                let answer = response.answer;
                
                if (typeof answer === 'object') {
                    // If answer is an object, try to extract the text
                    if (answer.text) {
                        answer = answer.text;
                    } else if (answer.content) {
                        answer = answer.content;
                    } else if (answer.message) {
                        answer = answer.message;
                    } else {
                        // Fallback: stringify the object
                        answer = JSON.stringify(answer, null, 2);
                    }
                } else if (typeof answer !== 'string') {
                    // Convert to string if it's not already
                    answer = String(answer);
                }
                
                this.addChatMessage('assistant', answer, response.sources);
            } else {
                this.addChatMessage('assistant', 'Sorry, I encountered an error: ' + (response.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('QA Error:', error);
            this.addChatMessage('assistant', 'Sorry, I encountered an error: ' + error.message);
        }
    }

    quickQuestion(type) {
        const questionInput = document.getElementById('questionInput');
        let question = '';
        
        switch (type) {
            case 'patterns':
                question = 'Analyze my browsing patterns. Count and list the websites I visit most frequently, including their URLs, domains, and visit times. Which sites appear most often in my history?';
                break;
            case 'recent':
                question = 'What are my most recent browsing activities? List the websites I visited recently with their URLs, titles, and visit times. Show me my latest browsing history.';
                break;
            case 'productivity':
                question = 'Analyze my browsing for work-related activity. Count and list all work-related websites I visit, including their URLs and domains. Which domains appear to be work-related vs entertainment?';
                break;
        }
        
        questionInput.value = question;
        this.askQuestion();
    }

    addChatMessage(role, content, sources = []) {
        const chatHistory = document.getElementById('chatHistory');
        
        // Clear loading state
        const loadingState = chatHistory.querySelector('.loading-state');
        if (loadingState) {
            loadingState.remove();
        }

        // Clear empty state on first message
        const emptyState = chatHistory.querySelector('.empty-state');
        if (emptyState && chatHistory.children.length === 1) {
            emptyState.remove();
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${role}`;
        
        // Ensure content is a string
        if (typeof content === 'object') {
            if (content.text) {
                content = content.text;
            } else if (content.content) {
                content = content.content;
            } else if (content.message) {
                content = content.message;
            } else {
                content = JSON.stringify(content, null, 2);
            }
        } else if (typeof content !== 'string') {
            content = String(content);
        }
        
        // Handle line breaks and formatting for better display
        let messageContent = this.escapeHtml(content)
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>');
        
        // Add sources if available
        if (sources && sources.length > 0) {
            const sourcesHtml = `
                <div class="sources-section">
                    <strong>Sources:</strong>
                    <ul>
                        ${sources.map(source => {
                            const title = source.title || source.url || 'Untitled';
                            const url = source.url || '#';
                            const displayText = title.length > 30 ? title.substring(0, 30) + '...' : title;
                            
                            return `<li>
                                <a href="${url}" target="_blank" title="${this.escapeHtml(title)}">
                                    ${this.escapeHtml(displayText)}
                                </a>
                                ${source.content ? `<br><small>${this.escapeHtml(source.content.substring(0, 80))}...</small>` : ''}
                            </li>`;
                        }).join('')}
                    </ul>
                </div>
            `;
            messageContent += sourcesHtml;
        }
        
        messageDiv.innerHTML = messageContent;
        chatHistory.appendChild(messageDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;
        
        this.chatHistory.push({ role, content, sources });
    }

    async syncHistory() {
        const syncBtn = document.getElementById('syncBtn');
        syncBtn.classList.add('syncing');
        
        try {
            const response = await this.sendMessage('syncHistoryToBackend');
            
            if (response.success) {
                this.showSuccess('History synced successfully!');
                this.loadStats(); // Refresh stats after sync
            } else {
                this.showError('Sync failed: ' + (response.error || 'Unknown error'));
            }
        } catch (error) {
            this.showError('Sync failed: ' + error.message);
        } finally {
            syncBtn.classList.remove('syncing');
        }
    }

    async loadStats() {
        try {
            const response = await this.sendMessage('getStats');
            
            if (response.success) {
                this.updateStatsDisplay(response.stats);
            }
        } catch (error) {
            console.error('Failed to load stats:', error);
        }
    }

    updateStatsDisplay(stats) {
        document.getElementById('totalVisits').textContent = stats.totalVisits || '-';
        document.getElementById('uniqueDomains').textContent = stats.uniqueDomains || '-';
        document.getElementById('todayVisits').textContent = stats.todayVisits || '-';
        document.getElementById('weekVisits').textContent = stats.weekVisits || '-';

        // Update top domains
        const topDomainsList = document.getElementById('topDomainsList');
        if (stats.topDomains && stats.topDomains.length > 0) {
            const domainsHtml = stats.topDomains.map(domain => `
                <div class="domain-item">
                    <span class="domain-name">${this.escapeHtml(domain.domain)}</span>
                    <span class="domain-count">${domain.count}</span>
                </div>
            `).join('');
            topDomainsList.innerHTML = domainsHtml;
        } else {
            topDomainsList.innerHTML = '<div class="empty-state"><p>No domain data available</p></div>';
        }
    }

    showLoading(message) {
        // For AI chat, show loading in chat history
        if (this.currentTab === 'ai') {
            const chatHistory = document.getElementById('chatHistory');
            const existingLoading = chatHistory.querySelector('.loading-state');
            
            if (existingLoading) {
                existingLoading.remove();
            }

            const loadingDiv = document.createElement('div');
            loadingDiv.className = 'loading-state';
            loadingDiv.innerHTML = `
                <div class="loading-spinner"></div>
                <p class="loading-text">${message}</p>
            `;
            
            chatHistory.appendChild(loadingDiv);
            chatHistory.scrollTop = chatHistory.scrollHeight;
        } else {
            // For other tabs, show loading in the tab content
            const currentTab = document.getElementById(`${this.currentTab}-tab`);
            const existingLoading = currentTab.querySelector('.loading-state');
            
            if (existingLoading) {
                existingLoading.remove();
            }

            const loadingDiv = document.createElement('div');
            loadingDiv.className = 'loading-state';
            loadingDiv.innerHTML = `
                <div class="loading-spinner"></div>
                <p class="loading-text">${message}</p>
            `;
            
            currentTab.appendChild(loadingDiv);
        }
    }

    showError(message) {
        // For AI chat, show error as a chat message
        if (this.currentTab === 'ai') {
            this.addChatMessage('assistant', `Error: ${message}`);
        } else {
            // For other tabs, show error in the tab content
            const currentTab = document.getElementById(`${this.currentTab}-tab`);
            const existingError = currentTab.querySelector('.error-state');
            
            if (existingError) {
                existingError.remove();
            }

            const errorDiv = document.createElement('div');
            errorDiv.className = 'error-state';
            errorDiv.innerHTML = `<p class="error-text">${this.escapeHtml(message)}</p>`;
            
            currentTab.appendChild(errorDiv);
            
            // Remove error after 5 seconds
            setTimeout(() => {
                if (errorDiv.parentNode) {
                    errorDiv.remove();
                }
            }, 5000);
        }
    }

    showSuccess(message) {
        // Create a temporary success message
        const successDiv = document.createElement('div');
        successDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #10b981;
            color: white;
            padding: 12px 16px;
            border-radius: 6px;
            font-size: 12px;
            z-index: 1000;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        `;
        successDiv.textContent = message;
        
        document.body.appendChild(successDiv);
        
        // Remove after 3 seconds
        setTimeout(() => {
            if (successDiv.parentNode) {
                successDiv.remove();
            }
        }, 3000);
    }

    async sendMessage(action, data = {}) {
        return new Promise((resolve, reject) => {
            chrome.runtime.sendMessage({ action, ...data }, (response) => {
                if (chrome.runtime.lastError) {
                    reject(new Error(chrome.runtime.lastError.message));
                } else {
                    resolve(response);
                }
            });
        });
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    extractDomain(url) {
        try {
            const domain = new URL(url).hostname;
            return domain.replace('www.', '');
        } catch {
            return 'unknown';
        }
    }

    formatDate(timestamp) {
        if (!timestamp) return 'Unknown';
        
        try {
            const date = new Date(timestamp);
            return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        } catch {
            return 'Unknown';
        }
    }
}

// Initialize the sidepanel when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new HistoryHounderSidepanel();
}); 