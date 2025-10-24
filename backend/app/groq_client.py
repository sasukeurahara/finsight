import logging
from groq import Groq
from app.config import settings

logger = logging.getLogger(__name__)

class GroqClient:
    def __init__(self):
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL
    
    def summarize_article(self, text: str) -> str:
        """
        Use Llama3 to generate a concise summary of the article
        """
        try:
            prompt = f"""You are a financial news analyst. Summarize the following financial news article in 2-3 sentences, focusing on key financial events, company performance, and market implications.

Article:
{text[:4000]}  # Limit to avoid token limits

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
        """
        Use Llama3 to extract publicly traded companies mentioned in the article
        """
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
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=100
            )
            
            companies_text = response.choices[0].message.content.strip()
            
            if companies_text.lower() == "none" or not companies_text:
                return []
            
            # Parse comma-separated list
            companies = [c.strip() for c in companies_text.split(',')]
            companies = [c for c in companies if c and len(c) > 1]
            
            logger.info(f"Extracted companies: {companies}")
            return companies
            
        except Exception as e:
            logger.error(f"Error extracting companies: {e}")
            return []
    
    def get_ticker_for_company(self, company_name: str) -> str:
        """
        Use Llama3 to get stock ticker for a company name
        """
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
            # Remove any extra text
            ticker = ticker.split()[0] if ticker else "UNKNOWN"
            
            logger.info(f"Ticker for {company_name}: {ticker}")
            return ticker
            
        except Exception as e:
            logger.error(f"Error getting ticker for {company_name}: {e}")
            return "UNKNOWN"

# Singleton instance
groq_client = GroqClient()