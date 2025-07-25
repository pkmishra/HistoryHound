// HistoryHounder Extension Tests
// Automated tests to verify extension functionality

class ExtensionTester {
    constructor() {
        this.results = [];
        this.testCount = 0;
        this.passCount = 0;
        this.failCount = 0;
    }

    // Test runner
    async runAllTests() {
        console.log('🧪 Starting HistoryHounder Extension Tests...\n');
        
        await this.testManifest();
        await this.testBackgroundScript();
        await this.testPopupInterface();
        await this.testContentScript();
        await this.testSettings();
        await this.testStorage();
        await this.testHistoryAccess();
        
        this.printResults();
    }

    // Test manifest.json
    async testManifest() {
        this.startTest('Manifest Validation');
        
        try {
            const manifest = chrome.runtime.getManifest();
            
            // Check required fields
            const required = ['manifest_version', 'name', 'version', 'description'];
            for (const field of required) {
                if (!manifest[field]) {
                    throw new Error(`Missing required field: ${field}`);
                }
            }
            
            // Check manifest version
            if (manifest.manifest_version !== 3) {
                throw new Error('Manifest version must be 3');
            }
            
            // Check permissions
            const requiredPermissions = ['history', 'storage'];
            for (const permission of requiredPermissions) {
                if (!manifest.permissions.includes(permission)) {
                    throw new Error(`Missing required permission: ${permission}`);
                }
            }
            
            // Check background script
            if (!manifest.background || !manifest.background.service_worker) {
                throw new Error('Missing background service worker');
            }
            
            // Check popup
            if (!manifest.action || !manifest.action.default_popup) {
                throw new Error('Missing popup configuration');
            }
            
            this.pass('Manifest is valid');
            
        } catch (error) {
            this.fail(`Manifest error: ${error.message}`);
        }
    }

    // Test background script
    async testBackgroundScript() {
        this.startTest('Background Script');
        
        try {
            const response = await this.sendMessage({
                action: 'getHistoryStats',
                filters: {}
            });
            
            if (!response) {
                throw new Error('No response from background script');
            }
            
            if (!response.success) {
                throw new Error(`Background script error: ${response.error}`);
            }
            
            if (!response.stats || typeof response.stats.total !== 'number') {
                throw new Error('Invalid stats response format');
            }
            
            this.pass(`Background script working - Found ${response.stats.total} history items`);
            
        } catch (error) {
            this.fail(`Background script error: ${error.message}`);
        }
    }

    // Test popup interface
    async testPopupInterface() {
        this.startTest('Popup Interface');
        
        try {
            // Test if popup elements exist (this would need to be run in popup context)
            const popupUrl = chrome.runtime.getURL('popup.html');
            
            // Check if popup file exists
            const response = await fetch(popupUrl);
            if (!response.ok) {
                throw new Error('Popup HTML not accessible');
            }
            
            this.pass('Popup interface accessible');
            
        } catch (error) {
            this.fail(`Popup interface error: ${error.message}`);
        }
    }

    // Test content script
    async testContentScript() {
        this.startTest('Content Script');
        
        try {
            // Check if content script is injected
            const button = document.getElementById('historyhounder-button');
            
            if (!button) {
                throw new Error('Content script not injected - no button found');
            }
            
            if (button.innerHTML !== '🔍 HistoryHounder') {
                throw new Error('Content script button has wrong text');
            }
            
            this.pass('Content script working - button found');
            
        } catch (error) {
            this.fail(`Content script error: ${error.message}`);
        }
    }

    // Test settings
    async testSettings() {
        this.startTest('Settings System');
        
        try {
            // Test settings page accessibility
            const settingsUrl = chrome.runtime.getURL('settings.html');
            const response = await fetch(settingsUrl);
            
            if (!response.ok) {
                throw new Error('Settings page not accessible');
            }
            
            // Test default settings
            const defaultSettings = {
                defaultDaysFilter: '',
                maxResults: '25',
                includeVisits: true,
                autoSearch: false,
                aiProvider: 'local',
                enableQa: true,
                cacheHistory: true,
                cacheDuration: '5'
            };
            
            const storedSettings = await this.getStorageData();
            
            // Check if settings are initialized
            for (const [key, defaultValue] of Object.entries(defaultSettings)) {
                if (storedSettings[key] === undefined) {
                    // Initialize default setting
                    await this.setStorageData({ [key]: defaultValue });
                }
            }
            
            this.pass('Settings system working');
            
        } catch (error) {
            this.fail(`Settings error: ${error.message}`);
        }
    }

