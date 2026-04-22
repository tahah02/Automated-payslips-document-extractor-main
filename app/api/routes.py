import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from pathlib import Path
import uuid
import json

from app.api.schemas import UploadResponse, StatusResponse, ExtractionResult, ErrorResponse
from core.unified_pipeline import UnifiedExtractionPipeline
from utils.config_loader import ConfigLoader

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["unified-extractor"])

processing_status = {}

ocr_config = ConfigLoader.load_config("ocr_config")
ocr_engine = ocr_config.get("engine", "paddleocr")
ocr_language = ocr_config.get("language", "en")

logger.info(f"Initializing pipeline with OCR engine: {ocr_engine}, language: {ocr_language}")

pipeline = UnifiedExtractionPipeline(ocr_engine=ocr_engine, ocr_language=ocr_language)

UPLOAD_DIR = Path("uploads/raw")
PROCESSED_DIR = Path("uploads/processed")
OUTPUT_DIR = Path("output/json")

for directory in [UPLOAD_DIR, PROCESSED_DIR, OUTPUT_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    try:
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        upload_id = str(uuid.uuid4())
        
        file_path = UPLOAD_DIR / f"{upload_id}.pdf"
        content = await file.read()
        with open(file_path, 'wb') as f:
            f.write(content)
        
        logger.info(f"File uploaded: {file.filename} with ID: {upload_id}")
        
        processing_status[upload_id] = {
            "status": "processing",
            "upload_id": upload_id,
            "message": "Analyzing document and detecting type...",
            "document_type": None,
            "classification_confidence": None
        }
        
        if background_tasks:
            background_tasks.add_task(process_document, upload_id, str(file_path))
        
        return UploadResponse(
            status="processing",
            upload_id=upload_id,
            message="File uploaded successfully. Auto-detecting document type and processing..."
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{upload_id}", response_model=StatusResponse)
async def get_status(upload_id: str):
    if upload_id not in processing_status:
        raise HTTPException(status_code=404, detail="Upload ID not found")
    
    return StatusResponse(**processing_status[upload_id])


@router.get("/result/{upload_id}", response_model=ExtractionResult)
async def get_result(upload_id: str):
    if upload_id not in processing_status:
        raise HTTPException(status_code=404, detail="Upload ID not found")
    
    status_info = processing_status[upload_id]
    
    if status_info["status"] == "processing":
        raise HTTPException(status_code=202, detail="Processing not completed yet")
    
    if status_info["status"] == "failed":
        raise HTTPException(status_code=400, detail=status_info.get("message", "Processing failed"))
    
    result_path = OUTPUT_DIR / f"{upload_id}.json"
    if not result_path.exists():
        raise HTTPException(status_code=404, detail="Result file not found")
    
    with open(result_path, 'r') as f:
        result = json.load(f)
    
    return ExtractionResult(**result)


async def process_document(upload_id: str, file_path: str):
    try:
        logger.info(f"Starting processing for {upload_id}")
        
        result = pipeline.process(upload_id, file_path)
        
        pipeline.save_result(upload_id, result)
        
        processing_status[upload_id] = {
            "status": "completed",
            "upload_id": upload_id,
            "message": f"Processing completed. Document type: {result['document_type']}",
            "document_type": result["document_type"],
            "classification_confidence": result["classification_confidence"],
            "result": result
        }
        
        logger.info(f"Processing completed for {upload_id} - Type: {result['document_type']}")
    
    except Exception as e:
        logger.error(f"Processing error for {upload_id}: {str(e)}")
        processing_status[upload_id] = {
            "status": "failed",
            "upload_id": upload_id,
            "message": f"Processing failed: {str(e)}",
            "document_type": None,
            "classification_confidence": None
        }
