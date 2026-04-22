import os
from typing import List
from dotenv import load_dotenv
from utils.config_loader import ConfigLoader

load_dotenv()


class Settings:
    
    APP_NAME: str = "Unified Document Extraction System"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Extract structured data from Bank Statements and Payslips automatically"
    
    _ocr_config = ConfigLoader.load_config("ocr_config")
    
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8080",
        "*"
    ]
    
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = "output/logs/app.log"
    
    OCR_ENGINE: str = _ocr_config.get("engine", "paddleocr")
    OCR_LANGUAGE: str = _ocr_config.get("language", "en")
    
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024
    ALLOWED_EXTENSIONS: List[str] = [".pdf"]
    
    UPLOAD_DIR: str = "uploads/raw"
    PROCESSED_DIR: str = "uploads/processed"
    OUTPUT_DIR: str = "output/json"


settings = Settings()
