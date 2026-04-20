# System Architecture Documentation

## Overview

The Unified Document Extraction System is a modular, scalable FastAPI-based application designed to automatically detect and extract structured data from financial documents (Bank Statements and Payslips) using OCR technology and intelligent pattern matching.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                             │
│  (Web Browser, Mobile App, API Client, Postman)                 │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP/HTTPS
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway Layer                           │
│                    (FastAPI + CORS)                              │
│  - Request Validation                                            │
│  - File Upload Handling                                          │
│  - Response Formatting                                           │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Processing Pipeline Layer                      │
│                  (Unified Pipeline Engine)                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  1. Document Type Detection (Digital vs Scanned)        │   │
│  │  2. Text Extraction (PDFPlumber or OCR)                 │   │
│  │  3. Document Classification (Bank Statement/Payslip)    │   │
│  │  4. Smart Routing to Appropriate Extractor              │   │
│  │  5. Field Extraction & Validation                       │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         ▼                               ▼
┌──────────────────┐           ┌──────────────────┐
│  Bank Statement  │           │     Payslip      │
│    Extractor     │           │    Extractor     │
│                  │           │                  │
│ - Account Info   │           │ - Employee Info  │
│ - Balances       │           │ - Salary Details │
│ - Transactions   │           │ - Deductions     │
│ - Bank Detection │           │ - EPF/SOCSO      │
└──────────────────┘           └──────────────────┘
         │                               │
         └───────────────┬───────────────┘
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Storage Layer                               │
│  - File System (uploads/raw, uploads/processed)                 │
│  - JSON Output (output/json)                                    │
│  - Logs (output/logs)                                           │
└─────────────────────────────────────────────────────────────────┘
```

## Component Architecture

### 1. Application Layer (`app/`)

**Purpose:** Entry point and API management

**Components:**
- **main.py**: FastAPI application initialization, middleware setup, lifecycle management
- **config.py**: Application settings, environment variables, configuration management
- **api/routes.py**: RESTful API endpoints, request handling, background task management
- **api/schemas.py**: Pydantic models for request/response validation

**Key Responsibilities:**
- HTTP request/response handling
- File upload management
- Background task orchestration
- CORS and security middleware
- API documentation (Swagger/ReDoc)

### 2. Core Processing Layer (`core/`)

**Purpose:** Core business logic and processing engines

**Components:**

#### a. **unified_pipeline.py** (Orchestrator)
- Main processing coordinator
- Routes documents to appropriate handlers
- Manages digital vs scanned PDF detection
- Coordinates OCR and PDFPlumber engines

#### b. **document_classifier.py** (Classifier)
- Keyword-based document type detection
- Distinguishes between bank statements and payslips
- Confidence scoring for classification
- Multi-language support (English/Malay)

#### c. **ocr_engine.py** (OCR Abstraction)
- Abstract OCR interface
- Multiple engine implementations:
  - PaddleOCR (default, high accuracy)
  - EasyOCR (alternative)
  - Tesseract (fallback)
- Text and coordinate extraction
- Token generation with bounding boxes

#### d. **pdfplumber_engine.py** (Digital PDF Handler)
- Fast text extraction from digital PDFs
- Token extraction with coordinates
- Layout preservation
- No OCR overhead for digital documents

#### e. **bank_detector.py** (Bank Identification)
- Bank-specific pattern matching
- Supports: CIMB, Bank Islam, BSN, Public Islamic
- Confidence scoring
- Generic fallback for unknown banks

#### f. **layout_analyzer.py** (Spatial Analysis)
- Token grouping into lines
- Spatial relationship detection
- Layout structure analysis

#### g. **spatial_search.py** (Proximity Search)
- Field extraction using spatial proximity
- Token merging for multi-word fields
- Context-aware extraction

#### h. **validators.py** (Data Validation)
- Field format validation
- Date range validation
- Currency format validation
- ID number validation

#### i. **utils.py** (Core Utilities)
- Currency formatting
- Number parsing
- NRIC normalization
- Percentage detection

#### j. **number_formatter.py** (Number Processing)
- Bank-specific number formatting
- Decimal normalization
- Currency cleaning

### 3. Extractor Layer (`extractors/`)

**Purpose:** Document-specific field extraction logic

#### a. **bank_statement_extractor.py**
**Extraction Strategy:**
- Regex-based pattern matching
- Bank-specific extraction rules
- Multi-page statement handling
- Field caching for continuation pages

**Extracted Fields:**
- Account holder name
- Account number
- Statement date
- Opening balance
- Closing balance
- Total debit
- Total credit
- Statement period (from/to)
- Available balance (bank-specific)

**Bank-Specific Logic:**
- **CIMB**: Account format `XX-XXXXXXX-X`, no summary section
- **Bank Islam**: Calculated closing balance (Opening + Credit - Debit)
- **BSN**: Available balance extraction
- **Public Islamic**: Date format handling (DD Month YYYY)

#### b. **payslip_extractor.py**
**Extraction Strategy:**
- Spatial extraction (primary)
- Regex fallback
- Token usage tracking (prevents duplicate extraction)
- Calculated fields (net income = gross - deductions)

**Extracted Fields:**
- Employee name
- ID number (NRIC)
- Gross income
- Net income
- Total deduction
- Month/Year

**Special Features:**
- Deduction item aggregation
- Math validation (gross - deduction = net)
- Multi-format date handling

### 4. Utility Layer (`utils/`)

**Purpose:** Supporting utilities and helpers

**Components:**
- **pdf_processor.py**: PDF to image conversion using PyMuPDF
- **text_cleaner.py**: Text normalization and cleaning
- **spatial_extractor.py**: Spatial field extraction from PDF pages
- **config_loader.py**: Configuration file management
- **logger.py**: Logging setup and management

### 5. Configuration Layer (`config/`)

**Purpose:** Centralized configuration management

**Configuration Files:**
- **extraction_config.json**: Bank statement extraction patterns
- **payslip_extraction_config.json**: Payslip extraction patterns
- **bank_specific_config.json**: Bank-specific rules and patterns
- **ocr_config.json**: OCR engine settings
- **app_config.yaml**: Application-level settings

## Data Flow Architecture

### Digital PDF Processing Flow

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
JSON Output
```

