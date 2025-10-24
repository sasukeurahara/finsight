import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

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
    GROQ_MODEL: str = "llama3-70b-8192"  # or llama3-8b-8192 for faster responses
    
    # Model Settings
    FINBERT_MODEL: str = "yiyanghkust/finbert-tone"
    MAX_TEXT_LENGTH: int = 512
    
    # Paths
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    MODELS_DIR: str = os.path.join(os.path.dirname(BASE_DIR), "models")

settings = Settings()

# Validate Groq API Key
if not settings.GROQ_API_KEY:
    print("WARNING: GROQ_API_KEY not set in .env file")