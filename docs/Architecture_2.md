# Unified Document Extraction System - Architecture & Design Document

## Executive Summary

The Unified Document Extraction System is a modern, intelligent API service that automatically processes financial documents (Bank Statements and Payslips) and extracts structured data using advanced OCR technology and pattern matching. The system is designed to handle both digital PDFs (fast processing) and scanned PDFs (OCR-based processing) with automatic detection and intelligent routing.

---

## 1. System Overview

### 1.1 Purpose

The system solves the problem of manual data entry from financial documents by:
- Automatically detecting document type (Bank Statement or Payslip)
- Extracting key financial information
- Validating extracted data
- Returning structured, machine-readable results

### 1.2 Key Capabilities

| Capability | Description |
|-----------|-------------|
| **Auto-Detection** | Automatically identifies document type without user input |
| **Dual Processing** | Fast path for digital PDFs, OCR path for scanned documents |
| **Multi-Bank Support** | Handles CIMB, Bank Islam, BSN, Public Islamic, and generic banks |
| **Multi-Language** | Supports English and Malay text extraction |
| **Multiple OCR Engines** | PaddleOCR (default), EasyOCR, Tesseract (fallback) |
| **Async Processing** | Background processing with status tracking |
| **Result Caching** | Instant response for repeated document uploads |
| **High Accuracy** | Bank-specific extraction patterns for reliable results |

### 1.3 Supported Documents

**Bank Statements:**
- Account holder name
- Account number
- Statement period
- Opening and closing balances
- Total debits and credits
- Available balance
- Bank identification

**Payslips:**
- Employee name
- ID number (NRIC)
- Gross income
- Net income
- Total deductions
- Deduction breakdown (EPF, SOCSO, Tax, etc.)
- Month and year

---

## 2. Architecture Overview

### 2.1 High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Client Layer                              │
│         (Web, Mobile, API Client, Postman)                  │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/HTTPS
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  API Gateway Layer                           │
│              (FastAPI + CORS Middleware)                     │
│  • Request validation and file upload handling              │
│  • Response formatting and error handling                   │
│  • Background task orchestration                            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│            Processing Pipeline Layer                         │
│         (Unified Extraction Pipeline Engine)                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 1. Document Type Detection (Digital vs Scanned)    │   │
│  │ 2. Text Extraction (PDFPlumber or OCR)             │   │
│  │ 3. Document Classification (Bank/Payslip)         │   │
│  │ 4. Smart Routing to Appropriate Extractor         │   │
│  │ 5. Field Extraction & Validation                  │   │
│  │ 6. Result Caching                                 │   │
│  └─────────────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
    ┌─────────────┐         ┌──────────────┐
    │   Bank      │         │   Payslip    │
    │ Statement   │         │  Extractor   │
    │ Extractor   │         │              │
    └─────────────┘         └──────────────┘
         │                       │
         └───────────┬───────────┘
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  Storage Layer                               │
│  • File System (uploads, processed, output)                 │
│  • Cache Storage (SHA256 hash-based caching)                │
│  • JSON Results (structured extraction output)              │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 System Components

The system is organized into five main layers:

1. **Application Layer** - API endpoints and request handling
2. **Core Processing Layer** - Business logic and document processing
3. **Extractor Layer** - Document-specific extraction logic
4. **Utility Layer** - Supporting functions and helpers
5. **Configuration Layer** - Centralized settings and patterns

---

## 3. Component Architecture

### 3.1 Application Layer (`app/`)

**Responsibility:** HTTP request/response handling and API management

**Components:**

| Component | Purpose |
|-----------|---------|
| **main.py** | FastAPI application initialization, middleware setup, lifecycle events |
| **config.py** | Application settings, environment variables, configuration management |
| **api/routes.py** | RESTful API endpoints, request handling, background task management |
| **api/schemas.py** | Pydantic models for request/response validation |

**Key Features:**
- CORS middleware for cross-origin requests
- Automatic API documentation (Swagger UI, ReDoc)
- Health check endpoints
- File upload handling with validation
- Background task management for async processing

### 3.2 Core Processing Layer (`core/`)

**Responsibility:** Core business logic and document processing engines

#### 3.2.1 Unified Pipeline (`unified_pipeline.py`)

**Role:** Main orchestrator that coordinates the entire processing workflow

**Workflow:**
1. Check cache for duplicate documents (SHA256 hash)
2. Detect if PDF is digital or scanned
3. Route to appropriate text extraction engine
4. Classify document type
5. Route to appropriate extractor
6. Validate and score results
7. Cache results for future requests