**Performance:** 1-2 seconds per document

### Scanned PDF Processing Flow

```
PDF Upload
    ↓
PDFPlumber.can_extract_text() → NO
    ↓
Convert PDF to Images (PyMuPDF)
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
JSON Output
```

**Performance:** 10-20 seconds per document (depending on pages)

## Design Patterns

### 1. Strategy Pattern
- **OCREngine**: Abstract base class with multiple implementations
- Allows runtime selection of OCR engine
- Easy to add new OCR engines

### 2. Pipeline Pattern
- **UnifiedExtractionPipeline**: Sequential processing stages
- Each stage transforms data for the next
- Clear separation of concerns

### 3. Factory Pattern
- **get_ocr_engine()**: Creates appropriate OCR engine instance
- Encapsulates engine instantiation logic

### 4. Template Method Pattern
- **FieldExtractor**: Common extraction workflow with bank-specific overrides
- Reusable extraction logic with customization points

### 5. Singleton Pattern
- **ConfigLoader**: Cached configuration loading
- Prevents redundant file I/O

## Scalability Considerations

### Current Architecture
- **Synchronous processing**: One document at a time
- **In-memory state**: Processing status stored in dictionary
- **File-based storage**: Results saved to JSON files

### Scaling Strategies

#### Horizontal Scaling
1. **Load Balancer**: Distribute requests across multiple instances
2. **Shared Storage**: Use S3/MinIO for file storage
3. **Database**: Replace in-memory state with Redis/PostgreSQL
4. **Message Queue**: Use Celery/RabbitMQ for async processing

#### Vertical Scaling
1. **GPU Acceleration**: Use GPU for OCR processing
2. **Multi-threading**: Process multiple pages in parallel
3. **Caching**: Cache OCR results for duplicate documents

#### Optimization Opportunities
1. **Batch Processing**: Process multiple documents in one request
2. **Streaming**: Stream large PDFs instead of loading entirely
3. **Lazy Loading**: Load OCR engine only when needed (already implemented)
4. **Result Caching**: Cache extraction results by document hash

