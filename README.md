# Unified Document Extraction System

A FastAPI-based service that **automatically detects and extracts** structured data from **Bank Statements** and **Payslips** using OCR technology.

## 🎯 Features

- ✅ **Automatic Document Type Detection** - No need to specify document type
- ✅ **Bank Statement Extraction** - Account number, balances, dates, transactions
- ✅ **Payslip Extraction** - Name, salary, deductions, EPF, SOCSO
- ✅ **Multi-Language Support** - English and Malay
- ✅ **Multiple OCR Engines** - PaddleOCR, EasyOCR, Tesseract
- ✅ **Smart PDF Processing** - Digital PDF (fast) or Scanned PDF (OCR)
- ✅ **Async Processing** - Background processing with status tracking
- ✅ **High Accuracy** - Bank-specific extraction patterns

## 🏗️ Architecture

```
Upload PDF
    ↓
Digital or Scanned? (Auto-detect)
    ↓
Extract Text (PDFPlumber or OCR)
    ↓
Classify Document Type (Bank Statement or Payslip)
    ↓
Route to Appropriate Extractor
    ↓
Return Structured Data
```

## 📋 Prerequisites

- Python 3.11+
- pip
- Tesseract OCR (optional, for tesseract engine)

## 🚀 Installation

### 1. Clone Repository
```bash
cd unified-document-extractor
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env file with your settings
```

### 4. (Optional) Install Tesseract
If using Tesseract OCR engine:
- Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
- Linux: `sudo apt-get install tesseract-ocr`
- Mac: `brew install tesseract`

## 🎮 Running the API

### Development Server
```bash
python -m app.main
```

### Production Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at `http://localhost:8000`

## 📡 API Endpoints

### 1. Upload Document
**POST** `/api/upload`

Upload a PDF document (bank statement or payslip). The system will automatically detect the type.

### 2. Check Status
**GET** `/api/status/{upload_id}`

### 3. Get Results
**GET** `/api/result/{upload_id}`

Retrieve extraction results.

**Response (Bank Statement):**
**Response (Payslip):**

### 4. Health Check
**GET** `/health`
Check API health status.

## 🔧 Configuration

### OCR Engine Selection
Edit `.env` file:
```env
OCR_ENGINE=paddleocr
# Options: paddleocr, easyocr, tesseract
```

### Language Configuration
```env
OCR_LANGUAGE=en
# Options: en (English), ms (Malay), ch (Chinese)
```

### Supported Banks
- CIMB Bank
- Bank Islam
- BSN (Bank Simpanan Nasional)
- Public Islamic Bank
- Generic bank statements

## 📁 Project Structure

```
unified-document-extractor/
├── app/
│   ├── api/
│   │   ├── routes.py          # API endpoints
│   │   └── schemas.py         # Pydantic models
│   ├── config.py              # Configuration
│   └── main.py                # FastAPI app
├── core/
│   ├── document_classifier.py # Auto document type detection
│   ├── unified_pipeline.py    # Main processing pipeline
│   ├── ocr_engine.py          # OCR engines
│   ├── pdfplumber_engine.py   # PDF text extraction
│   ├── bank_detector.py       # Bank type detection
│   └── validators.py          # Data validation
├── extractors/
│   ├── bank_statement_extractor.py  # Bank statement logic
│   └── payslip_extractor.py         # Payslip logic
├── utils/
│   ├── pdf_processor.py       # PDF to image conversion
│   ├── text_cleaner.py        # Text preprocessing
│   └── logger.py              # Logging setup
├── config/
│   ├── extraction_config.json        # Bank statement patterns
│   ├── payslip_extraction_config.json # Payslip patterns
│   ├── bank_specific_config.json     # Bank-specific rules
│   └── ocr_config.json               # OCR settings
├── uploads/                   # Uploaded files
├── output/                    # Extraction results
├── requirements.txt
├── .env.example
└── README.md
```

## 🧪 Testing

### Using cURL
```bash
# Upload document
curl -X POST "http://localhost:8000/api/upload" \
  -F "file=@test_document.pdf"

# Get result
curl "http://localhost:8000/api/result/{upload_id}"
```

### Using Postman
Import the Postman collection (if available) or use the API documentation at `http://localhost:8000/docs`

## 🎨 API Documentation

Interactive API documentation available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🐛 Troubleshooting

### PaddleOCR Issues
```bash
# Clear cache
rm -rf ~/.paddleocr

# Reinstall
pip install --upgrade paddleocr
```

### Memory Issues
- Reduce DPI in config files
- Use EasyOCR instead of PaddleOCR
- Process smaller PDFs

### Tesseract Not Found
- Install Tesseract OCR
- Update path in `app/main.py`

## 📊 Performance

| Document Type | Digital PDF | Scanned PDF |
|--------------|-------------|-------------|
| Bank Statement | 1-2 seconds | 15-20 seconds |
| Payslip | 1-2 seconds | 10-15 seconds |

## 🔐 Security Considerations

- Validate file types before processing
- Limit file upload size (default: 10MB)
- Sanitize file names
- Use HTTPS in production
- Implement authentication/authorization
- Regular security audits

## 🚧 Future Enhancements

- [ ] Database integration for result storage
- [ ] Webhook notifications
- [ ] Batch processing
- [ ] Table extraction from statements
- [ ] Transaction-level data extraction
- [ ] Multi-language UI
- [ ] Docker containerization
- [ ] API authentication

## 📝 License

MIT License

## 👥 Support

For issues or questions, please create an issue in the repository.

## 🙏 Acknowledgments

- PaddleOCR for OCR capabilities
- FastAPI for the web framework
- PDFPlumber for PDF text extraction
