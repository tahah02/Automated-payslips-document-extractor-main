import os
from typing import List
from dotenv import load_dotenv
from utils.config_loader import ConfigLoader

load_dotenv()


class Settings:
    """Application settings - loads from config files"""
    
    # App Info
    APP_NAME: str = "Unified Document Extraction System"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Extract structured data from Bank Statements and Payslips automatically"
    
    # Load OCR config from ocr_config.json
    _ocr_config = ConfigLoader.load_config("ocr_config")
    
    # Server (can be overridden by .env)
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8080",
        "*"
    ]
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = "output/logs/app.log"
    
    # OCR - Always load from ocr_config.json (ignore .env)
    OCR_ENGINE: str = _ocr_config.get("engine", "paddleocr")
    OCR_LANGUAGE: str = _ocr_config.get("language", "en")
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: List[str] = [".pdf"]
    
    # Directories
    UPLOAD_DIR: str = "uploads/raw"
    PROCESSED_DIR: str = "uploads/processed"
    OUTPUT_DIR: str = "output/json"


settings = Settings()
