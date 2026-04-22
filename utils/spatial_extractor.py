import logging
import re
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class SpatialExtractor:
    
    def __init__(self):
        self.tolerance_y = 10
        self.tolerance_x = 5
    
    def extract_field_by_position(self, page, label_text: str, search_direction: str = "right") -> Optional[str]:
        try:
            if hasattr(page, 'extract_text'):
                text = page.extract_text()
            elif hasattr(page, 'get_text'):
                text = page.get_text()
            else:
                logger.warning(f"Unknown page type: {type(page)}")
                return None
            
            if label_text.lower() in ['no kp', 'no. k/p', 'no ic', 'no. kad']:
                patterns = [
                    rf'No\s+KP\s*:?\s*(\d{{12}})',
                    rf'No\s+KP\s*:?\s*(\d{{6}}-\d{{2}}-\d{{4}})',
                    rf'No\.?\s*K/?P\s*:?\s*(\d{{12}})',
                    rf'No\.?\s*K/?P\s*:?\s*(\d{{6}}-\d{{2}}-\d{{4}})',
                    rf'No\.\s+Kad\s*:?\s*(\d{{12}})',
                    rf'No\.\s+Kad\s*:?\s*(\d{{6}}-\d{{2}}-\d{{4}})',
                ]
                for pattern in patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
                        logger.debug(f"Extracted {label_text}: {value}")
                        return value
            
            elif 'jumlah pendapatan' in label_text.lower():
                patterns = [
                    r'Jumlah\s+Pendapatan\s+([\d,]+\.[\d]{2})',
                    r'Jumlah\s+Pendapatan\s*:\s*([\d,]+\.[\d]{2})',
                ]
                for pattern in patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
                        logger.debug(f"Extracted {label_text}: {value}")
                        return value
            
            elif 'jumlah potongan' in label_text.lower():
                patterns = [
                    r'Jumlah\s+Potongan\s+([\d,]+\.[\d]{2})',
                    r'Jumlah\s+Potongan\s*:\s*([\d,]+\.[\d]{2})',
                ]
                for pattern in patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
                        logger.debug(f"Extracted {label_text}: {value}")
                        return value
            
            elif 'gaji bersih' in label_text.lower():
                patterns = [
                    r'Gaji\s+Bersih\s+([\d,]+\.[\d]{2})',
                    r'Gaji\s+Bersih\s*:\s*([\d,]+\.[\d]{2})',
                ]
                for pattern in patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
                        logger.debug(f"Extracted {label_text}: {value}")
                        return value
            
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
        try:
            if hasattr(page, 'extract_text'):
                text = page.extract_text()
            elif hasattr(page, 'get_text'):
                text = page.get_text()
            else:
                logger.warning(f"Unknown page type: {type(page)}")
                return None
            
            name_patterns = [
                r'Nama\s*:\s*([A-Z][A-Z\s]+(?:BIN|BINTI)\s+[A-Z][A-Z\s]+?)(?=\s+(?:Bulan|Jawatan|No\s+Gaji|No\.|Pusat|Pejabat)|\n)',
                r'Nama\s*:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:bin|binti|Bin|Binti)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)(?=\s+(?:Bulan|Jawatan|No\s+Gaji|No\.|Pusat|Pejabat)|\n)',
                r'Nama\s*:\s*([A-Z][A-Z\s]+?)(?=\s+(?:Bulan|Jawatan|No\s+Gaji|No\.|Pusat|Pejabat)|\n)',
            ]
            
            for pattern in name_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    name = match.group(1).strip()
                    name = ' '.join(name.split())
                    if (name and 5 <= len(name) <= 100 and 
                        not any(word in name.upper() for word in ["PENYATA", "GAJI", "BULANAN", "NAMA", "NO GAJI", "NO SIRI"])):
                        logger.debug(f"Extracted name: {name}")
                        return name
            
            return None
            
        except Exception as e:
            logger.error(f"Name extraction error: {str(e)}")
            return None
    
    def clean_numeric_value(self, value: str) -> Optional[str]:
        if not value:
            return None
        
        cleaned = re.sub(r'\s+', '', value)
        cleaned = cleaned.replace(',', '')
        
        match = re.search(r'([\d]+\.[\d]{2})', cleaned)
        if match:
            return match.group(1)
        
        match = re.search(r'([\d]+)', cleaned)
        if match:
            return f"{match.group(1)}.00"
        
        return None
