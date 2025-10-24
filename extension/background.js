// Background service worker for FinSight extension

console.log('FinSight background service worker loaded');

// Listen for extension installation
chrome.runtime.onInstalled.addListener((details) => {
    if (details.reason === 'install') {
        console.log('FinSight extension installed');
        
        // Set default settings
        chrome.storage.local.set({
            apiUrl: 'http://localhost:8000',
            enableNotifications: true,
            cacheResults: true
        });
        
        // Optionally open welcome page (comment out if you don't want this)
        // chrome.tabs.create({
        //     url: chrome.runtime.getURL('welcome.html')
        // });
    } else if (details.reason === 'update') {
        console.log('FinSight extension updated');
    }
});

// Listen for messages from content scripts or popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'openPopup') {
        // Open extension popup
        chrome.action.openPopup();
    } else if (request.action === 'analyze') {
        // Handle analysis request
        handleAnalysisRequest(request.text)
            .then(result => sendResponse({ success: true, data: result }))
            .catch(error => sendResponse({ success: false, error: error.message }));
        return true; // Keep message channel open for async response
    } else if (request.action === 'checkApiStatus') {
        // Check if API is running
        checkApiStatus()
            .then(status => sendResponse({ status }))
            .catch(() => sendResponse({ status: 'offline' }));
        return true;
    }
});

// Handle analysis request
async function handleAnalysisRequest(text) {
    const settings = await chrome.storage.local.get(['apiUrl']);
    const apiUrl = settings.apiUrl || 'http://localhost:8000';
    
    const response = await fetch(`${apiUrl}/analyze`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ text })
    });
    
    if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
    }
    
    return await response.json();
}

// Check if API is running
async function checkApiStatus() {
    try {
        const settings = await chrome.storage.local.get(['apiUrl']);
        const apiUrl = settings.apiUrl || 'http://localhost:8000';
        
        const response = await fetch(`${apiUrl}/health`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            return data.status || 'online';
        }
        return 'offline';
    } catch (error) {
        return 'offline';
    }
}

// Context menu for quick analysis
chrome.runtime.onInstalled.addListener(() => {
    chrome.contextMenus.create({
        id: 'analyzeWithFinSight',
        title: 'Analyze with FinSight',
        contexts: ['selection']
    });
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener((info, tab) => {
    if (info.menuItemId === 'analyzeWithFinSight' && info.selectionText) {
        // Send selected text for analysis
        chrome.storage.local.set({
            pendingAnalysis: info.selectionText
        }, () => {
            chrome.action.openPopup();
        });
    }
});

// Badge management
function updateBadge(text, color) {
    chrome.action.setBadgeText({ text });
    chrome.action.setBadgeBackgroundColor({ color });
}

// Listen for tab updates to detect financial news sites
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === 'complete' && tab.url) {
        const financialSites = [
            'bloomberg.com',
            'cnbc.com',
            'reuters.com',
            'wsj.com',
            'yahoo.com/finance',
            'marketwatch.com',
            'seekingalpha.com',
            'fool.com',
            'benzinga.com',
            'investing.com',
            'businessinsider.com',
            'forbes.com',
            'ft.com'
        ];
        
        const isFinancialSite = financialSites.some(site => tab.url.includes(site));
        
        if (isFinancialSite) {
            // Update badge to show extension is active
            updateBadge('', '#667eea');
        }
    }
});

// Periodic API health check (every 5 minutes)
setInterval(async () => {
    const status = await checkApiStatus();
    console.log(`FinSight API status: ${status}`);
}, 5 * 60 * 1000);