**Key Methods:**
- `process()` - Main entry point with caching
- `_process_with_pdfplumber()` - Fast path for digital PDFs
- `_process_with_ocr()` - OCR path for scanned PDFs

#### 3.2.2 Document Classifier (`document_classifier.py`)

**Role:** Automatically identifies document type

**Classification Method:**
- Keyword-based matching (Bank Statement vs Payslip)
- Confidence scoring
- Multi-language support (English/Malay)

**Example Keywords:**
- Bank Statement: "account", "balance", "statement", "transaction"
- Payslip: "salary", "gaji", "gross", "deduction", "net income"

#### 3.2.3 OCR Engine (`ocr_engine.py`)

**Role:** Abstract interface for multiple OCR engines

**Supported Engines:**
- **PaddleOCR** (default) - High accuracy, good for Asian languages
- **EasyOCR** - Alternative with good multilingual support
- **Tesseract** - Fallback option, widely available

**Capabilities:**
- Text extraction from images
- Coordinate extraction (bounding boxes)
- Token generation with confidence scores
- Multi-page document support

#### 3.2.4 PDFPlumber Engine (`pdfplumber_engine.py`)

**Role:** Fast text extraction from digital PDFs

**Advantages:**
- No OCR overhead (10x faster than OCR)
- Preserves document layout
- Accurate coordinate information
- Ideal for born-digital PDFs

**Detection Method:**
- Attempts text extraction
- If successful → digital PDF
- If fails → scanned PDF (needs OCR)

#### 3.2.5 Bank Detector (`bank_detector.py`)

**Role:** Identifies specific bank from statement

**Supported Banks:**
- CIMB Bank
- Bank Islam
- BSN (Bank Simpanan Nasional)
- Public Islamic Bank
- Generic (fallback for unknown banks)

**Detection Method:**
- Bank-specific keywords and patterns
- Logo/header recognition
- Account number format matching
- Confidence scoring

#### 3.2.6 Layout Analyzer (`layout_analyzer.py`)

**Role:** Analyzes spatial relationships between text elements

**Functions:**
- Groups tokens into lines
- Detects text alignment
- Identifies table structures
- Preserves document layout information

#### 3.2.7 Spatial Search (`spatial_search.py`)

**Role:** Extracts fields using spatial proximity

**Method:**
- Finds keyword (e.g., "Gross Income")
- Searches nearby tokens for values
- Merges multi-word fields
- Context-aware extraction

#### 3.2.8 Validators (`validators.py`)

**Role:** Validates extracted data

**Validation Types:**
- Format validation (NRIC format, date format)
- Range validation (salary within reasonable range)
- Consistency validation (gross >= net + deductions)
- Type validation (numeric, string, date)

#### 3.2.9 Utilities (`utils.py`)

**Role:** Common utility functions

**Functions:**
- Currency formatting and parsing
- Number normalization
- NRIC formatting
- Percentage detection
- Text cleaning

### 3.3 Extractor Layer (`extractors/`)

**Responsibility:** Document-specific field extraction logic

#### 3.3.1 Bank Statement Extractor

**Extraction Strategy:**
- Regex-based pattern matching
- Bank-specific extraction rules
- Multi-page statement handling
- Field caching for continuation pages

**Extracted Fields:**
- Account holder name
- Account number
- Statement date range
- Opening balance
- Closing balance
- Total debit
- Total credit
- Available balance
- Detected bank

**Bank-Specific Logic:**

**CIMB Bank:**
- Account format: `XX-XXXXXXX-X`
- No summary section
- Direct field extraction

**Bank Islam:**
- Calculated closing balance: Opening + Credit - Debit
- Caches opening balance for multi-page statements
- Special handling for continuation pages

**BSN:**
- Available balance extraction
- Specific date format handling

**Public Islamic:**
- Date format: DD Month YYYY
- Special transaction format

#### 3.3.2 Payslip Extractor

**Extraction Strategy:**
- Spatial extraction (primary method)
- Regex fallback for unstructured payslips
- Token usage tracking (prevents duplicate extraction)
- Calculated fields (net = gross - deductions)

**Extracted Fields:**
- Employee name
- ID number (NRIC)
- Gross income
- Net income
- Total deduction
- Deduction items (EPF, SOCSO, Tax, etc.)
- Month and year