    // Test storage
    async testStorage() {
        this.startTest('Storage System');
        
        try {
            const testKey = 'test_key_' + Date.now();
            const testValue = 'test_value_' + Date.now();
            
            // Test write
            await this.setStorageData({ [testKey]: testValue });
            
            // Test read
            const storedData = await this.getStorageData([testKey]);
            
            if (storedData[testKey] !== testValue) {
                throw new Error('Storage read/write failed');
            }
            
            // Test delete
            await this.removeStorageData([testKey]);
            
            const deletedData = await this.getStorageData([testKey]);
            if (deletedData[testKey] !== undefined) {
                throw new Error('Storage delete failed');
            }
            
            this.pass('Storage system working');
            
        } catch (error) {
            this.fail(`Storage error: ${error.message}`);
        }
    }

    // Test history access
    async testHistoryAccess() {
        this.startTest('History Access');
        
        try {
            // Test with empty query first
            const response = await this.sendMessage({
                action: 'searchHistory',
                query: '',
                filters: {}
            });
            
            if (!response) {
                throw new Error('No response from history search');
            }
            
            if (!response.success) {
                throw new Error(`History search error: ${response.error}`);
            }
            
            if (!Array.isArray(response.results)) {
                throw new Error('Invalid results format');
            }
            
            this.pass(`History access working - Found ${response.results.length} results`);
            
            // Test with actual query
            const searchResponse = await this.sendMessage({
                action: 'searchHistory',
                query: 'google',
                filters: {}
            });
            
            if (searchResponse && searchResponse.success) {
                this.pass(`Search query working - Found ${searchResponse.results.length} results for 'google'`);
            }
            
        } catch (error) {
            this.fail(`History access error: ${error.message}`);
        }
    }

    // Helper methods
    startTest(testName) {
        this.testCount++;
        console.log(`\n📋 Test ${this.testCount}: ${testName}`);
    }

    pass(message) {
        this.passCount++;
        console.log(`✅ PASS: ${message}`);
        this.results.push({ test: this.testCount, status: 'PASS', message });
    }

    fail(message) {
        this.failCount++;
        console.log(`❌ FAIL: ${message}`);
        this.results.push({ test: this.testCount, status: 'FAIL', message });
    }

    async sendMessage(message) {
        return new Promise((resolve) => {
            chrome.runtime.sendMessage(message, (response) => {
                resolve(response);
            });
        });
    }

    async getStorageData(keys = null) {
        return new Promise((resolve) => {
            chrome.storage.sync.get(keys, (result) => {
                resolve(result);
            });
        });
    }

    async setStorageData(data) {
        return new Promise((resolve) => {
            chrome.storage.sync.set(data, () => {
                resolve();
            });
        });
    }

    async removeStorageData(keys) {
        return new Promise((resolve) => {
            chrome.storage.sync.remove(keys, () => {
                resolve();
            });
        });
    }

    printResults() {
        console.log('\n' + '='.repeat(50));
        console.log('📊 TEST RESULTS SUMMARY');
        console.log('='.repeat(50));
        console.log(`Total Tests: ${this.testCount}`);
        console.log(`Passed: ${this.passCount} ✅`);
        console.log(`Failed: ${this.failCount} ❌`);
        console.log(`Success Rate: ${((this.passCount / this.testCount) * 100).toFixed(1)}%`);
        
        if (this.failCount > 0) {
            console.log('\n❌ FAILED TESTS:');
            this.results.filter(r => r.status === 'FAIL').forEach(result => {
                console.log(`  Test ${result.test}: ${result.message}`);
            });
        }
        
        if (this.passCount === this.testCount) {
            console.log('\n🎉 ALL TESTS PASSED! Extension is working correctly.');
        } else {
            console.log('\n⚠️  Some tests failed. Please check the issues above.');
        }
    }
}

// Run tests when page loads
document.addEventListener('DOMContentLoaded', () => {
    // Wait a bit for extension to initialize
    setTimeout(() => {
        const tester = new ExtensionTester();
        tester.runAllTests();
    }, 1000);
});

// Export for manual testing
window.ExtensionTester = ExtensionTester; 