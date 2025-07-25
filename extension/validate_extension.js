#!/usr/bin/env node
/**
 * HistoryHounder Extension Validator
 * Checks all files for common issues before testing
 */

const fs = require('fs');
const path = require('path');

class ExtensionValidator {
    constructor() {
        this.errors = [];
        this.warnings = [];
        this.extensionDir = __dirname;
    }

    async validate() {
        console.log('🔍 Validating HistoryHounder Extension...\n');

        await this.validateManifest();
        await this.validateFiles();
        await this.validateJavaScript();
        await this.validateIcons();
        await this.validateHTML();

        this.printResults();
    }

    async validateManifest() {
        console.log('📋 Validating manifest.json...');
        
        try {
            const manifestPath = path.join(this.extensionDir, 'manifest.json');
            const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));

            // Check required fields
            const required = ['manifest_version', 'name', 'version', 'description'];
            for (const field of required) {
                if (!manifest[field]) {
                    this.errors.push(`Manifest missing required field: ${field}`);
                }
            }

            // Check manifest version
            if (manifest.manifest_version !== 3) {
                this.errors.push('Manifest version must be 3');
            }

            // Check permissions
            const requiredPermissions = ['history', 'storage'];
            for (const permission of requiredPermissions) {
                if (!manifest.permissions.includes(permission)) {
                    this.errors.push(`Manifest missing required permission: ${permission}`);
                }
            }

            // Check background script
            if (!manifest.background || !manifest.background.service_worker) {
                this.errors.push('Manifest missing background service worker');
            }

            // Check popup
            if (!manifest.action || !manifest.action.default_popup) {
                this.errors.push('Manifest missing popup configuration');
            }

            // Check content scripts
            if (!manifest.content_scripts || manifest.content_scripts.length === 0) {
                this.warnings.push('No content scripts defined');
            }

            // Check icons
            if (!manifest.icons) {
                this.warnings.push('No icons defined');
            }

            console.log('✅ Manifest validation complete');

        } catch (error) {
            this.errors.push(`Manifest JSON error: ${error.message}`);
        }
    }

    async validateFiles() {
        console.log('📁 Validating file structure...');

        const requiredFiles = [
            'manifest.json',
            'background.js',
            'popup.html',
            'popup.js',
            'popup.css',
            'content.js',
            'settings.html',
            'settings.js'
        ];

        for (const file of requiredFiles) {
            const filePath = path.join(this.extensionDir, file);
            if (!fs.existsSync(filePath)) {
                this.errors.push(`Missing required file: ${file}`);
            } else {
                const stats = fs.statSync(filePath);
                if (stats.size === 0) {
                    this.warnings.push(`Empty file: ${file}`);
                }
            }
        }

        console.log('✅ File structure validation complete');
    }

    async validateJavaScript() {
        console.log('🔧 Validating JavaScript files...');

        const jsFiles = ['background.js', 'popup.js', 'content.js', 'settings.js'];

        for (const file of jsFiles) {
            const filePath = path.join(this.extensionDir, file);
            if (fs.existsSync(filePath)) {
                try {
                    const content = fs.readFileSync(filePath, 'utf8');
                    
                    // Check for basic syntax issues
                    if (content.includes('console.log') && !content.includes('console.error')) {
                        this.warnings.push(`${file}: Consider adding error logging`);
                    }

                    // Check for async/await usage
                    if (content.includes('async') && !content.includes('await')) {
                        this.warnings.push(`${file}: async function without await`);
                    }

                    // Check for error handling
                    if (content.includes('chrome.runtime.sendMessage') && !content.includes('catch')) {
                        this.warnings.push(`${file}: Consider adding error handling for message sending`);
                    }

                } catch (error) {
                    this.errors.push(`${file}: Read error - ${error.message}`);
                }
            }
        }

        console.log('✅ JavaScript validation complete');
    }

    async validateIcons() {
        console.log('🎨 Validating icons...');

        const iconDir = path.join(this.extensionDir, 'icons');
        if (!fs.existsSync(iconDir)) {
            this.errors.push('Icons directory missing');
            return;
        }

        const requiredIcons = ['icon16.png', 'icon48.png', 'icon128.png'];
        for (const icon of requiredIcons) {
            const iconPath = path.join(iconDir, icon);
            if (!fs.existsSync(iconPath)) {
                this.errors.push(`Missing icon: ${icon}`);
            } else {
                const stats = fs.statSync(iconPath);
                if (stats.size < 100) {
                    this.warnings.push(`Icon file very small: ${icon} (${stats.size} bytes)`);
                }
            }
        }

        console.log('✅ Icon validation complete');
    }

    async validateHTML() {
        console.log('🌐 Validating HTML files...');

        const htmlFiles = ['popup.html', 'settings.html', 'test_extension.html'];

        for (const file of htmlFiles) {
            const filePath = path.join(this.extensionDir, file);
            if (fs.existsSync(filePath)) {
                try {
                    const content = fs.readFileSync(filePath, 'utf8');
                    
                    // Check for basic HTML structure
                    if (!content.includes('<!DOCTYPE html>')) {
                        this.warnings.push(`${file}: Missing DOCTYPE declaration`);
                    }

                    if (!content.includes('<html')) {
                        this.warnings.push(`${file}: Missing html tag`);
                    }

                    if (!content.includes('<head>')) {
                        this.warnings.push(`${file}: Missing head tag`);
                    }

                    if (!content.includes('<body>')) {
                        this.warnings.push(`${file}: Missing body tag`);
                    }

                    // Check for script references
                    if (file === 'popup.html' && !content.includes('popup.js')) {
                        this.errors.push(`${file}: Missing popup.js script reference`);
                    }

                    if (file === 'settings.html' && !content.includes('settings.js')) {
                        this.errors.push(`${file}: Missing settings.js script reference`);
                    }

                } catch (error) {
                    this.errors.push(`${file}: Read error - ${error.message}`);
                }
            }
        }

        console.log('✅ HTML validation complete');
    }

    printResults() {
        console.log('\n' + '='.repeat(50));
        console.log('📊 VALIDATION RESULTS');
        console.log('='.repeat(50));

        if (this.errors.length === 0 && this.warnings.length === 0) {
            console.log('🎉 All validations passed! Extension should work correctly.');
        }

        if (this.errors.length > 0) {
            console.log(`\n❌ ERRORS (${this.errors.length}):`);
            this.errors.forEach(error => {
                console.log(`  • ${error}`);
            });
        }

        if (this.warnings.length > 0) {
            console.log(`\n⚠️  WARNINGS (${this.warnings.length}):`);
            this.warnings.forEach(warning => {
                console.log(`  • ${warning}`);
            });
        }

        if (this.errors.length > 0) {
            console.log('\n🚨 Extension has errors that need to be fixed before testing.');
            process.exit(1);
        } else if (this.warnings.length > 0) {
            console.log('\n⚠️  Extension has warnings but should still work.');
        } else {
            console.log('\n✅ Extension is ready for testing!');
        }
    }
}

// Run validation
const validator = new ExtensionValidator();
validator.validate().catch(console.error); 