**Special Features:**
- Deduction item aggregation
- Math validation (gross - deduction = net)
- Multi-format date handling
- Fuzzy matching for OCR errors

### 3.4 Utility Layer (`utils/`)

**Responsibility:** Supporting utilities and helpers

| Component | Purpose |
|-----------|---------|
| **pdf_processor.py** | PDF to image conversion using PyMuPDF |
| **text_cleaner.py** | Text normalization and cleaning |
| **spatial_extractor.py** | Spatial field extraction from PDF pages |
| **config_loader.py** | Configuration file management |
| **logger.py** | Logging setup and management |

### 3.5 Configuration Layer (`config/`)

**Responsibility:** Centralized configuration management

**Configuration Files:**

| File | Purpose |
|------|---------|
| **extraction_config.json** | Bank statement extraction patterns and keywords |
| **payslip_extraction_config.json** | Payslip extraction patterns and keywords |
| **bank_specific_config.json** | Bank-specific rules and patterns |
| **ocr_config.json** | OCR engine settings and parameters |
| **app_config.yaml** | Application-level settings |

---

## 4. Data Flow Architecture

### 4.1 Digital PDF Processing Flow

```
PDF Upload
    ↓
PDFPlumber.can_extract_text() → YES
    ↓
Extract text + tokens (PDFPlumber)
    ↓
Document Classification (keyword matching)
    ↓
Route to Extractor (Bank Statement / Payslip)
    ↓
Regex + Spatial Extraction
    ↓
Validation & Confidence Scoring
    ↓
Cache Result (SHA256 hash)
    ↓
JSON Output
```

**Performance:** 1-2 seconds per document

### 4.2 Scanned PDF Processing Flow

```
PDF Upload
    ↓
PDFPlumber.can_extract_text() → NO
    ↓
Convert PDF to Images (PyMuPDF)
    ↓
Image Optimization (deskew, contrast, denoise)
    ↓
OCR Processing (PaddleOCR/EasyOCR/Tesseract)
    ↓
Extract text + tokens with coordinates
    ↓
Document Classification (keyword matching)
    ↓
Route to Extractor (Bank Statement / Payslip)
    ↓
Regex + Spatial Extraction
    ↓
Validation & Confidence Scoring
    ↓
Cache Result (SHA256 hash)
    ↓
JSON Output
```

**Performance:** 10-20 seconds per document (depending on pages)

### 4.3 Caching Flow

```
PDF Upload
    ↓
Calculate SHA256 Hash
    ↓
Check Cache Index
    ↓
Cache Hit? → YES → Return Cached Result (0.1s)
    ↓ NO
Process Document (normal flow)
    ↓
Save Result to Cache
    ↓
Return Result
```

**Performance Improvement:**
- First request: 30 seconds
- Repeated request: 0.1 seconds (300x faster)

---

## 5. API Endpoints

### 5.1 Upload Document

**Endpoint:** `POST /api/upload`

**Request:**
- File: PDF document (multipart/form-data)

**Response:**
```json
{
  "upload_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "message": "Document uploaded successfully"
}
```

### 5.2 Check Processing Status

**Endpoint:** `GET /api/status/{upload_id}`

**Response:**
```json
{
  "upload_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": 100
}
```

### 5.3 Get Extraction Results

**Endpoint:** `GET /api/result/{upload_id}`

**Response (Bank Statement):**
```json
{
  "upload_id": "550e8400-e29b-41d4-a716-446655440000",
  "document_type": "bank_statement",
  "extraction_method": "pdfplumber",
  "documents": [
    {
      "document_number": 1,
      "extracted_data": {
        "account_holder": "John Doe",
        "account_number": "12-3456789-0",
        "statement_date": "2024-01-31",
        "opening_balance": "5000.00",
        "closing_balance": "6500.00",
        "total_debit": "2000.00",
        "total_credit": "3500.00",
        "detected_bank": "cimb"
      },
      "confidence_score": 0.95
    }
  ]
}
```

**Response (Payslip):**
```json
{
  "upload_id": "550e8400-e29b-41d4-a716-446655440000",
  "document_type": "payslip",
  "extraction_method": "paddleocr",
  "documents": [
    {
      "document_number": 1,
      "extracted_data": {
        "name": "Jane Smith",
        "id_number": "123456-12-1234",
        "gross_income": "5000.00",
        "net_income": "4200.00",
        "total_deduction": "800.00",
        "month_year": "01/2024",
        "deductions": {
          "epf": "300.00",
          "socso": "100.00",
          "tax": "400.00"
        }
      },
      "confidence_score": 0.92
    }
  ]
}
```

