import os
import logging
import torch
import yfinance as yf
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# Load environment variables
load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================

class Settings:
    # API Settings
    API_TITLE: str = "FinSight API"
    API_VERSION: str = "2.0.0"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    
    # Flask Settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    
    # CORS
    CORS_ORIGINS: str = "*"
    
    # Groq API Settings
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = "llama3-70b-8192"
    
    # Model Settings
    FINBERT_MODEL: str = "yiyanghkust/finbert-tone"
    MAX_TEXT_LENGTH: int = 512

settings = Settings()

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# GROQ CLIENT
# ============================================================================

class GroqClient:
    def __init__(self):
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL
    
    def summarize_article(self, text: str) -> str:
        """Use Llama3 to generate a concise summary of the article"""
        try:
            prompt = f"""You are a financial news analyst. Summarize the following financial news article in 2-3 sentences, focusing on key financial events, company performance, and market implications.

Article:
{text[:4000]}

Summary:"""

            response = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a financial analyst expert at summarizing financial news concisely."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=self.model,
                temperature=0.3,
                max_tokens=200
            )
            
            summary = response.choices[0].message.content.strip()
            logger.info(f"Article summarized: {len(summary)} chars")
            return summary
            
        except Exception as e:
            logger.error(f"Error summarizing article: {e}")
            return "Summary unavailable"
    
    def extract_companies(self, text: str) -> list:
        """Use Llama3 to extract publicly traded companies mentioned in the article"""
        try:
            prompt = f"""You are a financial analyst. Extract ALL publicly traded companies mentioned in this article.

Instructions:
- List ONLY the company names (e.g., "Apple", "Tesla", "Microsoft")
- Include companies that are directly mentioned or clearly implied
- Return as a comma-separated list
- If no companies found, return "None"

Article:
{text[:4000]}

Companies (comma-separated):"""

            response = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a financial data extraction expert. Extract company names accurately."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=self.model,
                temperature=0.1,
                max_tokens=100
            )
            
            companies_text = response.choices[0].message.content.strip()
            
            if companies_text.lower() == "none" or not companies_text:
                return []
            
            companies = [c.strip() for c in companies_text.split(',')]
            companies = [c for c in companies if c and len(c) > 1]
            
            logger.info(f"Extracted companies: {companies}")
            return companies
            
        except Exception as e:
            logger.error(f"Error extracting companies: {e}")
            return []
    
    def get_ticker_for_company(self, company_name: str) -> str:
        """Use Llama3 to get stock ticker for a company name"""
        try:
            prompt = f"""What is the stock ticker symbol for {company_name}?

Instructions:
- Return ONLY the ticker symbol (e.g., AAPL, TSLA, MSFT)
- If the company has multiple classes of stock, return the most common one
- If you're not sure, return "UNKNOWN"
- Return ONLY the ticker, nothing else

Ticker:"""

            response = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a financial data expert. Provide accurate stock ticker symbols."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=self.model,
                temperature=0.1,
                max_tokens=10
            )
            
            ticker = response.choices[0].message.content.strip().upper()
            ticker = ticker.split()[0] if ticker else "UNKNOWN"
            
            logger.info(f"Ticker for {company_name}: {ticker}")
            return ticker
            
        except Exception as e:
            logger.error(f"Error getting ticker for {company_name}: {e}")
            return "UNKNOWN"

# ============================================================================
# FINBERT NLP
# ============================================================================

