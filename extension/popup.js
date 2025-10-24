const API_URL = 'http://localhost:8000/analyze';

const analyzeBtn = document.getElementById('analyzeBtn');
const statusDiv = document.getElementById('status');
const resultsDiv = document.getElementById('results');
const summarySection = document.getElementById('summarySection');
const summaryText = document.getElementById('summaryText');

analyzeBtn.addEventListener('click', async () => {
    await analyzeArticle();
});

async function analyzeArticle() {
    try {
        setButtonLoading(true);
        showStatus('Extracting article text...', 'info');
        resultsDiv.innerHTML = '';
        summarySection.style.display = 'none';

        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

        const results = await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            function: extractArticleText,
        });

        const articleText = results[0].result;

        if (!articleText || articleText.trim().length < 100) {
            showStatus('❌ Could not extract sufficient text. Please navigate to a financial news article.', 'error');
            setButtonLoading(false);
            return;
        }

        showStatus('🤖 AI analyzing with Groq + FinBERT...', 'info');

        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text: articleText }),
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `API Error: ${response.status}`);
        }

        const data = await response.json();

        // Display summary
        if (data.summary) {
            summaryText.textContent = data.summary;
            summarySection.style.display = 'block';
        }

        // Display companies
        if (data.companies && data.companies.length > 0) {
            showStatus(`✅ Found ${data.companies.length} company mention${data.companies.length > 1 ? 's' : ''}`, 'success');
            displayResults(data.companies);
        } else {
            showStatus('No companies detected. Try a different financial news page.', 'info');
            displayEmptyState();
        }

    } catch (error) {
        console.error('Error:', error);
        if (error.message.includes('GROQ_API_KEY')) {
            showStatus('❌ Groq API key not configured. Check backend .env file.', 'error');
        } else if (error.message.includes('fetch')) {
            showStatus('❌ Cannot connect to backend. Make sure the server is running on port 8000.', 'error');
        } else {
            showStatus(`❌ Error: ${error.message}`, 'error');
        }
    } finally {
        setButtonLoading(false);
    }
}

function extractArticleText() {
    const selectors = [
        'article',
        'main',
        '[role="main"]',
        '.article-content',
        '.post-content',
        '.entry-content',
        '.content',
    ];

    for (const selector of selectors) {
        const element = document.querySelector(selector);
        if (element && element.innerText.trim().length > 100) {
            return element.innerText.trim();
        }
    }

    return document.body.innerText.trim();
}

function displayResults(companies) {
    resultsDiv.innerHTML = '';

    companies.forEach(company => {
        const card = createCompanyCard(company);
        resultsDiv.appendChild(card);
    });
}

