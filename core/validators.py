import logging
import re
import re
from typing import Dict, Any, Tuple
from typing import Dict, Any, Tuple
from core.config import get_validation_config
from core.config import get_validation_config


logger = logging.getLogger(__name__)

class DataValidator:
    
    @staticmethod
    def validate_bank_statement(data: Dict[str, Any], template: str = None) -> Tuple[bool, str]:
        try:
            required_fields = ["account_holder_name", "account_number", "statement_date", "opening_balance", "closing_balance"]
            missing_fields = [f for f in required_fields if not data.get(f)]
            
            if missing_fields:
                return False, f"Missing fields: {', '.join(missing_fields)}"
            
            if not DataValidator._validate_account_number(data["account_number"], template):
                return False, "Invalid account number format"
            
            if not DataValidator._validate_date(data["statement_date"], template):
                return False, "Invalid statement date format"
            
            if not DataValidator._validate_currency(data["opening_balance"], template):
                return False, "Invalid opening balance format"
            
            if not DataValidator._validate_currency(data["closing_balance"], template):
                return False, "Invalid closing balance format"
            
            return True, "Valid bank statement data"
        
        except Exception as e:
            logger.error(f"Bank statement validation error: {str(e)}")
            return False, str(e)
    
    @staticmethod
    def _validate_id_number(id_number: str, template: str = None) -> bool:
        config = get_validation_config(template)
        pattern = config.get("id_number_pattern", r"^\d{6}-\d{2}-\d{4}$")
        return bool(re.match(pattern, id_number.strip()))
    
    @staticmethod
    def _validate_currency(value: str, template: str = None) -> bool:
        config = get_validation_config(template)
        cleaned = value.replace(",", "").strip()
        pattern = config.get("currency_pattern", r"^\d+\.\d{2}$")
        return bool(re.match(pattern, cleaned))
    
    @staticmethod
    def _validate_month_year(value: str, template: str = None) -> bool:
        config = get_validation_config(template)
        pattern = config.get("month_year_pattern", r"^\d{2}/\d{4}$")
        if not re.match(pattern, value.strip()):
            return False
        
        date_range = config.get("date_range", {})
        month = int(value.split("/")[0])
        min_month = date_range.get("min_month", 1)
        max_month = date_range.get("max_month", 12)
        return min_month <= month <= max_month
    
    @staticmethod
    def _validate_account_number(account_number: str, template: str = None) -> bool:
        config = get_validation_config(template)
        pattern = config.get("account_number_pattern", r"^\d{2}-\d{7}-\d$")
        return bool(re.match(pattern, account_number.strip()))
    
    @staticmethod
    def _validate_date(date_str: str, template: str = None) -> bool:
        config = get_validation_config(template)
        pattern = config.get("date_pattern", r"^\d{2}/\d{2}/\d{4}$")
        if not re.match(pattern, date_str.strip()):
            return False
        
        date_range = config.get("date_range", {})
        day, month, year = date_str.split("/")
        day, month, year = int(day), int(month), int(year)
        
        min_day = date_range.get("min_day", 1)
        max_day = date_range.get("max_day", 31)
        min_month = date_range.get("min_month", 1)
        max_month = date_range.get("max_month", 12)
        min_year = date_range.get("min_year", 1900)
        max_year = date_range.get("max_year", 2100)
        
        return (min_day <= day <= max_day and 
                min_month <= month <= max_month and 
                min_year <= year <= max_year)
