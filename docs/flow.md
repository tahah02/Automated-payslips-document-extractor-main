Main poora flow step-by-step explain karta hoon with exact code files:

## 📄 Complete PDF Processing Flow

### **Step 1: PDF Upload** 
**File:** `app/api/routes.py`
```
User uploads PDF → POST /api/upload
↓
- File validation (PDF only, max 10MB)
- Generate unique upload_id (UUID)
- Save to uploads/raw/{upload_id}.pdf
- Return upload_id to user
```

---

### **Step 2: Processing Start**
**File:** `app/api/routes.py` → calls → `core/unified_pipeline.py`
```
UnifiedExtractionPipeline.process(upload_id, file_path)
```

---

### **Step 3: Cache Check**
**File:** `core/cache_manager.py`
```
CacheManager.get_cached_result(file_path)
↓
- Calculate SHA256 hash of PDF
- Check cache/cache_index.json
- If found → Return cached result (DONE in 0.1s)
- If not found → Continue processing
```

---

### **Step 4: PDF Type Detection**
**File:** `core/pdfplumber_engine.py`
```
PDFPlumberEngine.can_extract_text(pdf_path)
↓
- Try to extract text from first 3 pages
- If text > 100 chars → Digital PDF
- If text < 100 chars → Scanned PDF
```

---

### **Step 5A: Digital PDF Path (Fast - 1-2 seconds)**
**Files Used:**
1. `core/pdfplumber_engine.py`
2. `utils/text_cleaner.py`

```
PDFPlumberEngine.extract_text_from_pdf()
↓
- Extract all text from PDF
- Extract word coordinates (bounding boxes)
- Create tokens with positions
↓
TextCleaner.clean_text()
↓
- Remove extra whitespace
- Normalize special characters
- Clean text
```

---

### **Step 5B: Scanned PDF Path (Slow - 10-20 seconds)**
**Files Used:**
1. `utils/pdf_processor.py`
2. `core/scanned_pdf_optimizer.py`
3. `core/ocr_engine.py`
4. `utils/text_cleaner.py`

```
Step 5B.1: PDF to Images
PDFProcessor.pdf_to_images()
↓
- Convert PDF pages to PNG images
- DPI: 300, Zoom: 3.0x
- Save to uploads/processed/{upload_id}/page_1.png
↓
Step 5B.2: Image Optimization
ScannedPDFOptimizer.optimize_image()
↓
- Apply CLAHE (contrast enhancement)
- Bilateral filtering (noise reduction)
- Deskew (rotation correction)
- Save optimized image
↓
Step 5B.3: OCR Extraction
OCREngine.extract_text() & extract_tokens()
↓
- Run OCR (PaddleOCR/EasyOCR/Tesseract)
- Extract text with coordinates
- Create tokens with confidence scores
↓
Step 5B.4: Text Cleaning
TextCleaner.clean_text()
```

---

### **Step 6: Document Classification**
**File:** `core/document_classifier.py`
```
DocumentClassifier.classify(text)
↓
- Load keywords from config/document_classification_config.json
- Count bank statement keywords in text
- Count payslip keywords in text
- Compare scores
↓
Result: "bank_statement" or "payslip" + confidence
```

---

### **Step 7A: Bank Statement Processing**
**Files Used:**
1. `core/bank_detector.py`
2. `extractors/bank_statement_extractor.py`
3. `core/layout_analyzer.py`
4. `core/spatial_search.py`
5. `core/number_formatter.py`
6. `core/utils.py`

```
Step 7A.1: Bank Detection
BankDetector.detect(text)
↓
- Search for bank keywords (CIMB, Bank Islam, BSN, etc.)
- Return bank type + confidence
↓
Step 7A.2: Field Extraction
FieldExtractor.extract_bank_statement_fields()
↓
Uses:
- config/extraction_config.json (patterns)
- config/bank_specific_config.json (bank rules)
↓
Extracts:
- Account holder name
- Account number
- Opening balance
- Closing balance
- Total debit/credit
- Statement dates
↓
Methods used:
- Regex pattern matching
- Spatial search (LayoutAnalyzer + SpatialSearch)
- Bank-specific rules
- NumberFormatter for currency values
↓
Step 7A.3: Validation
- Check numeric ranges
- Validate date formats
- Calculate confidence score
```

---

### **Step 7B: Payslip Processing**
**Files Used:**
1. `extractors/payslip_extractor.py`
2. `utils/spatial_extractor.py`
3. `core/utils.py`

