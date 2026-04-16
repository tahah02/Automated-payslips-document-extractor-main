import re
import logging


logger = logging.getLogger(__name__)

class TextCleaner:
    
    @staticmethod
    def clean_text(text: str) -> str:
        if not text:
            return ""
        
        text = re.sub(r'\s+', ' ', text)
        
        text = re.sub(r'[^\w\s\-./,:]', '', text)
        
        text = text.strip()
        
        return text
    
    @staticmethod
    def normalize_currency(value: str) -> str:
        if not value:
            return ""
        
        value = value.replace(" ", "")
        
        value = re.sub(r'[^\d,.]', '', value)
        
        return value
    
    @staticmethod
    def normalize_id_number(id_number: str) -> str:
        if not id_number:
            return ""
        
        digits = re.sub(r'\D', '', id_number)
        
        if len(digits) == 12:
            return f"{digits[:6]}-{digits[6:8]}-{digits[8:]}"
        
        return id_number
    
    @staticmethod
    def normalize_date(date_str: str, format_type: str = "dd/mm/yyyy") -> str:
        if not date_str:
            return ""
        
        digits = re.findall(r'\d+', date_str)
        
        if format_type == "mm/yyyy" and len(digits) >= 2:
            return f"{digits[0]}/{digits[1]}"
        elif format_type == "dd/mm/yyyy" and len(digits) >= 3:
            return f"{digits[0]}/{digits[1]}/{digits[2]}"
        
        return date_str
    
    @staticmethod
    def extract_lines(text: str) -> list:
        lines = text.split('\n')
        return [line.strip() for line in lines if line.strip()]
