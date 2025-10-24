import yfinance as yf
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class StockDataFetcher:
    @staticmethod
    def get_stock_data(ticker: str) -> Dict:
        """
        Fetch real-time stock data from YFinance
        Returns comprehensive market data
        """
        try:
            logger.info(f"Fetching stock data for {ticker}")
            stock = yf.Ticker(ticker)
            
            # Get historical data
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
            
            # Calculate metrics
            current_price = float(hist['Close'].iloc[-1])
            prev_price = float(hist['Close'].iloc[-2])
            change_pct = ((current_price - prev_price) / prev_price) * 100
            
            # Get additional info
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

# Singleton instance
stock_fetcher = StockDataFetcher()