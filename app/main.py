import os
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ['PADDLE_DEVICE'] = 'cpu'
os.environ['PADDLE_DISABLE_ONEDNN'] = '1'
os.environ['PADDLE_DISABLE_FAST_MATH'] = '1'
os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'

try:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
except:
    pass

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.api.routes import router
from app.config import settings
from utils.logger import setup_logger

load_dotenv()

logger = setup_logger(__name__, settings.LOG_FILE)
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Server: {settings.HOST}:{settings.PORT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"OCR Engine: {settings.OCR_ENGINE}")
    
    for directory in [settings.UPLOAD_DIR, settings.PROCESSED_DIR, settings.OUTPUT_DIR]:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    logger.info("All directories created successfully")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"Shutting down {settings.APP_NAME}")


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "description": "Unified document extraction API - automatically detects and extracts bank statements and payslips",
        "endpoints": {
            "upload": "/api/upload",
            "status": "/api/status/{upload_id}",
            "result": "/api/result/{upload_id}",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "service": "unified-document-extractor"
    }


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting {settings.APP_NAME} on {settings.HOST}:{settings.PORT}")
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