```
Step 7B.1: Field Extraction
PayslipExtractor.extract_payslip_fields()
↓
Uses:
- config/payslip_extraction_config.json (patterns)
↓
Two extraction methods:

Method 1: Spatial Extraction (if page object available)
SpatialExtractor.extract_field_by_position()
↓
- Find "Nama" → extract name to the right
- Find "No K/P" → extract ID to the right
- Find "Jumlah Pendapatan" → extract gross income
- Find "Jumlah Potongan" → extract deductions
- Find "Gaji Bersih" → extract net income

Method 2: Regex Extraction (fallback)
_extract_payslip_with_regex()
↓
- Use regex patterns for each field
- Extract name, ID, amounts, dates
↓
Step 7B.2: Calculation
- If net income missing: gross - deductions = net
- If deduction missing: gross - net = deduction
↓
Step 7B.3: Validation
_validate_extracted_data()
↓
- Check: gross >= net
- Check: gross - deduction = net (with tolerance)
- Check: month (1-12), year (2000-2099)
- Check: no negative values
- Calculate confidence score
```

---

### **Step 8: Result Formatting**
**File:** `core/unified_pipeline.py`
```
Create result JSON:
{
  "upload_id": "...",
  "document_type": "payslip" or "bank_statement",
  "extraction_method": "pdfplumber" or "easyocr",
  "documents": [
    {
      "document_number": 1,
      "extracted_data": { ... },
      "confidence_score": 0.95
    }
  ],
  "processing_completed_at": "2026-04-30T...",
  "total_text_length": 610
}
```

---

### **Step 9: Cache Save**
**File:** `core/cache_manager.py`
```
CacheManager.save_result_to_cache()
↓
- Calculate SHA256 hash of PDF
- Save result to cache/{hash}.json
- Update cache/cache_index.json
- Next time same PDF → instant result!
```

---

### **Step 10: Save to Output**
**File:** `core/unified_pipeline.py`
```
save_result()
↓
- Save to output/json/{upload_id}.json
```

---

### **Step 11: Return to API**
**File:** `app/api/routes.py`
```
Return JSON response to user
```

---

## 📊 Summary - Files Used in Order:

### **Every Request:**
1. `app/api/routes.py` - Entry point
2. `core/unified_pipeline.py` - Orchestrator
3. `core/cache_manager.py` - Cache check
4. `core/pdfplumber_engine.py` - PDF type detection

### **Digital PDF Path:**
5. `core/pdfplumber_engine.py` - Text extraction
6. `utils/text_cleaner.py` - Text cleaning

### **Scanned PDF Path:**
5. `utils/pdf_processor.py` - PDF to images
6. `core/scanned_pdf_optimizer.py` - Image optimization
7. `core/ocr_engine.py` - OCR extraction
8. `utils/text_cleaner.py` - Text cleaning

### **Classification:**
9. `core/document_classifier.py` - Document type detection

### **Bank Statement Extraction:**
10. `core/bank_detector.py` - Bank identification
11. `extractors/bank_statement_extractor.py` - Field extraction
12. `core/layout_analyzer.py` - Layout analysis
13. `core/spatial_search.py` - Spatial search
14. `core/number_formatter.py` - Number formatting
15. `core/utils.py` - Utilities

### **Payslip Extraction:**
10. `extractors/payslip_extractor.py` - Field extraction
11. `utils/spatial_extractor.py` - Spatial extraction
12. `core/utils.py` - Utilities

### **Final Steps:**
13. `core/cache_manager.py` - Save to cache
14. `core/unified_pipeline.py` - Save result
15. `app/api/routes.py` - Return response

---

## ⏱️ Time Breakdown:

**Digital PDF (Total: ~2 seconds)**
- Upload: 0.1s
- Cache check: 0.05s
- PDFPlumber: 0.5s
- Classification: 0.2s
- Extraction: 0.5s
- Validation: 0.2s
- Cache save: 0.1s
- Return: 0.05s

**Scanned PDF (Total: ~15 seconds)**
- Upload: 0.1s
- Cache check: 0.05s
- PDF to images: 2s
- Image optimization: 1s
- OCR: 10s
- Classification: 0.2s
- Extraction: 0.5s
- Validation: 0.2s
- Cache save: 0.1s
- Return: 0.05s

**Cached Result (Total: ~0.25 seconds)**
- Upload: 0.1s
- Cache check: 0.05s
- Cache hit: 0.05s
- Return: 0.05s

Yeh hai complete flow! 🚀