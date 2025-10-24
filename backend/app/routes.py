import logging
from typing import Dict, List
from app.groq_client import groq_client
from app.nlp import finbert
from app.stock_data import stock_fetcher

logger = logging.getLogger(__name__)

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

def analyze_article(text: str) -> Dict:
    """
    Main analysis pipeline:
    1. Summarize article with Groq (Llama3)
    2. Extract companies with Groq (Llama3)
    3. Get tickers with Groq (Llama3)
    4. Analyze sentiment per company with FinBERT
    5. Fetch real-time stock data with YFinance
    6. Aggregate all results
    """
    logger.info(f"Starting analysis pipeline for text (length: {len(text)} chars)")
    
    try:
        # Step 1: Summarize article with Llama3
        logger.info("Step 1: Summarizing article...")
        summary = groq_client.summarize_article(text)
        
        # Step 2: Extract companies with Llama3
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
            
            # Step 3: Get ticker with Llama3
            ticker = groq_client.get_ticker_for_company(company_name)
            
            if ticker == "UNKNOWN":
                logger.warning(f"Could not find ticker for {company_name}")
                continue
            
            # Step 4: Analyze sentiment with FinBERT (company-specific)
            sentiment, confidence, sentiment_scores = finbert.analyze_sentiment_for_company(
                text, 
                company_name
            )
            
            # Step 5: Fetch real-time stock data with YFinance
            stock_data = stock_fetcher.get_stock_data(ticker)
            
            # Step 6: Predict impact
            impact = predict_impact(sentiment, confidence, stock_data["change_pct"])
            
            # Aggregate result
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