### 5.4 Health Check

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "service": "unified-document-extractor"
}
```

---

## 6. Design Patterns

### 6.1 Strategy Pattern

**Usage:** OCR Engine Selection

**Implementation:**
- Abstract `OCREngine` base class
- Multiple implementations (PaddleOCR, EasyOCR, Tesseract)
- Runtime selection based on configuration
- Easy to add new OCR engines

**Benefit:** Flexibility to switch OCR engines without changing core logic

### 6.2 Pipeline Pattern

**Usage:** Document Processing Workflow

**Implementation:**
- Sequential processing stages
- Each stage transforms data for the next
- Clear separation of concerns
- Easy to add/remove processing steps

**Benefit:** Modular, maintainable processing flow

### 6.3 Factory Pattern

**Usage:** OCR Engine Creation

**Implementation:**
- `get_ocr_engine()` function
- Encapsulates engine instantiation logic
- Centralized engine creation

**Benefit:** Single point of control for engine creation

### 6.4 Template Method Pattern

**Usage:** Field Extraction

**Implementation:**
- Common extraction workflow in base class
- Bank-specific overrides in subclasses
- Reusable extraction logic with customization points

**Benefit:** Code reuse with customization flexibility

### 6.5 Singleton Pattern

**Usage:** Configuration Loading

**Implementation:**
- Cached configuration loading
- Prevents redundant file I/O
- Single instance per configuration file

**Benefit:** Performance optimization and consistency

---

## 7. Performance Characteristics

### 7.1 Processing Time

| Document Type | Digital PDF | Scanned PDF |
|--------------|-------------|-------------|
| Bank Statement | 1-2 seconds | 15-20 seconds |
| Payslip | 1-2 seconds | 10-15 seconds |
| Cached Result | 0.1 seconds | 0.1 seconds |

### 7.2 Throughput

- **Single Instance:** 30-60 documents per minute
- **With Caching:** 100-300 documents per minute (for repeated documents)

### 7.3 Resource Usage

| Resource | Usage |
|----------|-------|
| Memory | 500MB - 2GB (depending on OCR engine) |
| CPU | 1-4 cores (scales with document complexity) |
| Disk | 50KB per cached result |
| Network | 1-10MB per document (PDF size dependent) |

---

## 8. Security Architecture

### 8.1 Current Security Measures

1. **File Type Validation** - Only PDF files accepted
2. **File Size Limits** - 10MB maximum upload size
3. **CORS Protection** - Configurable allowed origins
4. **Input Sanitization** - Text cleaning and validation
5. **Error Handling** - No sensitive data in error messages

### 8.2 Recommended Enhancements

1. **Authentication** - JWT/OAuth2 for API access
2. **Rate Limiting** - Prevent abuse and DoS attacks
3. **Encryption** - Encrypt sensitive data at rest
4. **Audit Logging** - Track all document processing
5. **Virus Scanning** - Scan uploaded files for malware
6. **Data Retention** - Automatic cleanup of old files

---

## 9. Scalability Architecture

### 9.1 Current Limitations

- Synchronous processing (one document at a time)
- In-memory state (processing status stored in dictionary)
- File-based storage (results saved to JSON files)
- Single instance deployment

### 9.2 Horizontal Scaling Strategy

1. **Load Balancer** - Distribute requests across multiple instances
2. **Shared Storage** - Use S3/MinIO for file storage
3. **Database** - Replace in-memory state with Redis/PostgreSQL
4. **Message Queue** - Use Celery/RabbitMQ for async processing

### 9.3 Vertical Scaling Strategy

1. **GPU Acceleration** - Use GPU for OCR processing
2. **Multi-threading** - Process multiple pages in parallel
3. **Caching** - Cache OCR results for duplicate documents
4. **Lazy Loading** - Load OCR engine only when needed

### 9.4 Optimization Opportunities

1. **Batch Processing** - Process multiple documents in one request
2. **Streaming** - Stream large PDFs instead of loading entirely
3. **Lazy Loading** - Load OCR engine only when needed
4. **Result Caching** - Cache extraction results by document hash (implemented)

---

## 10. Technology Stack

### 10.1 Backend Framework

| Technology | Purpose |
|-----------|---------|
| **FastAPI** | Modern, fast web framework with async support |
| **Uvicorn** | ASGI server for production deployment |
| **Pydantic** | Data validation and serialization |

### 10.2 OCR Engines

| Engine | Characteristics |
|--------|-----------------|
| **PaddleOCR** | High accuracy, good for Asian languages, default choice |
| **EasyOCR** | Alternative with good multilingual support |
| **Tesseract** | Fallback option, widely available, lower accuracy |

### 10.3 PDF Processing

| Library | Purpose |
|---------|---------|
| **PyMuPDF (fitz)** | PDF to image conversion |
| **PDFPlumber** | Digital PDF text extraction |

### 10.4 Image Processing

| Library | Purpose |
|---------|---------|
| **OpenCV** | Image preprocessing and optimization |
| **Pillow** | Image manipulation and conversion |

### 10.5 Utilities

| Technology | Purpose |
|-----------|---------|
| **Python 3.11+** | Modern Python features |
| **python-dotenv** | Environment variable management |
| **aiofiles** | Async file operations |

---

## 11. Deployment Architecture

### 11.1 Development Environment

```
Local Machine
    ↓
