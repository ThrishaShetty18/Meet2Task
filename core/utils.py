"""
Utility functions for Meet2Task AI
Includes logging, validation, and sentiment analysis
"""

import logging
import os
from datetime import datetime
from textblob import TextBlob
from typing import Optional

# Setup logging
def setup_logging():
    """Configure logging for the application"""
    log_dir = "data/logs"
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"app_{datetime.now().strftime('%Y%m%d')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

def validate_api_key(api_key: str) -> bool:
    """Validate API key format"""
    if not api_key or len(api_key) < 20:
        logger.warning("Invalid API key format")
        return False
    return True

def validate_transcript(text: str) -> bool:
    """Validate transcript text"""
    if not text or len(text.strip()) < 10:
        logger.warning("Transcript too short or empty")
        return False
    return True

def analyze_sentiment(text: str) -> dict:
    """
    Analyze sentiment of text using TextBlob
    Returns: dict with polarity, subjectivity, and label
    """
    try:
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        subjectivity = blob.sentiment.subjectivity
        
        if polarity > 0.2:
            label = "Positive"
        elif polarity < -0.2:
            label = "Negative"
        else:
            label = "Neutral"
        
        logger.info(f"Sentiment analysis complete: {label}")
        return {
            "polarity": polarity,
            "subjectivity": subjectivity,
            "label": label
        }
    except Exception as e:
        logger.error(f"Sentiment analysis failed: {e}")
        return {"polarity": 0, "subjectivity": 0, "label": "Neutral"}

def format_timestamp() -> str:
    """Return formatted timestamp"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file operations"""
    return "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_')).strip()

