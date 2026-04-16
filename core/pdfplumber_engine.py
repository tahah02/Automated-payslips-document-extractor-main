import logging
from typing import List, Dict, Any, Tuple, Optional
import pdfplumber
from pathlib import Path

logger = logging.getLogger(__name__)

class PDFPlumberEngine:
    
    def __init__(self):
        self.min_text_threshold = 100
        logger.info("PDFPlumber engine initialized")
    
    def can_extract_text(self, pdf_path: str) -> bool:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_text = ""
                for page in pdf.pages[:3]:
                    text = page.extract_text()
                    if text:
                        total_text += text
                    if len(total_text) > self.min_text_threshold:
                        return True
                
                return len(total_text) > self.min_text_threshold
        except Exception as e:
            logger.error(f"Error checking PDF text extractability: {str(e)}")
            return False
    
    def extract_text_from_pdf(self, pdf_path: str) -> Tuple[str, List[Dict[str, Any]]]:
        try:
            all_text = []
            all_tokens = []
            
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text:
                        all_text.append(page_text)
                    
                    words = page.extract_words()
                    for word in words:
                        token = {
                            'text': word['text'],
                            'bbox': [word['x0'], word['top'], word['x1'], word['bottom']],
                            'x0': word['x0'],
                            'y0': word['top'],
                            'x1': word['x1'],
                            'y1': word['bottom'],
                            'confidence': 1.0,
                            'page': page_num,
                            'engine': 'pdfplumber',
                            '_used_by': None
                        }
                        all_tokens.append(token)
            
            full_text = "\n\n".join(all_text)
            logger.info(f"Extracted {len(full_text)} characters and {len(all_tokens)} tokens from PDF")
            
            return full_text, all_tokens
            
        except Exception as e:
            logger.error(f"PDFPlumber extraction error: {str(e)}")
            raise
    
    def extract_tables_from_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        try:
            all_tables = []
            
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    tables = page.extract_tables()
                    for table_idx, table in enumerate(tables):
                        all_tables.append({
                            'page': page_num,
                            'table_index': table_idx,
                            'data': table
                        })
            
            logger.info(f"Extracted {len(all_tables)} tables from PDF")
            return all_tables
            
        except Exception as e:
            logger.error(f"Table extraction error: {str(e)}")
            return []