Python 3.11+ Virtual Environment
    ↓
FastAPI Development Server (uvicorn with reload)
    ↓
http://localhost:8000
```

### 11.2 Production Environment (Recommended)

```
Load Balancer (Nginx/HAProxy)
    ↓
Multiple FastAPI Instances (uvicorn workers)
    ↓
Shared Storage (S3/MinIO)
    ↓
Database (PostgreSQL/Redis)
    ↓
Message Queue (Celery/RabbitMQ)
```

### 11.3 Docker Deployment

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 12. Monitoring and Observability

### 12.1 Current Logging

- File-based logging: `output/logs/app.log`
- Console logging: Real-time output
- Log levels: DEBUG, INFO, WARNING, ERROR

### 12.2 Recommended Monitoring

1. **Application Metrics** - Response time, throughput, error rate
2. **System Metrics** - CPU, memory, disk usage
3. **Business Metrics** - Documents processed, success rate, confidence scores
4. **Alerting** - Slack/Email notifications for failures
5. **Tracing** - Distributed tracing for request flow

### 12.3 Monitoring Tools

| Tool | Purpose |
|------|---------|
| **Prometheus** | Metrics collection |
| **Grafana** | Visualization |
| **ELK Stack** | Log aggregation and analysis |
| **Sentry** | Error tracking |

---

## 13. Configuration Management

### 13.1 Environment Variables

```
HOST=0.0.0.0
PORT=8000
DEBUG=False
LOG_LEVEL=INFO
OCR_ENGINE=paddleocr
OCR_LANGUAGE=en
UPLOAD_DIR=uploads/raw
PROCESSED_DIR=uploads/processed
OUTPUT_DIR=output
```

### 13.2 Configuration Files

- **JSON:** Extraction patterns and rules
- **YAML:** Application settings
- **Python:** Code-level configuration

### 13.3 Configuration Hierarchy

1. Environment variables (highest priority)
2. Configuration files
3. Default values (lowest priority)

---

## 14. Error Handling Strategy

### 14.1 Error Categories

1. **Client Errors (4xx)** - Invalid input, file format errors
2. **Server Errors (5xx)** - Processing failures, OCR errors
3. **Validation Errors** - Field format violations

### 14.2 Error Response Format

```json
{
  "status": "error",
  "error": "Error message",
  "details": "Detailed error information"
}
```

### 14.3 Recovery Mechanisms

1. **Retry Logic** - Automatic retry for transient failures
2. **Fallback Engines** - Switch OCR engine on failure
3. **Graceful Degradation** - Return partial results when possible
4. **Error Logging** - Detailed error tracking for debugging

---

## 15. Future Enhancements

### 15.1 Short-term (3-6 months)

1. Database integration (PostgreSQL)
2. Redis caching for results
3. Webhook notifications
4. Batch processing API

### 15.2 Medium-term (6-12 months)

1. Docker containerization
2. Kubernetes orchestration
3. Microservices architecture
4. GraphQL API

### 15.3 Long-term (12+ months)

1. Machine learning models for extraction
2. Real-time processing with WebSockets
3. Multi-tenant architecture
4. Cloud-native deployment (AWS/Azure/GCP)

---

## 16. Conclusion

The Unified Document Extraction System is a well-architected, scalable solution for automated financial document processing. The modular design allows for easy maintenance and extension, while the intelligent routing and caching mechanisms ensure optimal performance. The system is production-ready and can be deployed in various environments with appropriate scaling strategies.

