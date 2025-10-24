import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from app.config import settings
from app.routes import analyze_article

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app
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

# Routes
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
    """
    Analyze financial news article with enhanced AI pipeline
    
    Pipeline:
    1. Groq (Llama3) - Summarize article
    2. Groq (Llama3) - Extract companies
    3. Groq (Llama3) - Get stock tickers
    4. FinBERT - Sentiment analysis per company
    5. YFinance - Real-time stock data
    6. Aggregate - Combine all insights
    
    Expected JSON body:
    {
        "text": "Article text here..."
    }
    
    Returns:
    {
        "summary": "AI-generated summary...",
        "companies": [
            {
                "name": "Apple",
                "ticker": "AAPL",
                "sentiment": "positive",
                "confidence": 0.92,
                "sentiment_scores": {...},
                "stock_data": {
                    "price": 182.45,
                    "change_pct": 1.34,
                    "volume": 50000000,
                    "market_cap": 2800000000000,
                    "market_cap_formatted": "$2.80T",
                    "day_high": 183.50,
                    "day_low": 181.20
                },
                "predicted_impact": "...",
                "data_status": "success"
            }
        ],
        "total_companies": 1
    }
    """
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        # Get JSON data
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
        
        # Check Groq API key
        if not settings.GROQ_API_KEY:
            return jsonify({
                "error": "GROQ_API_KEY not configured. Please add it to .env file"
            }), 500
        
        # Analyze article
        result = analyze_article(text)
        
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

if __name__ == '__main__':
    # Validate Groq API key on startup
    if not settings.GROQ_API_KEY:
        logger.error("=" * 60)
        logger.error("ERROR: GROQ_API_KEY not found!")
        logger.error("Please create backend/.env file with:")
        logger.error("GROQ_API_KEY=your_actual_api_key_here")
        logger.error("Get your key from: https://console.groq.com/")
        logger.error("=" * 60)
    
    app.run(
        host=settings.API_HOST,
        port=settings.API_PORT,
        debug=settings.DEBUG
    )