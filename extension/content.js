// Content script for FinSight extension
// This script runs on financial news pages to help extract article content

console.log('FinSight content script loaded');

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'extractText') {
        const text = extractArticleText();
        sendResponse({ text });
    }
    return true;
});

// Extract article text from the current page
function extractArticleText() {
    // Try multiple selectors for different news sites
    const selectors = [
        'article',
        '[role="article"]',
        '.article-body',
        '.article-content',
        '.story-body',
        '.post-content',
        '.entry-content',
        'main article',
        '.article',
        '[itemprop="articleBody"]'
    ];
    
    let text = '';
    
    // Try each selector
    for (const selector of selectors) {
        const element = document.querySelector(selector);
        if (element) {
            // Get all paragraphs
            const paragraphs = element.querySelectorAll('p');
            if (paragraphs.length > 0) {
                text = Array.from(paragraphs)
                    .map(p => p.textContent.trim())
                    .filter(t => t.length > 30) // Filter out very short paragraphs
                    .join(' ');
                
                if (text.length > 200) {
                    console.log(`FinSight: Found article text using selector: ${selector}`);
                    break;
                }
            }
        }
    }
    
    // Fallback: get all paragraphs on the page
    if (!text || text.length < 200) {
        console.log('FinSight: Using fallback paragraph extraction');
        const allParagraphs = document.querySelectorAll('p');
        text = Array.from(allParagraphs)
            .map(p => p.textContent.trim())
            .filter(t => t.length > 30)
            .slice(0, 30) // Limit to first 30 paragraphs
            .join(' ');
    }
    
    // Clean up the text
    text = text
        .replace(/\s+/g, ' ') // Replace multiple spaces with single space
        .replace(/\n+/g, ' ') // Replace newlines with space
        .trim();
    
    console.log(`FinSight: Extracted ${text.length} characters`);
    return text;
}

// Optional: Add visual indicator when extension is active
function addVisualIndicator() {
    // Check if indicator already exists
    if (document.getElementById('finsight-indicator')) {
        return;
    }
    
    const indicator = document.createElement('div');
    indicator.id = 'finsight-indicator';
    indicator.style.cssText = `
        position: fixed;
        top: 10px;
        right: 10px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 8px 15px;
        border-radius: 20px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 12px;
        font-weight: 600;
        z-index: 10000;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        cursor: pointer;
        transition: transform 0.2s;
    `;
    indicator.textContent = '📊 FinSight Active';
    
    indicator.addEventListener('mouseenter', () => {
        indicator.style.transform = 'scale(1.05)';
    });
    
    indicator.addEventListener('mouseleave', () => {
        indicator.style.transform = 'scale(1)';
    });
    
    indicator.addEventListener('click', () => {
        // Open extension popup when clicked
        chrome.runtime.sendMessage({ action: 'openPopup' });
    });
    
    document.body.appendChild(indicator);
    
    // Remove indicator after 3 seconds
    setTimeout(() => {
        indicator.style.opacity = '0';
        indicator.style.transition = 'opacity 0.5s';
        setTimeout(() => {
            if (indicator.parentNode) {
                indicator.parentNode.removeChild(indicator);
            }
        }, 500);
    }, 3000);
}

// Add indicator when page loads (only on financial news sites)
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        if (isFinancialNewsSite()) {
            addVisualIndicator();
        }
    });
} else {
    if (isFinancialNewsSite()) {
        addVisualIndicator();
    }
}

// Check if current site is a financial news site
function isFinancialNewsSite() {
    const hostname = window.location.hostname.toLowerCase();
    const financialSites = [
        'bloomberg.com',
        'cnbc.com',
        'reuters.com',
        'wsj.com',
        'yahoo.com',
        'marketwatch.com',
        'seekingalpha.com',
        'fool.com',
        'benzinga.com',
        'investing.com',
        'businessinsider.com',
        'forbes.com',
        'ft.com',
        'barrons.com',
        'morningstar.com'
    ];
    
    return financialSites.some(site => hostname.includes(site));
}