function createCompanyCard(company) {
    const card = document.createElement('div');
    card.className = 'company-card';

    const sentimentClass = getSentimentClass(company.sentiment);
    const sentimentEmoji = getSentimentEmoji(company.sentiment);
    const priceChangeClass = company.stock_data.change_pct >= 0 ? 'positive' : 'negative';
    const priceChangeSymbol = company.stock_data.change_pct >= 0 ? '↑' : '↓';

    card.innerHTML = `
        <div class="company-header">
            <div class="company-info">
                <h3 class="company-name">${company.name}</h3>
                <span class="company-ticker">${company.ticker}</span>
            </div>
            <div class="sentiment-badge ${sentimentClass}">
                ${sentimentEmoji} ${company.sentiment}
            </div>
        </div>

        <div class="stock-info">
            <div class="stock-price">
                <span class="price-label">Price:</span>
                <span class="price-value">$${company.stock_data.price}</span>
            </div>
            <div class="stock-change ${priceChangeClass}">
                ${priceChangeSymbol} ${Math.abs(company.stock_data.change_pct)}%
            </div>
        </div>

        <div class="stock-details">
            <div class="stock-detail-item">
                <span class="stock-detail-label">Volume</span>
                <span class="stock-detail-value">${formatNumber(company.stock_data.volume)}</span>
            </div>
            <div class="stock-detail-item">
                <span class="stock-detail-label">Market Cap</span>
                <span class="stock-detail-value">${company.stock_data.market_cap_formatted}</span>
            </div>
            <div class="stock-detail-item">
                <span class="stock-detail-label">Day High</span>
                <span class="stock-detail-value">$${company.stock_data.day_high}</span>
            </div>
            <div class="stock-detail-item">
                <span class="stock-detail-label">Day Low</span>
                <span class="stock-detail-value">$${company.stock_data.day_low}</span>
            </div>
        </div>

        <div class="sentiment-scores">
            <div class="score-bar">
                <span class="score-label">Positive</span>
                <div class="score-progress">
                    <div class="score-fill positive" style="width: ${company.sentiment_scores.positive * 100}%"></div>
                </div>
                <span class="score-value">${(company.sentiment_scores.positive * 100).toFixed(0)}%</span>
            </div>
            <div class="score-bar">
                <span class="score-label">Neutral</span>
                <div class="score-progress">
                    <div class="score-fill neutral" style="width: ${company.sentiment_scores.neutral * 100}%"></div>
                </div>
                <span class="score-value">${(company.sentiment_scores.neutral * 100).toFixed(0)}%</span>
            </div>
            <div class="score-bar">
                <span class="score-label">Negative</span>
                <div class="score-progress">
                    <div class="score-fill negative" style="width: ${company.sentiment_scores.negative * 100}%"></div>
                </div>
                <span class="score-value">${(company.sentiment_scores.negative * 100).toFixed(0)}%</span>
            </div>
        </div>

        <div class="impact-section">
            <span class="impact-label">📊 Predicted Impact:</span>
            <p class="impact-text">${company.predicted_impact}</p>
        </div>

        <div class="confidence-section">
            <span class="confidence-label">Confidence:</span>
            <span class="confidence-value">${(company.confidence * 100).toFixed(1)}%</span>
        </div>
    `;

    return card;
}

function getSentimentClass(sentiment) {
    const classes = {
        'positive': 'sentiment-positive',
        'negative': 'sentiment-negative',
        'neutral': 'sentiment-neutral'
    };
    return classes[sentiment] || 'sentiment-neutral';
}

function getSentimentEmoji(sentiment) {
    const emojis = {
        'positive': '📈',
        'negative': '📉',
        'neutral': '➖'
    };
    return emojis[sentiment] || '➖';
}

function formatNumber(num) {
    if (num >= 1_000_000_000) {
        return `${(num / 1_000_000_000).toFixed(2)}B`;
    } else if (num >= 1_000_000) {
        return `${(num / 1_000_000).toFixed(2)}M`;
    } else if (num >= 1_000) {
        return `${(num / 1_000).toFixed(2)}K`;
    }
    return num.toLocaleString();
}

function showStatus(message, type) {
    statusDiv.textContent = message;
    statusDiv.className = `status-message ${type}`;
    statusDiv.style.display = 'block';
}

function setButtonLoading(isLoading) {
    const btnText = analyzeBtn.querySelector('.btn-text');
    const loader = analyzeBtn.querySelector('.loader');

    if (isLoading) {
        btnText.style.display = 'none';
        loader.style.display = 'inline-block';
        analyzeBtn.disabled = true;
    } else {
        btnText.style.display = 'inline';
        loader.style.display = 'none';
        analyzeBtn.disabled = false;
    }
}

function displayEmptyState() {
    resultsDiv.innerHTML = `
        <div class="empty-state">
            <p>🔍 No publicly traded companies detected in this article.</p>
            <p class="empty-hint">Try analyzing articles from:</p>
            <ul class="empty-list">
                <li>Bloomberg</li>
                <li>CNBC</li>
                <li>Reuters Business</li>
                <li>Wall Street Journal</li>
                <li>Yahoo Finance</li>
            </ul>
        </div>
    `;
}