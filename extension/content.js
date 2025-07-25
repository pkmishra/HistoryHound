// HistoryHounder Content Script
// Provides context-aware features and page enhancement

// Initialize content script
(function() {
  'use strict';
  
  // Check if we're on a supported page
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeContentScript);
  } else {
    initializeContentScript();
  }
  
  function initializeContentScript() {
    // Add HistoryHounder context menu
    addContextMenu();
    
    // Listen for messages from popup or background
    chrome.runtime.onMessage.addListener(handleMessage);
    
    // Add page analysis on load
    analyzePage();
  }
  
  // Add context menu for HistoryHounder features
  function addContextMenu() {
    document.addEventListener('contextmenu', (event) => {
      const selectedText = window.getSelection().toString().trim();
      
      if (selectedText) {
        // Store selected text for potential use
        chrome.runtime.sendMessage({
          action: 'storeSelection',
          text: selectedText,
          url: window.location.href
        });
      }
    });
  }
  
  // Handle messages from popup or background
  function handleMessage(request, sender, sendResponse) {
    switch (request.action) {
      case 'getPageInfo':
        sendResponse({
          url: window.location.href,
          title: document.title,
          domain: window.location.hostname,
          selectedText: window.getSelection().toString().trim()
        });
        break;
        
      case 'highlightHistory':
        highlightHistoryItems(request.items);
        break;
        
      case 'addHistoryButton':
        addHistoryButton();
        break;
    }
  }
  
  // Analyze current page for HistoryHounder features
  function analyzePage() {
    const pageInfo = {
      url: window.location.href,
      title: document.title,
      domain: window.location.hostname,
      timestamp: Date.now()
    };
    
    // Send page info to background script for potential processing
    chrome.runtime.sendMessage({
      action: 'pageAnalyzed',
      pageInfo: pageInfo
    });
  }
  
  // Highlight history items on the page (if they match current page)
  function highlightHistoryItems(items) {
    // Remove existing highlights
    document.querySelectorAll('.historyhounder-highlight').forEach(el => {
      el.classList.remove('historyhounder-highlight');
    });
    
    // Add highlights for matching items
    items.forEach(item => {
      if (item.url === window.location.href) {
        // Highlight the page title or other relevant elements
        const titleElement = document.querySelector('h1, h2, .title, [class*="title"]');
        if (titleElement) {
          titleElement.classList.add('historyhounder-highlight');
        }
      }
    });
  }
  
  // Add HistoryHounder button to page
  function addHistoryButton() {
    // Check if button already exists
    if (document.getElementById('historyhounder-button')) {
      return;
    }
    
    const button = document.createElement('button');
    button.id = 'historyhounder-button';
    button.innerHTML = '🔍 HistoryHounder';
    button.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      z-index: 10000;
      background: #007bff;
      color: white;
      border: none;
      border-radius: 5px;
      padding: 8px 12px;
      font-size: 12px;
      cursor: pointer;
      box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    `;
    
    button.addEventListener('click', () => {
      // Open HistoryHounder popup or trigger search
      chrome.runtime.sendMessage({
        action: 'openPopup',
        query: document.title
      });
    });
    
    document.body.appendChild(button);
  }
  
  // Add CSS for highlights
  const style = document.createElement('style');
  style.textContent = `
    .historyhounder-highlight {
      background-color: #fff3cd !important;
      border: 2px solid #ffc107 !important;
      border-radius: 3px !important;
    }
    
    #historyhounder-button:hover {
      background: #0056b3 !important;
    }
  `;
  document.head.appendChild(style);
  
})(); 