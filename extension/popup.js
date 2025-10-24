// Configuration
const API_URL = 'http://localhost:8000/analyze';

// DOM Elements
const analyzeButton = document.getElementById('analyzeButton');
const retryButton = document.getElementById('retryButton');
const instructionsSection = document.getElementById('instructionsSection');
const loadingSpinner = document.getElementById('loadingSpinner');
const errorMessage = document.getElementById('errorMessage');
const errorText = document.getElementById('errorText');
const resultsSection = document.getElementById('resultsSection');
const summaryContent = document.getElementById('summaryContent');
const companiesSection = document.getElementById('companiesSection');

// Initialize popup
document.addEventListener('DOMContentLoaded', () => {
    // Check if we have cached results
    chrome.storage.local.get(['lastAnalysis', 'lastUrl'], (result) => {
        if (result.lastAnalysis && result.lastUrl) {
            // Check if we're still on the same page
            chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
                if (tabs[0] && tabs[0].url === result.lastUrl) {
                    displayResults(result.lastAnalysis);
                }
            });
        }
    });
    
    // Set up event listeners
    analyzeButton.addEventListener('click', analyzeCurrentPage);
    retryButton.addEventListener('click', analyzeCurrentPage);
});

// Main analysis function
async function analyzeCurrentPage() {
    try {
        // Hide all sections
        hideAllSections();
        showLoading();
        
        // Get current tab
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        
        if (!tab) {
            throw new Error('No active tab found');
        }
        
        // Extract article text from the page
        const results = await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            func: extractArticleText
        });
        
        if (!results || !results[0] || !results[0].result) {
            throw new Error('Could not extract text from page');
        }
        
        const articleText = results[0].result;
        
        if (!articleText || articleText.length < 100) {
            throw new Error('Article text too short. Please navigate to a full article page.');
        }
        
        // Send to API for analysis
        const analysis = await analyzeWithAPI(articleText);
        
        // Cache the results
        chrome.storage.local.set({
            lastAnalysis: analysis,
            lastUrl: tab.url,
            lastAnalyzed: new Date().toISOString()
        });
        
        // Display results
        displayResults(analysis);
        
    } catch (error) {
        console.error('Analysis error:', error);
        showError(error.message);
    }
}

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
        'main',
        '.content'
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
                    .filter(t => t.length > 50) // Filter out short paragraphs
                    .join(' ');
                
                if (text.length > 100) {
                    break;
                }
            }
        }
    }
    
    // Fallback: get all paragraphs on the page
    if (!text || text.length < 100) {
        const allParagraphs = document.querySelectorAll('p');
        text = Array.from(allParagraphs)
            .map(p => p.textContent.trim())
            .filter(t => t.length > 50)
            .slice(0, 20) // Limit to first 20 paragraphs
            .join(' ');
    }
    
    return text.trim();
}

// Call the Flask API
async function analyzeWithAPI(text) {
    const response = await fetch(API_URL, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ text })
    });
    
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `API Error: ${response.status}`);
    }
    
    return await response.json();
}

// Display analysis results
function displayResults(data) {
    hideAllSections();
    
    // Show results section
    resultsSection.style.display = 'block';
    
    // Display summary
    summaryContent.innerHTML = `<p>${data.summary || 'No summary available'}</p>`;
    
    // Display companies
    if (data.companies && data.companies.length > 0) {
        companiesSection.innerHTML = data.companies.map(company => createCompanyCard(company)).join('');
    } else {
        companiesSection.innerHTML = '<p style="text-align: center; color: #666; padding: 20px;">No companies found in this article.</p>';
    }
}

// Create HTML for a company card
function createCompanyCard(company) {
    const sentimentClass = `sentiment-${company.sentiment}`;
    const changeClass = company.stock_data.change_pct >= 0 ? 'positive' : 'negative';
    const changeSymbol = company.stock_data.change_pct >= 0 ? '+' : '';
    
    return `
        <div class="company-card">
            <div class="company-header">
                <div class="company-name">${company.name}</div>
                <div class="company-ticker">${company.ticker}</div>
            </div>
            
            <div class="sentiment-badge ${sentimentClass}">
                ${capitalizeFirst(company.sentiment)} Sentiment
            </div>
            
            <div class="confidence-meter">
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <span class="stock-label">Confidence</span>
                    <span style="font-weight: 600;">${(company.confidence * 100).toFixed(1)}%</span>
                </div>
                <div class="confidence-bar">
                    <div class="confidence-fill" style="width: ${company.confidence * 100}%"></div>
                </div>
            </div>
            
            <div class="sentiment-scores">
                <div class="score-item">
                    <div class="score-label">Positive</div>
                    <div class="score-value" style="color: #27ae60;">${(company.sentiment_scores.positive * 100).toFixed(0)}%</div>
                </div>
                <div class="score-item">
                    <div class="score-label">Neutral</div>
                    <div class="score-value" style="color: #3498db;">${(company.sentiment_scores.neutral * 100).toFixed(0)}%</div>
                </div>
                <div class="score-item">
                    <div class="score-label">Negative</div>
                    <div class="score-value" style="color: #e74c3c;">${(company.sentiment_scores.negative * 100).toFixed(0)}%</div>
                </div>
            </div>
            
            <div class="stock-data-grid">
                <div class="stock-data-item">
                    <div class="stock-label">Current Price</div>
                    <div class="stock-value">$${company.stock_data.price.toFixed(2)}</div>
                </div>
                <div class="stock-data-item">
                    <div class="stock-label">Change</div>
                    <div class="stock-value ${changeClass}">${changeSymbol}${company.stock_data.change_pct.toFixed(2)}%</div>
                </div>
                <div class="stock-data-item">
                    <div class="stock-label">Market Cap</div>
                    <div class="stock-value">${company.stock_data.market_cap_formatted || 'N/A'}</div>
                </div>
                <div class="stock-data-item">
                    <div class="stock-label">Volume</div>
                    <div class="stock-value">${formatVolume(company.stock_data.volume)}</div>
                </div>
                <div class="stock-data-item">
                    <div class="stock-label">Day High</div>
                    <div class="stock-value">$${company.stock_data.day_high.toFixed(2)}</div>
                </div>
                <div class="stock-data-item">
                    <div class="stock-label">Day Low</div>
                    <div class="stock-value">$${company.stock_data.day_low.toFixed(2)}</div>
                </div>
            </div>
            
            <div class="impact-prediction">
                <strong>Predicted Impact:</strong> ${company.predicted_impact}
            </div>
        </div>
    `;
}

// Utility Functions
function hideAllSections() {
    instructionsSection.style.display = 'none';
    loadingSpinner.style.display = 'none';
    errorMessage.style.display = 'none';
    resultsSection.style.display = 'none';
}

function showLoading() {
    loadingSpinner.style.display = 'block';
}

function showError(message) {
    hideAllSections();
    errorMessage.style.display = 'block';
    errorText.textContent = message;
}

function capitalizeFirst(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function formatVolume(volume) {
    if (volume >= 1000000000) {
        return (volume / 1000000000).toFixed(2) + 'B';
    } else if (volume >= 1000000) {
        return (volume / 1000000).toFixed(2) + 'M';
    } else if (volume >= 1000) {
        return (volume / 1000).toFixed(2) + 'K';
    }
    return volume.toString();
}