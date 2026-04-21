# Unified Document Extraction System - Architecture v1

## Current System Overview

This is a FastAPI-based document extraction system that automatically detects and extracts structured data from Bank Statements and Payslips using OCR technology.

## System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   PDF Upload    │───▶│  Document Type   │───▶│   Appropriate   │
│                 │    │   Detection      │    │   Extractor     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │  Digital/Scanned │
                       │   Detection      │
                       └──────────────────┘
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
            ┌──────────────┐        ┌──────────────┐
            │ PDFPlumber   │        │ OCR Engine   │
            │ (Digital)    │        │ (Scanned)    │
            └──────────────┘        └──────────────┘
                    │                       │
                    └───────────┬───────────┘
                                ▼
                    ┌──────────────────────┐
                    │  Text Processing &   │
                    │  Field Extraction    │
                    └──────────────────────┘
                                │
                                ▼
                    ┌──────────────────────┐
                    │  Structured JSON     │
                    │     Response         │
                    └──────────────────────┘
```

## Core Components

### 1. **FastAPI Application** (`app/`)
- **main.py**: Application entry point
- **api/routes.py**: REST API endpoints
- **api/schemas.py**: Pydantic models
- **config.py**: Application configuration

### 2. **Core Processing Engine** (`core/`)
- **unified_pipeline.py**: Main processing pipeline
- **document_classifier.py**: Auto document type detection
- **ocr_engine.py**: OCR engines (PaddleOCR, EasyOCR, Tesseract)
- **pdfplumber_engine.py**: Digital PDF text extraction
- **bank_detector.py**: Bank type detection
- **validators.py**: Data validation

### 3. **Extractors** (`extractors/`)
- **payslip_extractor.py**: Payslip field extraction logic
- **bank_statement_extractor.py**: Bank statement extraction logic

### 4. **Utilities** (`utils/`)
- **pdf_processor.py**: PDF to image conversion
- **text_cleaner.py**: Text preprocessing
- **spatial_extractor.py**: Spatial text extraction
- **logger.py**: Logging setup

### 5. **Configuration** (`config/`)
- **payslip_extraction_config.json**: Payslip patterns & rules
- **extraction_config.json**: Bank statement patterns
- **ocr_config.json**: OCR engine settings
- **bank_specific_config.json**: Bank-specific rules

## Processing Flow

### Document Upload
1. **File Upload** via `/api/upload` endpoint
2. **File Validation** (PDF format, size limits)
3. **Unique ID Generation** for tracking

### Document Classification
1. **Digital vs Scanned Detection**
   - Try PDFPlumber text extraction
   - If text length > 50 chars → Digital PDF
   - Else → Scanned PDF (needs OCR)

2. **Document Type Detection**
   - Extract sample text
   - Use keyword matching
   - Classify as Bank Statement or Payslip

### Text Extraction
- **Digital PDFs**: Use PDFPlumber for fast text extraction
- **Scanned PDFs**: Convert to images → OCR processing

### Field Extraction
- **Pattern Matching**: Regex patterns for each field
- **Spatial Extraction**: Position-based extraction
- **Fallback Patterns**: Multiple patterns per field
- **Validation**: Data type and business rule validation

### Response Generation
- **Structured JSON** with extracted fields
- **Confidence Scores** for extraction quality
- **Validation Errors** if any
- **Processing Metadata**

## Current Capabilities

### Payslip Extraction
- ✅ **Name**: Employee name with bin/binti support
- ✅ **ID Number**: Malaysian IC format (XXXXXX-XX-XXXX)
- ✅ **Gross Income**: Total earnings
- ✅ **Net Income**: Take-home salary
- ✅ **Total Deduction**: Sum of all deductions
- ✅ **Month/Year**: Payslip period

### Bank Statement Extraction
- ✅ **Account Number**: Bank account identification
- ✅ **Account Holder**: Account owner name
- ✅ **Statement Period**: Date range
- ✅ **Opening/Closing Balance**: Account balances
- ✅ **Transaction History**: Individual transactions

### Supported Banks
- CIMB Bank
- Bank Islam
- BSN (Bank Simpanan Nasional)
- Public Islamic Bank
- Generic bank statements

## Technology Stack

### Backend
- **FastAPI**: Web framework
- **Python 3.11+**: Programming language
- **Pydantic**: Data validation
- **Uvicorn**: ASGI server

### OCR Engines
- **PaddleOCR**: Primary OCR engine
- **EasyOCR**: Alternative OCR engine
- **Tesseract**: Fallback OCR engine

### PDF Processing
- **PDFPlumber**: Digital PDF text extraction
- **PyMuPDF (fitz)**: PDF to image conversion
- **Pillow**: Image processing

### Data Processing
- **Regex**: Pattern matching
- **JSON**: Configuration and responses
- **Logging**: Application monitoring

## API Endpoints

### Core Endpoints
- `POST /api/upload` - Upload document for processing
- `GET /api/status/{upload_id}` - Check processing status
- `GET /api/result/{upload_id}` - Get extraction results
- `GET /health` - Health check

### Response Format
```json
{
  "upload_id": "unique-id",
  "document_type": "payslip|bank_statement",
  "processing_status": "completed|processing|failed",
  "extracted_data": {
    "name": "Employee Name",
    "id_number": "123456-78-9012",
    "gross_income": "5000.00",
    "net_income": "4200.00",
    "total_deduction": "800.00",
    "month_year": "12/2024"
  },
  "confidence": 0.95,
  "validation_errors": [],
  "processing_time": "2.5s"
}
```

## Current Issues & Limitations

### OCR Quality Issues
- Poor text recognition on scanned payslips
- Character substitution errors (O→0, l→1)
- Layout detection problems
- Low confidence scores

### Pattern Matching Limitations
- Rigid regex patterns
- Poor handling of OCR errors
- Limited fuzzy matching
- Context-insensitive extraction

### Performance Bottlenecks
- OCR processing time (10-20 seconds)
- Memory usage with large PDFs
- No caching mechanism
- Sequential processing only

## File Structure
```
unified-document-extractor/
├── app/                    # FastAPI application
├── core/                   # Core processing logic
├── extractors/             # Document-specific extractors
├── utils/                  # Utility functions
├── config/                 # Configuration files
├── uploads/                # Uploaded files storage
├── output/                 # Processing results
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
└── README.md              # Project documentation
```

## Environment Configuration
```env
# OCR Engine Selection
OCR_ENGINE=paddleocr          # paddleocr, easyocr, tesseract
OCR_LANGUAGE=en               # en, ms, ch

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=False

# File Handling
MAX_FILE_SIZE=10485760        # 10MB
UPLOAD_DIR=uploads/raw
PROCESSED_DIR=uploads/processed
OUTPUT_DIR=output/json

# Logging
LOG_LEVEL=INFO
LOG_FILE=output/logs/app.log
```

## Current Status
- ✅ **Basic functionality working**
- ✅ **Digital PDF extraction accurate**
- ⚠️ **Scanned PDF extraction needs improvement**
- ⚠️ **OCR quality issues on complex layouts**
- ⚠️ **Pattern matching needs enhancement**

---
*Architecture documented as of current system state*