import re
import logging
import logging
from typing import Optional
from typing import Optional


logger = logging.getLogger(__name__)


class CurrencyFormatter:
   
    
    @staticmethod
    def clean_currency(value: str) -> str:
       
        if not value or not isinstance(value, str):
            return "0.00"
        
        value = value.strip()       
        if not value:
            return "0.00"
       
        comma_count = value.count(",")
        dot_count = value.count(".")        
        if dot_count > 0:
            
            value = value.replace(",", "").replace(" ", "")
        elif comma_count > 0:
            value_no_space = value.replace(" ", "")
            last_comma_pos = value_no_space.rfind(",")
            digits_after_comma = len(value_no_space) - last_comma_pos - 1
            
            if digits_after_comma == 5:
                value = value_no_space.replace(",", "")
             
                if len(value) >= 2:
                    value = value[:-2] + "." + value[-2:]
            elif digits_after_comma == 2:
             
                value = value_no_space.replace(",", "")
            else:
              
                value = value_no_space.replace(",", "")
        else:
            
            value = value.replace(" ", "")
             
        value = re.sub(r"[^\d.]", "", value)
       
        if not value:
            return "0.00"
            
        if value.count(".") > 1:
            parts = value.split(".")
            value = "".join(parts[:-1]) + "." + parts[-1]        
        try:
            numeric_value = float(value)
            return f"{numeric_value:.2f}"
        except ValueError:
            logger.warning(f"Could not convert '{value}' to float, returning 0.00")
            return "0.00"


    @staticmethod
    def clean_id_number(value: str) -> str:
        if not value or not isinstance(value, str):
            return ""   
        digits = re.sub(r"\D", "", value.strip())       
        if len(digits) == 12:
            return f"{digits[:6]}-{digits[6:8]}-{digits[8:12]}"
        
        return value.strip()


    @staticmethod
    def clean_month_year(value: str) -> str:
    
        if not value or not isinstance(value, str):
            return ""
        
        value = value.strip()
        match = re.search(r"(\d{1,2})[/-]?(\d{4})", value)
        
        if match:
            month = int(match.group(1))
            year = match.group(2)

            if 1 <= month <= 12:
                return f"{month:02d}/{year}"
        
        return value


def parse_number(text: str) -> Optional[float]:
    if not text or not isinstance(text, str):
        return None
    
    s = text.strip()
    
    s = re.sub(r"[^\d,.\-\s]", "", s)
    s = s.strip()
    
    if not s:
        return None
    
    if '.' in s and ',' in s:
        s = s.replace(',', '')
    elif ',' in s and re.search(r",\d{1,2}$", s):
        s = s.replace(',', '.')
    elif ',' in s:
        s = s.replace(',', '')
    
    s = s.replace(' ', '')
    
    try:
        return float(s)
    except ValueError:
        logger.debug(f"Could not parse number from: {text}")
        return None


def normalize_nric(s: str) -> Optional[str]:
    if not s or not isinstance(s, str):
        return None
    
    digits = re.sub(r"\D", "", s)
    
    if len(digits) != 12:
        logger.debug(f"NRIC has {len(digits)} digits, expected 12: {s}")
        return None
    
    return f"{digits[:6]}-{digits[6:8]}-{digits[8:]}"


def is_percentage_context(text: str, label: str = "") -> bool:
    if not text:
        return False
    
    text_lower = text.lower()
    label_lower = label.lower() if label else ""
    
    if '%' in text:
        return True
    
    percentage_keywords = ['peratus', 'percentage', 'pct', 'percent', '%']
    
    for keyword in percentage_keywords:
        if keyword in label_lower or keyword in text_lower:
            return True
    
    return False


def is_likely_percentage_value(value: float, context: str = "", label: str = "") -> bool:
    if is_percentage_context(context, label):
        return True
    
    if value < 100 and is_percentage_context(context, label):
        return True
    
    return False