## Security Architecture

### Current Security Measures
1. **File Type Validation**: Only PDF files accepted
2. **File Size Limits**: 10MB maximum upload size
3. **CORS Protection**: Configurable allowed origins
4. **Input Sanitization**: Text cleaning and validation
5. **Error Handling**: No sensitive data in error messages

### Recommended Enhancements
1. **Authentication**: JWT/OAuth2 for API access
2. **Rate Limiting**: Prevent abuse and DoS attacks
3. **Encryption**: Encrypt sensitive data at rest
4. **Audit Logging**: Track all document processing
5. **Virus Scanning**: Scan uploaded files for malware
6. **Data Retention**: Automatic cleanup of old files

## Technology Stack

### Backend Framework
- **FastAPI**: Modern, fast web framework with async support
- **Uvicorn**: ASGI server for production deployment
- **Pydantic**: Data validation and serialization

### OCR Engines
- **PaddleOCR**: Primary OCR engine (high accuracy)
- **EasyOCR**: Alternative OCR engine
- **Tesseract**: Fallback OCR engine

### PDF Processing
- **PyMuPDF (fitz)**: PDF to image conversion
- **PDFPlumber**: Digital PDF text extraction

### Image Processing
- **OpenCV**: Image preprocessing
- **Pillow**: Image manipulation

### Utilities
- **Python 3.11+**: Modern Python features
- **python-dotenv**: Environment variable management
- **aiofiles**: Async file operations

## Deployment Architecture

### Development Environment
```
Local Machine
    ↓
Python 3.11+ Virtual Environment
    ↓
FastAPI Development Server (uvicorn with reload)
    ↓
http://localhost:8000
```

### Production Environment (Recommended)
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

### Docker Deployment (Future)
```dockerfile
# Dockerfile structure
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Monitoring and Observability

### Current Logging
- **File-based logging**: `output/logs/app.log`
- **Console logging**: Real-time output
- **Log levels**: DEBUG, INFO, WARNING, ERROR

### Recommended Monitoring
1. **Application Metrics**: Response time, throughput, error rate
2. **System Metrics**: CPU, memory, disk usage
3. **Business Metrics**: Documents processed, success rate, confidence scores
4. **Alerting**: Slack/Email notifications for failures
5. **Tracing**: Distributed tracing for request flow

### Tools
- **Prometheus**: Metrics collection
- **Grafana**: Visualization
- **ELK Stack**: Log aggregation and analysis
- **Sentry**: Error tracking

## Configuration Management

### Environment Variables (.env)
```
HOST=0.0.0.0
PORT=8000
DEBUG=False
LOG_LEVEL=INFO
OCR_ENGINE=paddleocr
OCR_LANGUAGE=en
```

### Configuration Files
- **JSON**: Extraction patterns and rules
- **YAML**: Application settings
- **Python**: Code-level configuration

### Configuration Hierarchy
1. Environment variables (highest priority)
2. Configuration files
3. Default values (lowest priority)

## Error Handling Strategy

### Error Categories
1. **Client Errors (4xx)**: Invalid input, file format errors
2. **Server Errors (5xx)**: Processing failures, OCR errors
3. **Validation Errors**: Field format violations

### Error Response Format
```json
{
  "status": "error",
  "error": "Error message",
  "details": "Detailed error information"
}
```

### Recovery Mechanisms
1. **Retry Logic**: Automatic retry for transient failures
2. **Fallback Engines**: Switch OCR engine on failure
3. **Graceful Degradation**: Return partial results when possible
4. **Error Logging**: Detailed error tracking for debugging

## Future Architecture Enhancements

### Short-term (3-6 months)
1. Database integration (PostgreSQL)
2. Redis caching for results
3. Webhook notifications
4. Batch processing API

### Medium-term (6-12 months)
1. Docker containerization
2. Kubernetes orchestration
3. Microservices architecture
4. GraphQL API

### Long-term (12+ months)
1. Machine learning models for extraction
2. Real-time processing with WebSockets
3. Multi-tenant architecture
4. Cloud-native deployment (AWS/Azure/GCP)
