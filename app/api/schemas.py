from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime


class DocumentExtraction(BaseModel):
    """Single document extraction result"""
    document_number: int
    document_type: str  # "bank_statement" or "payslip"
    extracted_data: Dict[str, Any]
    confidence_score: float
    text_length: int


class ExtractionSummary(BaseModel):
    """Summary of extraction results"""
    bank_statements: Optional[int] = 0
    payslips: Optional[int] = 0
    other: int = 0
    average_confidence: float


class ExtractionResult(BaseModel):
    """Complete extraction result"""
    upload_id: str
    file_type: str
    document_type: str  # "bank_statement" or "payslip"
    classification_confidence: float
    extraction_method: str  # "pdfplumber" or "paddleocr" etc.
    total_documents: int
    documents: List[DocumentExtraction]
    summary: ExtractionSummary
    processing_completed_at: datetime
    original_file: str
    total_text_length: int


class UploadResponse(BaseModel):
    """Response after file upload"""
    status: str
    upload_id: str
    message: str = "File uploaded successfully. Processing started."


class StatusResponse(BaseModel):
    """Processing status response"""
    status: str  # "processing", "completed", "failed"
    upload_id: str
    message: Optional[str] = None
    document_type: Optional[str] = None  # Available after classification
    classification_confidence: Optional[float] = None
    result: Optional[ExtractionResult] = None


class ErrorResponse(BaseModel):
    """Error response"""
    status: str = "error"
    error: str
    details: Optional[str] = None
