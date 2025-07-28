# HistoryHounder Browser Extension

A powerful browser extension that allows you to search and chat with your browser history using AI-powered semantic search and Q&A capabilities.

## Features

- 🔍 **Semantic History Search**: Advanced search using HistoryHounder's semantic search capabilities
- 🤖 **AI Q&A**: Ask questions about your browsing history using Ollama LLM
  - **Statistical Questions**: "What is the most visited website?" with accurate visit count analysis
  - **Domain-Specific Questions**: "How many times did I visit GitHub?" with visit count aggregation
  - **Semantic Questions**: "What AI-related websites did I visit?" with content-based search
- 📊 **History Analytics**: View statistics about your browsing patterns
- 🎯 **Advanced Filtering**: Filter by time range and exclude specific domains
- 🔗 **Quick Access**: Click on history items to revisit pages instantly
- 🎨 **Modern UI**: Clean, intuitive interface that matches your browser's design
- 🔄 **Backend Integration**: Full integration with HistoryHounder backend for enhanced AI features
- 📡 **Real-time Processing**: Process and sync history data with the backend
- 📋 **Sidepanel Interface**: Persistent workspace with advanced features, chat history, and statistics

## Installation

### Prerequisites

1. **HistoryHounder Backend** (Required for full functionality):
   ```bash
   # Install Python dependencies
   pip install langchain-ollama langchain-chroma langchain-huggingface
   
   # Start Ollama (for AI features)
   ollama serve
   
   # Start the backend server (from main project directory)
   cd ..  # Go to main project directory
   uv run python -m historyhounder.server
   # OR use the CLI
   uv run python -m historyhounder.cli server
   
   # Access API documentation
   # Swagger UI: http://localhost:8080/docs
   # ReDoc: http://localhost:8080/redoc
   ```

2. **Browser Extension**:
   - Clone or download this repository
   - Navigate to the `extension/` folder

### For Chrome/Chromium-based browsers:

1. **Load the Extension**:
   - Open Chrome and go to `chrome://extensions/`
   - Enable "Developer mode" (toggle in the top right)
   - Click "Load unpacked"
   - Select the `extension/` folder from this repository

2. **Grant Permissions**:
   - The extension will request access to your browser history
   - Click "Allow" to enable all features

3. **Configure Backend**:
   - Click the extension icon
   - Click "Settings"
   - Verify backend URL is set to `http://localhost:8080`
   - Click "Test Backend Connection"
   - Click "Sync History to Backend" to process your history
   - **Note**: Backend server must be running from the main project directory

### For Edge:
- Follow the same steps as Chrome (Edge uses the same extension format)

### For Brave:
- Follow the same steps as Chrome (Brave is Chromium-based)

## Usage

### Basic Search
1. Click the HistoryHounder icon in your browser toolbar
2. Type your search query in the search box
3. View results with page titles, URLs, and visit information
4. Click on any result to open that page

### Advanced Filtering
- **Time Range**: Use the dropdown to filter by last 24 hours, 7 days, 30 days, or 90 days
- **Domain Exclusion**: Enter domains to exclude (e.g., "google.com, facebook.com")

### AI Q&A
1. Perform a search first to provide context
2. Use the Q&A section to ask questions about your history
3. Get intelligent answers based on your browsing patterns

**Question Types Supported**:
- **Statistical Questions**: "What is the most visited website?" - Returns accurate visit count analysis
- **Domain-Specific Questions**: "How many times did I visit GitHub?" - Aggregates visit counts for specific domains
- **Semantic Questions**: "What AI-related websites did I visit?" - Content-based search and analysis

### Sidepanel Interface
1. Right-click the HistoryHounder extension icon and select "Open side panel"
2. Access a persistent workspace with advanced features
3. Use the tabbed interface for different functionalities:
   - **Search Tab**: Advanced search with filters and quick actions
   - **Chat Tab**: AI Q&A with chat history and quick questions
   - **Stats Tab**: Detailed browsing statistics and analytics
4. Enjoy persistent chat history and enhanced workspace features

### Settings
- Click the "Settings" button to customize your experience
- Your preferences are automatically saved

## Privacy & Security

- **Local Processing**: All history data is processed locally in your browser
- **No Data Collection**: We don't collect or store your browsing data
- **Secure Permissions**: Only requests necessary permissions for functionality
- **Open Source**: Full transparency with open source code

## Syncing History to Backend

When you use the "Sync History to Backend" button in the extension settings, the extension will now automatically filter and map your browser history data to only the required fields and correct types before sending it to the backend. This ensures compatibility with the backend API and prevents 422 Unprocessable Entity errors.

### Troubleshooting

- **422 Unprocessable Entity Error**: If you see this error when syncing history, make sure you are using the latest version of the extension. The extension must send only the required fields (`id`, `url`, `title`, `lastVisitTime`, `visitCount`) and ensure they are the correct types. If you have modified the extension, ensure this mapping is present in `settings.js`.

## Technical Details

### Architecture
- **Manifest V3**: Uses the latest Chrome extension manifest format
- **Service Worker**: Background script for history processing
- **Content Script**: Page enhancement and context awareness
- **Popup Interface**: Modern, responsive UI for user interaction

### Permissions Used
- `history`: Access to browser history for search functionality
- `storage`: Save user preferences and settings
- `activeTab`: Access current tab information
- `scripting`: Execute content scripts for page enhancement

### Browser Compatibility
- ✅ Chrome 88+
- ✅ Edge 88+
- ✅ Brave 1.20+
- ✅ Other Chromium-based browsers

## Development

