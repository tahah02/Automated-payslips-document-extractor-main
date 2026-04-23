import logging
import json
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path

from core.document_classifier import DocumentClassifier
from core.ocr_engine import get_ocr_engine
from core.pdfplumber_engine import PDFPlumberEngine
from core.config import get_config
from extractors.bank_statement_extractor import FieldExtractor
from extractors.payslip_extractor import PayslipExtractor
from utils.pdf_processor import PDFProcessor
from utils.text_cleaner import TextCleaner

logger = logging.getLogger(__name__)


class UnifiedExtractionPipeline:
    
    
    def __init__(self, ocr_engine: str = "paddleocr", ocr_language: str = "en"):
        
        self.classifier = DocumentClassifier()
        self.pdfplumber_engine = PDFPlumberEngine()
        self.text_cleaner = TextCleaner()
        
        self.bank_extractor = FieldExtractor()
        self.payslip_extractor = PayslipExtractor()
        
        self.ocr_engine_name = ocr_engine
        self.ocr_language = ocr_language
        self.ocr_engine = None
        
        logger.info(f"Unified pipeline initialized (OCR: {ocr_engine}, Language: {ocr_language})")
    
    def process(self, upload_id: str, file_path: str) -> Dict[str, Any]:
        
        try:
            logger.info(f"Starting unified processing for {upload_id}")
            
            use_pdfplumber = self.pdfplumber_engine.can_extract_text(file_path)
            
            if use_pdfplumber:
                logger.info("Digital PDF detected - using PDFPlumber")
                return self._process_with_pdfplumber(upload_id, file_path)
            else:
                logger.info("Scanned PDF detected - using OCR")
                return self._process_with_ocr(upload_id, file_path)
        
        except Exception as e:
            logger.error(f"Processing error for {upload_id}: {str(e)}")
            raise
    
    def _process_with_pdfplumber(self, upload_id: str, file_path: str) -> Dict[str, Any]:
        
        try:
            full_text, tokens = self.pdfplumber_engine.extract_text_from_pdf(file_path)
            full_text = self.text_cleaner.clean_text(full_text)
            
            logger.info(f"Extracted {len(full_text)} characters using PDFPlumber")
            
            doc_type, classification_confidence = self.classifier.classify(full_text)
            logger.info(f"Document classified as: {doc_type} (confidence: {classification_confidence})")
            
            if doc_type == "payslip":
                import pdfplumber
                with pdfplumber.open(file_path) as pdf:
                    page = pdf.pages[0] if len(pdf.pages) > 0 else None
                    extracted_data = self.payslip_extractor.extract_payslip_fields(full_text, tokens=tokens, page=page)
                    confidence = self.payslip_extractor.calculate_confidence(extracted_data)
            elif doc_type == "bank_statement":
                extracted_data = self.bank_extractor.extract_bank_statement_fields(full_text, tokens)
                confidence = self.bank_extractor.calculate_confidence(extracted_data)
            else:
                raise ValueError(f"Unknown document type: {doc_type}")
            
            logger.info(f"Extraction confidence: {confidence}")
            
            result = {
                "upload_id": upload_id,
                "file_type": "pdf",
                "document_type": doc_type,
                "classification_confidence": classification_confidence,
                "extraction_method": "pdfplumber",
                "total_documents": 1,
                "documents": [{
                    "document_number": 1,
                    "document_type": doc_type,
                    "extracted_data": extracted_data,
                    "confidence_score": confidence,
                    "text_length": len(full_text)
                }],
                "summary": {
                    doc_type + "s": 1,
                    "other": 0,
                    "average_confidence": round(confidence, 2)
                },
                "processing_completed_at": datetime.now().isoformat(),
                "original_file": f"raw/{upload_id}.pdf",
                "total_text_length": len(full_text)
            }
            
            logger.info(f"PDFPlumber processing completed for {upload_id}")
            return result
        
        except Exception as e:
            logger.error(f"PDFPlumber processing failed: {str(e)}")
            raise
    
    def _process_with_ocr(self, upload_id: str, file_path: str) -> Dict[str, Any]:
        
        try:
            if self.ocr_engine is None:
                self.ocr_engine = get_ocr_engine(self.ocr_engine_name, self.ocr_language)
            
            from core.scanned_pdf_optimizer import ScannedPDFOptimizer
            optimizer = ScannedPDFOptimizer()
            
            processed_dir = f"uploads/processed/{upload_id}"
            Path(processed_dir).mkdir(parents=True, exist_ok=True)
            
            from core.config import load_json, PREPROCESSING_CONFIG_FILE
            preprocessing_config = load_json(PREPROCESSING_CONFIG_FILE)
            
            # Load DPI and zoom from preprocessing config
            base_dpi = preprocessing_config.get('preprocessing', {}).get('image_conversion', {}).get('dpi', 300)
            zoom = preprocessing_config.get('preprocessing', {}).get('image_conversion', {}).get('zoom', 3.0)
            
            images = PDFProcessor.pdf_to_images(file_path, processed_dir, dpi=base_dpi, zoom=zoom)
            logger.info(f"Converted {len(images)} pages to images (DPI: {base_dpi}, Zoom: {zoom})")
            
            documents = []
            total_text_length = 0
            confidence_scores = []
            doc_type = None
            classification_confidence = None
            
            for doc_num, image_path in enumerate(images, 1):
                logger.info(f"Processing page {doc_num}/{len(images)}")
                
                # Optimize image for better OCR
                optimized_image = optimizer.optimize_image(image_path, adaptive=True)
                
                if optimized_image is not None:
                    # Save optimized image temporarily
                    optimized_path = image_path.replace('.png', '_optimized.png')
                    optimizer.save_optimized_image(optimized_image, optimized_path)
                    ocr_image_path = optimized_path
                    logger.info(f"Using optimized image for OCR")
                else:
                    ocr_image_path = image_path
                    logger.warning(f"Optimization failed, using original image")
                
                text = self.ocr_engine.extract_text(ocr_image_path)
                tokens = self.ocr_engine.extract_tokens(ocr_image_path, page=doc_num-1)
                text = self.text_cleaner.clean_text(text)
                
                logger.info(f"=== OCR EXTRACTED TEXT (Page {doc_num}) ===")
                logger.info(f"{text[:500]}...")  # Log first 500 chars only
                logger.info(f"=== END OCR TEXT ===")
                
                total_text_length += len(text)
                logger.info(f"Extracted {len(text)} characters from page {doc_num}")
                
                if doc_num == 1:
                    doc_type, classification_confidence = self.classifier.classify(text)
                    logger.info(f"Document classified as: {doc_type} (confidence: {classification_confidence})")
                
                if doc_type == "bank_statement":
                    extracted_data = self.bank_extractor.extract_bank_statement_fields(text, tokens)
                    confidence = self.bank_extractor.calculate_confidence(extracted_data)
                elif doc_type == "payslip":
                    extracted_data = self.payslip_extractor.extract_payslip_fields(text, tokens)
                    confidence = self.payslip_extractor.calculate_confidence(extracted_data)
                else:
                    raise ValueError(f"Unknown document type: {doc_type}")
                
                confidence_scores.append(confidence)
                
                documents.append({
                    "document_number": doc_num,
                    "document_type": doc_type,
                    "extracted_data": extracted_data,
                    "confidence_score": confidence,
                    "text_length": len(text)
                })
            
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
            
            result = {
                "upload_id": upload_id,
                "file_type": "pdf",
                "document_type": doc_type,
                "classification_confidence": classification_confidence,
                "extraction_method": self.ocr_engine_name,
                "total_documents": len(documents),
                "documents": documents,
                "summary": {
                    doc_type + "s": len(documents),
                    "other": 0,
                    "average_confidence": round(avg_confidence, 2)
                },
                "processing_completed_at": datetime.now().isoformat(),
                "original_file": f"raw/{upload_id}.pdf",
                "total_text_length": total_text_length
            }
            
            logger.info(f"OCR processing completed for {upload_id}")
            return result
        
        except Exception as e:
            logger.error(f"OCR processing failed: {str(e)}")
            raise
    
    def save_result(self, upload_id: str, result: Dict[str, Any]):
        
        try:
            output_dir = Path("output/json")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            result_path = output_dir / f"{upload_id}.json"
            with open(result_path, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            
            logger.info(f"Result saved to {result_path}")
        except Exception as e:
            logger.error(f"Error saving result: {str(e)}")
            raise
