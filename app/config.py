import os
from typing import List
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings"""
    
    # App Info
    APP_NAME: str = "Unified Document Extraction System"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Extract structured data from Bank Statements and Payslips automatically"
    
    # Server
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
    
    # OCR
    OCR_ENGINE: str = os.getenv("OCR_ENGINE", "paddleocr")
    OCR_LANGUAGE: str = os.getenv("OCR_LANGUAGE", "en")
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: List[str] = [".pdf"]
    
    # Directories
    UPLOAD_DIR: str = "uploads/raw"
    PROCESSED_DIR: str = "uploads/processed"
    OUTPUT_DIR: str = "output/json"


settings = Settings()