### Project Structure
```
extension/
├── manifest.json          # Extension configuration
├── background.js          # Service worker for background tasks
├── popup.html            # Extension popup interface
├── popup.js              # Popup functionality
├── popup.css             # Popup styling
├── sidepanel.html        # Sidepanel interface
├── sidepanel.js          # Sidepanel functionality
├── content.js            # Content script for page enhancement
├── icons/                # Extension icons
│   ├── icon16.png
│   ├── icon48.png
│   └── icon128.png
└── README.md             # This file
```

### Building Icons
To regenerate the extension icons:
```bash
cd extension
python3 create_simple_icons.py
```

### Testing
1. Load the extension in developer mode
2. Test search functionality with various queries
3. Verify filtering works correctly
4. Check Q&A features with different questions

## Troubleshooting

### Extension Not Loading
- Ensure you're using a Chromium-based browser
- Check that Developer mode is enabled
- Verify all files are present in the extension folder

### Search Not Working
- Check that history permissions are granted
- Try refreshing the extension
- Clear browser cache and reload

### Q&A Not Responding
- Make sure you've performed a search first
- Check your internet connection (for AI features)
- Try a different question format
- Ensure the backend server is running and accessible
- Check that Ollama is running with the correct model (default: llama3.2:latest)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This extension is part of the HistoryHounder project and follows the same license terms.

## TODO - Future Enhancements

### 🚀 **Planned Features**

#### **User Experience Improvements**
- [ ] **Keyboard Shortcuts**: Add keyboard shortcuts for common actions (Ctrl+S for search, etc.)
- [ ] **Search Suggestions**: Auto-complete and search suggestions based on history
- [ ] **Search History**: Remember and display recent searches
- [ ] **Voice Input**: Speech-to-text functionality for AI chat
- [ ] **Custom Themes**: Light/dark mode toggle with theme customization
- [ ] **Export Features**: Export search results, statistics, or chat history
- [ ] **Bookmark Integration**: Connect with browser bookmarks for enhanced search

#### **Advanced Functionality**
- [ ] **Advanced Filters**: Date range picker, file type filters, visit count filters
- [ ] **Smart Categories**: Auto-categorize websites (work, personal, shopping, etc.)
- [ ] **Search Analytics**: Track search patterns and popular queries
- [ ] **Offline Mode**: Cache data for offline access and search
- [ ] **Batch Operations**: Select multiple history items for bulk actions
- [ ] **Search Templates**: Save and reuse complex search queries

#### **AI & Analytics Enhancements**
- [ ] **Personalized Insights**: AI-generated insights about browsing patterns
- [ ] **Predictive Search**: Suggest searches based on time of day and patterns
- [ ] **Content Analysis**: Analyze page content for better categorization
- [ ] **Usage Analytics**: Detailed analytics dashboard with charts and graphs
- [ ] **Export Reports**: Generate PDF/CSV reports of browsing statistics

#### **Integration & Connectivity**
- [ ] **Cross-Browser Sync**: Sync settings and data across browsers
- [ ] **Cloud Backup**: Optional cloud backup of settings and preferences
- [ ] **API Integration**: Connect with external services (Notion, Obsidian, etc.)
- [ ] **Webhook Support**: Send notifications to external services
- [ ] **Mobile Companion**: Mobile app for viewing statistics and insights

#### **Performance & Technical**
- [ ] **Lazy Loading**: Implement lazy loading for large history datasets
- [ ] **Search Indexing**: Optimize search performance with better indexing
- [ ] **Memory Management**: Improve memory usage for large history files
- [ ] **Background Sync**: Automatic background synchronization
- [ ] **Progressive Web App**: PWA capabilities for standalone use

#### **Accessibility & Internationalization**
- [ ] **Screen Reader Support**: Enhanced accessibility for visually impaired users
- [ ] **High Contrast Mode**: Dedicated high contrast theme
- [ ] **Internationalization**: Multi-language support (i18n)
- [ ] **Keyboard Navigation**: Full keyboard navigation support
- [ ] **Voice Commands**: Voice control for hands-free operation

#### **Security & Privacy**
- [ ] **End-to-End Encryption**: Encrypt sensitive data
- [ ] **Privacy Controls**: Granular privacy settings and data controls
- [ ] **Data Anonymization**: Option to anonymize data for analytics
- [ ] **Audit Log**: Track data access and usage
- [ ] **GDPR Compliance**: Full GDPR compliance features

### 🎯 **Priority Levels**

#### **High Priority** (Next Release)
- [ ] Keyboard shortcuts
- [ ] Search suggestions
- [ ] Custom themes (light/dark mode)
- [ ] Export features
- [ ] Enhanced accessibility

#### **Medium Priority** (Future Releases)
- [ ] Advanced filters
- [ ] Smart categories
- [ ] Offline mode
- [ ] Cross-browser sync
- [ ] Performance optimizations

#### **Low Priority** (Long-term)
- [ ] Voice input
- [ ] Mobile companion
- [ ] API integrations
- [ ] Cloud backup
- [ ] Internationalization

### 🤝 **Contributing to TODO Items**

We welcome contributions! If you'd like to work on any of these features:

1. **Check the Issues**: Look for existing issues related to the feature
2. **Create a Proposal**: Open an issue describing your implementation plan
3. **Follow Guidelines**: Ensure your code follows our coding standards
4. **Test Thoroughly**: Include tests for new functionality
5. **Document Changes**: Update documentation for new features

---

## Support

For issues and questions:
- Check the main HistoryHounder repository
- Open an issue with detailed information
- Include browser version and extension version

---

**Note**: This extension is designed to work with the HistoryHounder backend for full AI functionality. Some features may be limited when used standalone. 