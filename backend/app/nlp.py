import torch
import logging
from typing import Dict, Tuple
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from app.config import settings

logger = logging.getLogger(__name__)

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
        """
        Analyze sentiment for a specific company in the text
        Focuses on sentences mentioning the company
        """
        # Extract sentences mentioning the company
        sentences = text.split('.')
        relevant_sentences = [
            s for s in sentences 
            if company_name.lower() in s.lower()
        ]
        
        # If no specific mentions, use full text
        if not relevant_sentences:
            relevant_text = text[:settings.MAX_TEXT_LENGTH * 2]
        else:
            relevant_text = '. '.join(relevant_sentences[:5])  # Max 5 sentences
        
        return self.analyze_sentiment(relevant_text)
    
    def analyze_sentiment(self, text: str) -> Tuple[str, float, Dict[str, float]]:
        """
        Analyze sentiment using FinBERT
        Returns: (sentiment_label, confidence_score, all_scores)
        """
        # Tokenize
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=settings.MAX_TEXT_LENGTH,
            padding=True
        )
        
        # Get predictions
        with torch.no_grad():
            outputs = self.model(**inputs)
            predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
        
        # FinBERT labels: [negative, neutral, positive]
        sentiment_scores = {
            "negative": predictions[0][0].item(),
            "neutral": predictions[0][1].item(),
            "positive": predictions[0][2].item()
        }
        
        # Get dominant sentiment
        dominant_sentiment = max(sentiment_scores, key=sentiment_scores.get)
        confidence = sentiment_scores[dominant_sentiment]
        
        logger.info(f"Sentiment: {dominant_sentiment} ({confidence:.2%})")
        return dominant_sentiment, confidence, sentiment_scores

# Singleton instance
finbert = FinancialNLP()