import logging
import re
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from utils.spatial_extractor import SpatialExtractor

logger = logging.getLogger(__name__)


class PayslipExtractor:
    def __init__(self, config_path: str = "config/payslip_extraction_config.json"):
        self.config = self._load_config(config_path)
        self.used_tokens = set()
        self.payslip_config = self.config.get("extraction", {}).get("fields", {})
        self.spatial_extractor = SpatialExtractor()
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        try:
            if Path(config_path).exists():
                with open(config_path, 'r') as f:
                    return json.load(f)
            else:
                logger.warning(f"Config file not found: {config_path}, using defaults")
                return {}
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            return {}
    
    def extract_payslip_fields(self, text: str, tokens: List[Dict[str, Any]] = None, page=None) -> Dict[str, Any]:
        self.used_tokens = set()
        
        if page:
            extracted = self._extract_with_spatial(page, text)
        else:
            extracted = self._extract_payslip_with_regex(text)
        
        extracted = self._validate_extracted_data(extracted)
        return extracted
    
    def _extract_with_spatial(self, page, text: str) -> Dict[str, Any]:
        extracted = {}
        
        # Try spatial extraction for name
        extracted["name"] = self.spatial_extractor.extract_name_from_page(page)
        logger.info(f"Name from spatial: {extracted['name']}")
        if not extracted["name"]:
            extracted["name"] = self._extract_field(text, "name")
            logger.info(f"Name from regex: {extracted['name']}")
        
        # Clean name - remove trailing newline and text after it
        if extracted["name"]:
            extracted["name"] = extracted["name"].split('\n')[0].strip()
        
        # Try spatial extraction for ID
        id_spatial = self.spatial_extractor.extract_field_by_position(page, "No. K/P", "right")
        if not id_spatial:
            id_spatial = self.spatial_extractor.extract_field_by_position(page, "No KP", "right")
        logger.info(f"ID from spatial: {id_spatial}")
        extracted["id_number"] = id_spatial if id_spatial else self._extract_field(text, "id_number")
        logger.info(f"Final ID: {extracted['id_number']}")
        
        # Try spatial extraction for gross income
        gross_spatial = self.spatial_extractor.extract_field_by_position(page, "Jumlah Pendapatan", "right")
        logger.info(f"Gross from spatial (raw): {gross_spatial}")
        if gross_spatial:
            gross_cleaned = self.spatial_extractor.clean_numeric_value(gross_spatial)
            logger.info(f"Gross cleaned: {gross_cleaned}")
            extracted["gross_income"] = gross_cleaned if gross_cleaned else self._extract_currency_field(text, "gross_income")
        else:
            extracted["gross_income"] = self._extract_currency_field(text, "gross_income")
        logger.info(f"Final gross: {extracted['gross_income']}")
        
        # Try spatial extraction for deduction
        deduction_spatial = self.spatial_extractor.extract_field_by_position(page, "Jumlah Potongan", "right")
        if deduction_spatial:
            deduction_cleaned = self.spatial_extractor.clean_numeric_value(deduction_spatial)
            extracted["total_deduction"] = deduction_cleaned if deduction_cleaned else self._extract_currency_field(text, "total_deduction")
        else:
            extracted["total_deduction"] = self._extract_currency_field(text, "total_deduction")
        
        # If spatial extraction failed, calculate from items
        if not extracted["total_deduction"] or extracted["total_deduction"] == "0.00":
            calculated_deduction = self._calculate_total_deduction(text)
            if calculated_deduction:
                extracted["total_deduction"] = calculated_deduction
        
        # Try spatial extraction for net income
        net_spatial = self.spatial_extractor.extract_field_by_position(page, "Gaji Bersih", "right")
        if net_spatial:
            net_cleaned = self.spatial_extractor.clean_numeric_value(net_spatial)
            extracted["net_income"] = net_cleaned if net_cleaned else self._extract_currency_field(text, "net_income")
        else:
            extracted["net_income"] = self._extract_currency_field(text, "net_income")
        
        # Extract month/year
        extracted["month_year"] = self._extract_field(text, "month_year")
        
        # Clean currency values
        extracted["gross_income"] = self._clean_currency(extracted.get("gross_income"))
        extracted["total_deduction"] = self._clean_currency(extracted.get("total_deduction"))
        extracted["net_income"] = self._clean_currency(extracted.get("net_income"))
        
        # Calculate net income if needed
        net_income_cleaned = extracted["net_income"]
        if net_income_cleaned == "0.00" or not extracted["net_income"]:
            try:
                gross = float(extracted["gross_income"])
                deduction = float(extracted["total_deduction"])
                calculated_net = gross - deduction
                extracted["net_income"] = f"{calculated_net:.2f}"
                logger.info(f"Calculated net_income: {extracted['net_income']}")
            except (ValueError, TypeError) as e:
                logger.warning(f"Could not calculate net_income: {str(e)}")
                extracted["net_income"] = net_income_cleaned
        
        # Log what was extracted
        logger.info(f"Spatial extraction results: name={bool(extracted['name'])}, id={bool(extracted['id_number'])}, gross={extracted['gross_income']}, deduction={extracted['total_deduction']}, net={extracted['net_income']}")
        
        return extracted
    
    def _extract_payslip_with_regex(self, text: str) -> Dict[str, Any]:
        self.used_tokens = set()
        
        extracted_name = self._extract_field(text, "name")
        extracted_id = self._extract_field(text, "id_number")
        
        # Extract in order: gross -> deduction -> net (to avoid token conflicts)
        extracted_gross = self._extract_currency_field(text, "gross_income")
        logger.info(f"Extracted gross_income: {extracted_gross}")
        
        extracted_deduction = self._extract_currency_field(text, "total_deduction")
        logger.info(f"Extracted total_deduction: {extracted_deduction}")
        
        if not extracted_deduction:
            calculated_deduction = self._calculate_total_deduction(text)
            if calculated_deduction:
                logger.info(f"Using calculated deduction from items: {calculated_deduction}")
                extracted_deduction = calculated_deduction
        
        extracted_net = self._extract_currency_field(text, "net_income")
        logger.info(f"Extracted net_income: {extracted_net}")
        
        extracted_month_year = self._extract_field(text, "month_year")
        
        extracted = {
            "name": extracted_name,
            "id_number": extracted_id,
            "gross_income": self._clean_currency(extracted_gross),
            "net_income": self._clean_currency(extracted_net),
            "total_deduction": self._clean_currency(extracted_deduction),
            "month_year": extracted_month_year
        }
        
        net_income_cleaned = self._clean_currency(extracted["net_income"])
        if net_income_cleaned == "0.00" or not extracted["net_income"]:
            try:
                gross = float(extracted["gross_income"])
                deduction = float(extracted["total_deduction"])
                calculated_net = gross - deduction
                extracted["net_income"] = f"{calculated_net:.2f}"
                logger.info(f"Calculated net_income: {extracted['net_income']}")
            except (ValueError, TypeError) as e:
                logger.warning(f"Could not calculate net_income: {str(e)}")
                extracted["net_income"] = net_income_cleaned
        else:
            extracted["net_income"] = net_income_cleaned
        
        return extracted
    
    def _validate_extracted_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        errors = []
        
        try:
            gross = float(data.get("gross_income", 0))
            if gross < 0:
                errors.append("Gross income cannot be negative")
            if gross > 999999.99:
                errors.append("Gross income exceeds maximum (999999.99)")
        except (ValueError, TypeError):
            pass
        
        try:
            net = float(data.get("net_income", 0))
            if net < 0:
                errors.append("Net income cannot be negative")
            if net > 999999.99:
                errors.append("Net income exceeds maximum (999999.99)")
        except (ValueError, TypeError):
            pass
        
        try:
            deduction = float(data.get("total_deduction", 0))
            if deduction < 0:
                errors.append("Total deduction cannot be negative")
            if deduction > 999999.99:
                errors.append("Total deduction exceeds maximum (999999.99)")
        except (ValueError, TypeError):
            pass
        
        try:
            month, year = data.get("month_year", "").split('/')
            month_int = int(month)
            year_int = int(year)
            
            if month_int < 1 or month_int > 12:
                errors.append(f"Invalid month: {month}")
            if year_int < 2000 or year_int > 2099:
                errors.append(f"Invalid year: {year}")
        except (ValueError, AttributeError):
            pass
        
        try:
            gross = float(data.get("gross_income", 0))
            net = float(data.get("net_income", 0))
            deduction = float(data.get("total_deduction", 0))
            
            if gross > 0 and net > 0 and deduction > 0:
                calculated_net = gross - deduction
                if abs(calculated_net - net) > 1.0:
                    logger.warning(f"Math mismatch: gross({gross}) - deduction({deduction}) = {calculated_net}, but net = {net}")
        except (ValueError, TypeError):
            pass
        
        if errors:
            logger.warning(f"Validation errors: {errors}")
            data["validation_errors"] = errors
        
        return data
    
    def _extract_field(self, text: str, field_name: str) -> Optional[str]:
        field_config = self.payslip_config.get(field_name, {})
        keywords = field_config.get("keywords", [])
        pattern = field_config.get("pattern")
        fallback_patterns = field_config.get("fallback_patterns", [])
        exclusion_keywords = field_config.get("exclusion_keywords", [])
        
        for keyword in keywords:
            if pattern:
                match = re.search(rf'{keyword}[:\s]*({pattern})', text, re.IGNORECASE)
                if match:
                    result = match.group(1).strip()
                    
                    # Check exclusion keywords in surrounding context
                    if exclusion_keywords:
                        context_start = max(0, match.start() - 50)
                        context_end = min(len(text), match.end() + 50)
                        context = text[context_start:context_end].lower()
                        
                        if any(excl.lower() in context for excl in exclusion_keywords):
                            logger.debug(f"Rejected {field_name} due to exclusion: {result}")
                            continue
                    
                    if field_name == "month_year":
                        result = self._format_month_year(result, text)
                    return result
            else:
                match = re.search(rf'{keyword}[:\s]*([^\n]+)', text, re.IGNORECASE)
                if match:
                    result = match.group(1).strip()
                    
                    # Check exclusion keywords
                    if exclusion_keywords:
                        context_start = max(0, match.start() - 50)
                        context_end = min(len(text), match.end() + 50)
                        context = text[context_start:context_end].lower()
                        
                        if any(excl.lower() in context for excl in exclusion_keywords):
                            logger.debug(f"Rejected {field_name} due to exclusion: {result}")
                            continue
                    
                    if field_name == "month_year":
                        result = self._format_month_year(result, text)
                    return result
        
        for pattern in fallback_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    result = match.group(1).strip()
                except IndexError:
                    result = match.group(0).strip()
                
                # Check exclusion keywords in surrounding context
                if exclusion_keywords:
                    context_start = max(0, match.start() - 50)
                    context_end = min(len(text), match.end() + 50)
                    context = text[context_start:context_end].lower()
                    
                    if any(excl.lower() in context for excl in exclusion_keywords):
                        logger.debug(f"Rejected {field_name} due to exclusion: {result}")
                        continue
                
                if field_name == "month_year":
                    result = self._format_month_year(result, text)
                return result
        
        return None
    
    def _extract_name_from_text(self, text: str) -> Optional[str]:
        lines = text.split('\n')[:5]
        
        for line in lines:
            line = line.strip()
            if len(line) < 10 or len(line) > 100:
                continue
            
            name_pattern = r'^([A-Z][a-z]+(?:\s+(?:bin|binti|Bin|Binti)\s+)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
            match = re.match(name_pattern, line)
            if match:
                name = match.group(1).strip()
                if 3 <= len(name.split()) <= 6:
                    return name
        
        return None
        pattern = field_config.get("pattern")
        fallback_patterns = field_config.get("fallback_patterns", [])
        
        for keyword in keywords:
            if pattern:
                match = re.search(rf'{keyword}[:\s]*({pattern})', text, re.IGNORECASE)
                if match:
                    result = match.group(1).strip()
                    # Special handling for month_year field
                    if field_name == "month_year":
                        result = self._format_month_year(result, text)
                    return result
            else:
                match = re.search(rf'{keyword}[:\s]*([^\n]+)', text, re.IGNORECASE)
                if match:
                    result = match.group(1).strip()
                    if field_name == "month_year":
                        result = self._format_month_year(result, text)
                    return result
        
        for pattern in fallback_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    result = match.group(1).strip()
                    if field_name == "month_year":
                        result = self._format_month_year(result, text)
                    return result
                except IndexError:
                    result = match.group(0).strip()
                    if field_name == "month_year":
                        result = self._format_month_year(result, text)
                    return result
        
        return None
    
    def _format_month_year(self, value: str, full_text: str) -> str:
        """Format month/year to MM/YYYY format"""
        # If already in correct format MM/YYYY
        if re.match(r'^\d{1,2}/\d{4}$', value):
            parts = value.split('/')
            month = parts[0].zfill(2)
            return f"{month}/{parts[1]}"
        
        # If in M/M format (like 1/22 from M/S: 1/22), need to find the actual year
        if re.match(r'^\d{1,2}/\d{1,2}$', value):
            parts = value.split('/')
            potential_month = parts[0]
            potential_day = parts[1]
            
            # Look for a 4-digit year in the full text
            year_match = re.search(r'\b(20\d{2})\b', full_text)
            if year_match:
                year = year_match.group(1)
                
                # Determine which number is the month
                # If first number is 1-12, it's likely the month
                if 1 <= int(potential_month) <= 12:
                    month = potential_month.zfill(2)
                    return f"{month}/{year}"
                # If second number is 1-12 and first is > 12, swap them
                elif 1 <= int(potential_day) <= 12 and int(potential_month) > 12:
                    month = potential_day.zfill(2)
                    return f"{month}/{year}"
                else:
                    # Default to first number as month
                    month = potential_month.zfill(2)
                    return f"{month}/{year}"
            else:
                # No year found, assume current year 2025
                month = potential_month.zfill(2) if int(potential_month) <= 12 else potential_day.zfill(2)
                return f"{month}/2025"
        
        # If month name format
        month_names = {
            'januari': '01', 'februari': '02', 'mac': '03', 'april': '04',
            'mei': '05', 'jun': '06', 'julai': '07', 'ogos': '08',
            'september': '09', 'oktober': '10', 'november': '11', 'disember': '12',
            'january': '01', 'february': '02', 'march': '03', 'may': '05',
            'june': '06', 'july': '07', 'august': '08', 'october': '10', 'december': '12',
            'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
            'jul': '07', 'agu': '08', 'aug': '08', 'sep': '09',
            'okt': '10', 'oct': '10', 'nov': '11', 'des': '12', 'dec': '12'
        }
        
        for month_name, month_num in month_names.items():
            if month_name in value.lower():
                year_match = re.search(r'(20\d{2})', value)
                if year_match:
                    return f"{month_num}/{year_match.group(1)}"
        
        return value
    
    def _extract_currency_field(self, text: str, field_name: str) -> Optional[str]:
        field_config = self.payslip_config.get(field_name, {})
        patterns = field_config.get("fallback_patterns", [])
        exclusion_keywords = field_config.get("exclusion_keywords", [])
        
        # Direct pattern matching - NO PROXIMITY
        for pattern in patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE))
            
            for match in matches:
                try:
                    value_str = match.group(1).strip()
                except IndexError:
                    continue
                
                # Skip if already used
                if value_str in self.used_tokens:
                    logger.debug(f"Skipping already used token for {field_name}: {value_str}")
                    continue
                
                # Check exclusion keywords in surrounding context
                context_start = max(0, match.start() - 100)
                context_end = min(len(text), match.end() + 100)
                context = text[context_start:context_end].lower()
                
                # Skip if exclusion keyword found
                if any(keyword.lower() in context for keyword in exclusion_keywords):
                    logger.debug(f"Rejected {field_name} due to exclusion: {value_str}")
                    continue
                
                # Mark as used and return
                self.used_tokens.add(value_str)
                logger.info(f"Extracted {field_name}: {value_str} using pattern")
                return value_str
        
        return None
    
    def _extract_by_proximity(self, text: str, keywords: List[str], exclusion_keywords: List[str], max_distance: int = 100) -> Optional[str]:
        """DEPRECATED - Not used anymore"""
        return None
    
    def _calculate_total_deduction(self, text: str) -> Optional[str]:
        deduction_config = self.payslip_config.get("total_deduction", {})
        item_patterns = deduction_config.get("deduction_item_patterns", [])
        
        if not item_patterns:
            return None
        
        total = 0.0
        found_items = []
        
        for pattern in item_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                value_str = match.group(1).strip()
                numeric_value = self._parse_number(value_str)
                
                if numeric_value and numeric_value > 0:
                    total += numeric_value
                    found_items.append(f"{match.group(0)}: {numeric_value}")
                    logger.debug(f"Found deduction item: {numeric_value}")
        
        if total > 0 and len(found_items) >= 2:
            logger.info(f"Calculated total deduction: {total:.2f} from {len(found_items)} items")
            return f"{total:.2f}"
        
        return None
    
    def _parse_number(self, value_str: str) -> Optional[float]:
        try:
            # Remove spaces, commas, RM, and handle both . and - as decimal separators
            cleaned = value_str.replace(" ", "").replace(",", "").replace("RM", "").strip()
            # Replace - with . for decimal separator
            cleaned = cleaned.replace("-", ".")
            return float(cleaned)
        except (ValueError, AttributeError):
            return None
    
    def _clean_currency(self, value: Optional[str]) -> str:
        if not value:
            return "0.00"
        
        try:
            # Remove spaces, commas, RM, and handle both . and - as decimal separators
            cleaned = value.replace(" ", "").replace(",", "").replace("RM", "").strip()
            # Replace - with . for decimal separator
            cleaned = cleaned.replace("-", ".")
            numeric = float(cleaned)
            return f"{numeric:.2f}"
        except (ValueError, AttributeError):
            return "0.00"
    
    def calculate_confidence(self, extracted_data: Dict[str, Any]) -> float:
        required_fields = ["name", "id_number", "gross_income", "net_income", "total_deduction", "month_year"]
        filled_fields = sum(1 for field in required_fields if extracted_data.get(field) and extracted_data.get(field) != "0.00")
        confidence = filled_fields / len(required_fields)
        logger.info(f"Payslip confidence: {confidence:.2f} ({filled_fields}/{len(required_fields)} fields)")
        return round(confidence, 2)
