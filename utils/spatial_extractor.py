import logging
import re
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class SpatialExtractor:
    
    def __init__(self):
        self.tolerance_y = 10
        self.tolerance_x = 5
    
    def extract_field_by_position(self, page, label_text: str, search_direction: str = "right") -> Optional[str]:
        """Extract field value by position. Works with both PDFPlumber and PyMuPDF pages."""
        try:
            # Try simple text-based extraction first (works for both)
            if hasattr(page, 'extract_text'):
                # PDFPlumber page
                text = page.extract_text()
            elif hasattr(page, 'get_text'):
                # PyMuPDF page
                text = page.get_text()
            else:
                logger.warning(f"Unknown page type: {type(page)}")
                return None
            
            # For "No KP" - extract the 12-digit number after it (with or without dashes)
            if label_text.lower() in ['no kp', 'no. k/p', 'no ic', 'no. kad']:
                # Try multiple patterns
                patterns = [
                    rf'No\s+KP\s*:?\s*(\d{{12}})',  # No KP : 610614045225
                    rf'No\s+KP\s*:?\s*(\d{{6}}-\d{{2}}-\d{{4}})',  # No KP : 610614-04-5225
                    rf'No\.?\s*K/?P\s*:?\s*(\d{{12}})',  # No. K/P : 610614045225
                    rf'No\.?\s*K/?P\s*:?\s*(\d{{6}}-\d{{2}}-\d{{4}})',  # No. K/P : 610614-04-5225
                    rf'No\.\s+Kad\s*:?\s*(\d{{12}})',  # No. Kad : 750203125544
                    rf'No\.\s+Kad\s*:?\s*(\d{{6}}-\d{{2}}-\d{{4}})',  # No. Kad : 750203-12-5544
                ]
                for pattern in patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
                        logger.debug(f"Extracted {label_text}: {value}")
                        return value
            
            # For "Jumlah Pendapatan" - extract the amount (with commas)
            elif 'jumlah pendapatan' in label_text.lower():
                patterns = [
                    r'Jumlah\s+Pendapatan\s+([\d,]+\.[\d]{2})',  # Without colon
                    r'Jumlah\s+Pendapatan\s*:\s*([\d,]+\.[\d]{2})',  # With colon
                ]
                for pattern in patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
                        logger.debug(f"Extracted {label_text}: {value}")
                        return value
            
            # For "Jumlah Potongan" - extract the amount (with commas)
            elif 'jumlah potongan' in label_text.lower():
                patterns = [
                    r'Jumlah\s+Potongan\s+([\d,]+\.[\d]{2})',  # Without colon
                    r'Jumlah\s+Potongan\s*:\s*([\d,]+\.[\d]{2})',  # With colon
                ]
                for pattern in patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
                        logger.debug(f"Extracted {label_text}: {value}")
                        return value
            
            # For "Gaji Bersih" - extract the amount (with commas)
            elif 'gaji bersih' in label_text.lower():
                patterns = [
                    r'Gaji\s+Bersih\s+([\d,]+\.[\d]{2})',  # Without colon
                    r'Gaji\s+Bersih\s*:\s*([\d,]+\.[\d]{2})',  # With colon
                ]
                for pattern in patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
                        logger.debug(f"Extracted {label_text}: {value}")
                        return value
            
            # Generic pattern for other fields
            else:
                pattern = rf'{re.escape(label_text)}\s*:?\s*([^\n]+?)(?:\s+(?:Bulan|No\.|Pejabat|Pusat|Jawatan)|\n|$)'
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    value = value.lstrip(':').strip()
                    if value and len(value) > 0 and not value.startswith('-'):
                        logger.debug(f"Extracted {label_text}: {value}")
                        return value
            
            logger.debug(f"Label not found in text: {label_text}")
            return None
            
        except Exception as e:
            logger.error(f"Spatial extraction error for {label_text}: {str(e)}")
            return None
    
    def _find_value_right(self, text_blocks: List[Dict], label_bbox: tuple) -> Optional[str]:
        candidates = []
        
        for block in text_blocks:
            for line in block.get("lines", []):
                line_bbox = line["bbox"]
                
                if abs(line_bbox[1] - label_bbox[1]) < self.tolerance_y:
                    if line_bbox[0] > label_bbox[2] + self.tolerance_x:
                        line_text = "".join([span["text"] for span in line.get("spans", [])])
                        candidates.append({
                            "text": line_text,
                            "distance": line_bbox[0] - label_bbox[2]
                        })
        
        if candidates:
            closest = min(candidates, key=lambda x: x["distance"])
            value = closest["text"].strip()
            value = value.lstrip(":").strip()
            return value if value else None
        
        return None
    
    def _find_value_below(self, text_blocks: List[Dict], label_bbox: tuple) -> Optional[str]:
        candidates = []
        
        for block in text_blocks:
            for line in block.get("lines", []):
                line_bbox = line["bbox"]
                
                if line_bbox[1] > label_bbox[3]:
                    if abs(line_bbox[0] - label_bbox[0]) < 50:
                        line_text = "".join([span["text"] for span in line.get("spans", [])])
                        candidates.append({
                            "text": line_text,
                            "distance": line_bbox[1] - label_bbox[3]
                        })
        
        if candidates:
            closest = min(candidates, key=lambda x: x["distance"])
            return closest["text"].strip()
        
        return None
    
    def extract_name_from_page(self, page) -> Optional[str]:
        """Extract name from page. Works with both PDFPlumber and PyMuPDF pages."""
        try:
            # Get text from page
            if hasattr(page, 'extract_text'):
                # PDFPlumber page
                text = page.extract_text()
            elif hasattr(page, 'get_text'):
                # PyMuPDF page
                text = page.get_text()
            else:
                logger.warning(f"Unknown page type: {type(page)}")
                return None
            
            # Specific pattern for "Nama : NAME" format (handles both uppercase and mixed case)
            # Use lookahead to stop before common keywords that follow the name
            name_patterns = [
                r'Nama\s*:\s*([A-Z][A-Z\s]+(?:BIN|BINTI)\s+[A-Z][A-Z\s]+?)(?=\s+(?:Bulan|Jawatan|No\s+Gaji|No\.|Pusat|Pejabat)|\n)',
                r'Nama\s*:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:bin|binti|Bin|Binti)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)(?=\s+(?:Bulan|Jawatan|No\s+Gaji|No\.|Pusat|Pejabat)|\n)',
                r'Nama\s*:\s*([A-Z][A-Z\s]+?)(?=\s+(?:Bulan|Jawatan|No\s+Gaji|No\.|Pusat|Pejabat)|\n)',
            ]
            
            for pattern in name_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    name = match.group(1).strip()
                    # Clean up - remove extra spaces and newlines
                    name = ' '.join(name.split())
                    # Validate name - should not contain these words and should be reasonable length
                    if (name and 5 <= len(name) <= 100 and 
                        not any(word in name.upper() for word in ["PENYATA", "GAJI", "BULANAN", "NAMA", "NO GAJI", "NO SIRI"])):
                        logger.debug(f"Extracted name: {name}")
                        return name
            
            return None
            
        except Exception as e:
            logger.error(f"Name extraction error: {str(e)}")
            return None
    
    def clean_numeric_value(self, value: str) -> Optional[str]:
        """Clean and extract numeric value from text"""
        if not value:
            return None
        
        # Remove all spaces
        cleaned = re.sub(r'\s+', '', value)
        # Remove commas
        cleaned = cleaned.replace(',', '')
        
        # Extract the first number with decimal point (format: digits.digits)
        match = re.search(r'([\d]+\.[\d]{2})', cleaned)
        if match:
            return match.group(1)
        
        # Try without decimal point requirement
        match = re.search(r'([\d]+)', cleaned)
        if match:
            return f"{match.group(1)}.00"
        
        return None