class FinancialNLP:
    def __init__(self):
        self.tokenizer = None
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load FinBERT model"""
        try:
            logger.info(f"Loading FinBERT model: {settings.FINBERT_MODEL}")
            self.tokenizer = AutoTokenizer.from_pretrained(settings.FINBERT_MODEL)
            self.model = AutoModelForSequenceClassification.from_pretrained(settings.FINBERT_MODEL)
            logger.info("FinBERT model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def analyze_sentiment_for_company(self, text: str, company_name: str) -> Tuple[str, float, Dict[str, float]]:
        """Analyze sentiment for a specific company in the text"""
        sentences = text.split('.')
        relevant_sentences = [
            s for s in sentences 
            if company_name.lower() in s.lower()
        ]
        
        if not relevant_sentences:
            relevant_text = text[:settings.MAX_TEXT_LENGTH * 2]
        else:
            relevant_text = '. '.join(relevant_sentences[:5])
        
        return self.analyze_sentiment(relevant_text)
    
    def analyze_sentiment(self, text: str) -> Tuple[str, float, Dict[str, float]]:
        """Analyze sentiment using FinBERT"""
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=settings.MAX_TEXT_LENGTH,
            padding=True
        )
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
        
        sentiment_scores = {
            "negative": predictions[0][0].item(),
            "neutral": predictions[0][1].item(),
            "positive": predictions[0][2].item()
        }
        
        dominant_sentiment = max(sentiment_scores, key=sentiment_scores.get)
        confidence = sentiment_scores[dominant_sentiment]
        
        logger.info(f"Sentiment: {dominant_sentiment} ({confidence:.2%})")
        return dominant_sentiment, confidence, sentiment_scores

# ============================================================================
# STOCK DATA FETCHER
# ============================================================================

class StockDataFetcher:
    @staticmethod
    def get_stock_data(ticker: str) -> Dict:
        """Fetch real-time stock data from YFinance"""
        try:
            logger.info(f"Fetching stock data for {ticker}")
            stock = yf.Ticker(ticker)
            hist = stock.history(period="5d")
            
            if hist.empty or len(hist) < 2:
                logger.warning(f"Insufficient historical data for {ticker}")
                return {
                    "ticker": ticker,
                    "price": 0.0,
                    "change_pct": 0.0,
                    "volume": 0,
                    "market_cap": 0,
                    "day_high": 0.0,
                    "day_low": 0.0,
                    "status": "No data available"
                }
            
            current_price = float(hist['Close'].iloc[-1])
            prev_price = float(hist['Close'].iloc[-2])
            change_pct = ((current_price - prev_price) / prev_price) * 100
            
            try:
                info = stock.info
                market_cap = info.get('marketCap', 0)
                day_high = float(hist['High'].iloc[-1])
                day_low = float(hist['Low'].iloc[-1])
                volume = int(hist['Volume'].iloc[-1])
            except:
                market_cap = 0
                day_high = current_price
                day_low = current_price
                volume = int(hist['Volume'].iloc[-1]) if 'Volume' in hist else 0
            
            return {
                "ticker": ticker,
                "price": round(current_price, 2),
                "change_pct": round(change_pct, 2),
                "volume": volume,
                "market_cap": market_cap,
                "day_high": round(day_high, 2),
                "day_low": round(day_low, 2),
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error fetching stock data for {ticker}: {e}")
            return {
                "ticker": ticker,
                "price": 0.0,
                "change_pct": 0.0,
                "volume": 0,
                "market_cap": 0,
                "day_high": 0.0,
                "day_low": 0.0,
                "status": f"Error: {str(e)}"
            }
    
    @staticmethod
    def format_market_cap(market_cap: int) -> str:
        """Format market cap in human-readable format"""
        if market_cap >= 1_000_000_000_000:
            return f"${market_cap / 1_000_000_000_000:.2f}T"
        elif market_cap >= 1_000_000_000:
            return f"${market_cap / 1_000_000_000:.2f}B"
        elif market_cap >= 1_000_000:
            return f"${market_cap / 1_000_000:.2f}M"
        else:
            return f"${market_cap:,.0f}"

# ============================================================================
# ANALYSIS FUNCTIONS
# ============================================================================

def predict_impact(sentiment: str, score: float, change_pct: float) -> str:
    """Predict short-term market impact based on sentiment and price action"""
    if sentiment == "positive" and score > 0.7:
        if change_pct > 2:
            return "Strong bullish momentum - High confidence positive outlook"
        return "Likely short-term positive momentum"
    elif sentiment == "negative" and score > 0.7:
        if change_pct < -2:
            return "Strong bearish pressure - High confidence negative outlook"
        return "Potential short-term downward pressure"
    elif sentiment == "positive" and score > 0.5:
        return "Moderate positive sentiment - Watch for upside"
    elif sentiment == "negative" and score > 0.5:
        return "Moderate negative sentiment - Caution advised"
    else:
        return "Neutral outlook - Limited immediate impact expected"

def analyze_article(text: str, groq_client: GroqClient, finbert: FinancialNLP, 
                   stock_fetcher: StockDataFetcher) -> Dict:
    """Main analysis pipeline"""
    logger.info(f"Starting analysis pipeline for text (length: {len(text)} chars)")
    
    try:
        # Step 1: Summarize
        logger.info("Step 1: Summarizing article...")
        summary = groq_client.summarize_article(text)
        
        # Step 2: Extract companies
        logger.info("Step 2: Extracting companies...")
        companies = groq_client.extract_companies(text)
        
        if not companies:
            logger.info("No companies found in article")
            return {
                "summary": summary,
                "companies": [],
                "total_companies": 0
            }
        
        logger.info(f"Found {len(companies)} companies: {companies}")
        
        # Step 3-6: Process each company
        results = []
        
        for company_name in companies:
            logger.info(f"Processing company: {company_name}")
            
            ticker = groq_client.get_ticker_for_company(company_name)
            
            if ticker == "UNKNOWN":
                logger.warning(f"Could not find ticker for {company_name}")
                continue
            
            sentiment, confidence, sentiment_scores = finbert.analyze_sentiment_for_company(
                text, company_name
            )
            
            stock_data = stock_fetcher.get_stock_data(ticker)
            impact = predict_impact(sentiment, confidence, stock_data["change_pct"])
            
            company_result = {
                "name": company_name,
                "ticker": stock_data["ticker"],
                "sentiment": sentiment,
                "confidence": round(confidence, 3),
                "sentiment_scores": {
                    k: round(v, 3) for k, v in sentiment_scores.items()
                },
                "stock_data": {
                    "price": stock_data["price"],
                    "change_pct": stock_data["change_pct"],
                    "volume": stock_data["volume"],
                    "market_cap": stock_data["market_cap"],
                    "market_cap_formatted": stock_fetcher.format_market_cap(stock_data["market_cap"]),
                    "day_high": stock_data["day_high"],
                    "day_low": stock_data["day_low"]
                },
                "predicted_impact": impact,
                "data_status": stock_data["status"]
            }
            
            results.append(company_result)
        
        logger.info(f"Analysis complete: {len(results)} companies processed")
        
        return {
            "summary": summary,
            "companies": results,
            "total_companies": len(results)
        }
        
    except Exception as e:
        logger.error(f"Error in analysis pipeline: {e}", exc_info=True)
        raise

# ============================================================================
# INITIALIZE SERVICES
# ============================================================================

# Validate Groq API Key
if not settings.GROQ_API_KEY:
    logger.warning("WARNING: GROQ_API_KEY not set in .env file")
    groq_client = None
else:
    try:
        groq_client = GroqClient()
    except Exception as e:
        logger.error(f"Failed to initialize Groq client: {e}")
        groq_client = None

# Initialize FinBERT
try:
    finbert = FinancialNLP()
except Exception as e:
    logger.error(f"Failed to initialize FinBERT: {e}")
    finbert = None

# Initialize Stock Fetcher
stock_fetcher = StockDataFetcher()

# ============================================================================
# FLASK APP
# ============================================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = settings.SECRET_KEY
app.config['DEBUG'] = settings.DEBUG

# Enable CORS
CORS(app, resources={
    r"/*": {
        "origins": settings.CORS_ORIGINS,
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# ============================================================================
# ROUTES
# ============================================================================

@app.route('/', methods=['GET'])
def index():
    """Health check endpoint"""
    return jsonify({
        "message": "FinSight API v2.0 - Now powered by Groq + FinBERT",
        "version": settings.API_VERSION,
        "status": "healthy",
        "features": {
            "summarization": "Groq (Llama3)",
            "company_extraction": "Groq (Llama3)",
            "sentiment_analysis": "FinBERT",
            "stock_data": "YFinance"
        }
    })

@app.route('/health', methods=['GET'])
def health():
    """Detailed health check"""
    groq_status = "configured" if settings.GROQ_API_KEY else "missing"
    
    return jsonify({
        "status": "healthy",
        "api_version": settings.API_VERSION,
        "groq_api": groq_status,
        "finbert_model": settings.FINBERT_MODEL
    })

@app.route('/analyze', methods=['POST', 'OPTIONS'])
def analyze():
    """Analyze financial news article with enhanced AI pipeline"""
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "error": "No JSON data provided"
            }), 400
        
        text = data.get('text', '')
        
        if not text or len(text) < 100:
            return jsonify({
                "error": "Text must be at least 100 characters long for meaningful analysis"
            }), 400
        
        if not groq_client:
            return jsonify({
                "error": "GROQ_API_KEY not configured. Please add it to .env file"
            }), 500
        
        if not finbert:
            return jsonify({
                "error": "FinBERT model not loaded. Check server logs."
            }), 500
        
        result = analyze_article(text, groq_client, finbert, stock_fetcher)
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error during analysis: {e}", exc_info=True)
        return jsonify({
            "error": str(e),
            "message": "Analysis failed. Check server logs for details."
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Endpoint not found"
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": "Internal server error"
    }), 500

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    # Validate Groq API key on startup
    if not settings.GROQ_API_KEY:
        logger.error("=" * 60)
        logger.error("ERROR: GROQ_API_KEY not found!")
        logger.error("Please create .env file with:")
        logger.error("GROQ_API_KEY=your_actual_api_key_here")
        logger.error("Get your key from: https://console.groq.com/")
        logger.error("=" * 60)
    
    app.run(
        host=settings.API_HOST,
        port=settings.API_PORT,
        debug=settings.DEBUG
    )