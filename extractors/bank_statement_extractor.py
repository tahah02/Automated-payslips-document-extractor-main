import json
import logging
import re
from typing import Dict, Any, Optional, Tuple, Set, List
from pathlib import Path
from core.utils import CurrencyFormatter, parse_number, normalize_nric, is_percentage_context, is_likely_percentage_value
from core.config import get_confidence_config, get_extraction_config, get_text_constraints_config, get_config
from core.layout_analyzer import LayoutAnalyzer
from core.spatial_search import SpatialSearch
from core.bank_detector import BankDetector
from core.number_formatter import NumberFormatter

logger = logging.getLogger(__name__)

class FieldExtractor:
    
    def __init__(self, config_path: str = "config/extraction_config.json", template: str = None):
        self.config = self._load_config(config_path)
        bank_config_path = config_path.replace("extraction_config.json", "bank_specific_config.json")
        self.bank_config = self._load_config(bank_config_path)
        self.template = template
        self.extraction_config = get_extraction_config(template)
        self.confidence_config = get_confidence_config(template)
        self.text_constraints = get_text_constraints_config(template)
        self.used_tokens: Set[str] = set()
        
        # Cache for multi-page statements
        self.cached_opening_balance = None
        self.cached_total_debit = None
        self.cached_total_credit = None
        
        full_config = get_config(template)
        self.layout_analyzer = LayoutAnalyzer(full_config)
        self.spatial_search = SpatialSearch(full_config, self.layout_analyzer)
    
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
    
    def _validate_date(self, date_str: str) -> Optional[str]:
        if not date_str:
            return None
        
        try:
            parts = date_str.split('/')
            if len(parts) != 3:
                logger.warning(f"Invalid date format: {date_str}")
                return None
            
            day = int(parts[0])
            month = int(parts[1])
            year = int(parts[2])
            
            # Validate day
            if day < 1 or day > 31:
                logger.warning(f"Invalid day in date: {date_str} (day={day})")
                return None
            
            # Validate month
            if month < 1 or month > 12:
                logger.warning(f"Invalid month in date: {date_str} (month={month})")
                return None
            
            # Handle 2-digit years
            if year < 100:
                year += 2000
            
            # Validate year range (2000-2099)
            if year < 2000 or year > 2099:
                logger.warning(f"Invalid year in date: {date_str} (year={year})")
                return None
            
            # Validate day for specific months
            if month in [4, 6, 9, 11] and day > 30:
                logger.warning(f"Invalid day for month in date: {date_str}")
                return None
            
            if month == 2 and day > 29:
                logger.warning(f"Invalid day for February in date: {date_str}")
                return None
            
            logger.info(f"✓ Date validated: {date_str}")
            return date_str
            
        except (ValueError, IndexError) as e:
            logger.warning(f"Error validating date {date_str}: {str(e)}")
            return None
    
    def _validate_and_fix_date(self, date_str: str) -> Optional[str]:
        """Validate date and attempt to fix common OCR errors"""
        if not date_str:
            return None
        
        # First try standard validation
        validated = self._validate_date(date_str)
        if validated:
            return validated
        
        # Try to fix common OCR errors
        logger.info(f"Attempting to fix invalid date: {date_str}")
        
        try:
            # Replace common OCR character mistakes
            fixed = date_str.replace('O', '0').replace('l', '1').replace('I', '1')
            fixed = fixed.replace('S', '5').replace('Z', '2').replace('B', '8')
            
            # Try validation again
            validated = self._validate_date(fixed)
            if validated:
                logger.info(f"Fixed date: {date_str} → {fixed}")
                return validated
            
            # Try to extract date pattern from garbled text
            import re
            # Look for any DD/MM/YYYY pattern
            match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{2,4})', fixed)
            if match:
                day, month, year = match.groups()
                day = int(day)
                month = int(month)
                year = int(year)
                
                # Clamp invalid values to valid ranges
                day = max(1, min(31, day))
                month = max(1, min(12, month))
                if year < 100:
                    year += 2000
                year = max(2000, min(2099, year))
                
                fixed_date = f"{day:02d}/{month:02d}/{year}"
                validated = self._validate_date(fixed_date)
                if validated:
                    logger.info(f"Clamped date: {date_str} → {fixed_date}")
                    return validated
            
        except Exception as e:
            logger.warning(f"Error fixing date {date_str}: {str(e)}")
        
        return None
    
    
    def extract_bank_statement_fields(self, text: str, tokens: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        bank_type, confidence = BankDetector.detect(text)
        logger.info(f"Detected bank: {bank_type} (confidence: {confidence})")
        
        extracted = self._extract_bank_statement_with_regex(text, bank_type)
        extracted['detected_bank'] = bank_type
        extracted['bank_detection_confidence'] = confidence
        
        # For Bank Islam multi-page statements, cache opening/debit/credit from first page
        if bank_type == 'bank_islam':
            # If opening balance is valid (not 0.00), cache it
            if extracted.get('opening_balance') and float(extracted['opening_balance']) > 0:
                self.cached_opening_balance = extracted['opening_balance']
                self.cached_total_debit = extracted.get('total_debit')
                self.cached_total_credit = extracted.get('total_credit')
                logger.info(f"Bank Islam: Cached opening balance: {self.cached_opening_balance}")
            # If opening balance is 0.00 but we have cached value, use it
            elif extracted.get('opening_balance') == '0.00' and self.cached_opening_balance:
                extracted['opening_balance'] = self.cached_opening_balance
                if self.cached_total_debit:
                    extracted['total_debit'] = self.cached_total_debit
                if self.cached_total_credit:
                    extracted['total_credit'] = self.cached_total_credit
                logger.info(f"Bank Islam: Using cached opening balance: {self.cached_opening_balance}")
            
            # Also cache debit/credit if they are valid (not None)
            if extracted.get('total_debit') and extracted['total_debit'] != 'None':
                self.cached_total_debit = extracted['total_debit']
            if extracted.get('total_credit') and extracted['total_credit'] != 'None':
                self.cached_total_credit = extracted['total_credit']
        
        return extracted
    
    def _extract_bank_statement_with_layout(self, tokens: List[Dict[str, Any]]) -> Dict[str, Any]:
        bank_config = self.extraction_config.get("bank_statement", {})
        
        merged_tokens = self.spatial_search.merge_adjacent_tokens(tokens)
        lines = self.layout_analyzer.group_tokens_to_lines(merged_tokens)
        
        extracted_name = self._extract_field_spatial(merged_tokens, lines, "account_holder_name", bank_config)
        extracted_account = self._extract_field_spatial(merged_tokens, lines, "account_number", bank_config)
        extracted_date = self._extract_field_spatial(merged_tokens, lines, "statement_date", bank_config)
        extracted_opening = self._extract_field_spatial(merged_tokens, lines, "opening_balance", bank_config)
        extracted_closing = self._extract_field_spatial(merged_tokens, lines, "closing_balance", bank_config)
        extracted_total_debit = self._extract_field_spatial(merged_tokens, lines, "total_debit", bank_config)
        extracted_total_credit = self._extract_field_spatial(merged_tokens, lines, "total_credit", bank_config)
        extracted_period_from = self._extract_field_spatial(merged_tokens, lines, "statement_period_from", bank_config)
        extracted_period_to = self._extract_field_spatial(merged_tokens, lines, "statement_period_to", bank_config)
        
        if extracted_account:
            extracted_account = re.sub(r'^(NO|No|no)\s+', '', extracted_account).strip()
        
        extracted = {
            "account_holder_name": extracted_name,
            "account_number": extracted_account,
            "statement_date": extracted_date,
            "opening_balance": extracted_opening,
            "closing_balance": extracted_closing,
            "total_debit": extracted_total_debit,
            "total_credit": extracted_total_credit,
            "statement_period_from": extracted_period_from,
            "statement_period_to": extracted_period_to
        }
        
        extracted["opening_balance"] = CurrencyFormatter.clean_currency(extracted["opening_balance"])
        extracted["closing_balance"] = CurrencyFormatter.clean_currency(extracted["closing_balance"])
        if extracted["total_debit"]:
            extracted["total_debit"] = CurrencyFormatter.clean_currency(extracted["total_debit"])
        if extracted["total_credit"]:
            extracted["total_credit"] = CurrencyFormatter.clean_currency(extracted["total_credit"])
        
        return extracted
    
    def _extract_bank_statement_with_regex(self, text: str, bank_type: str = 'generic') -> Dict[str, Any]:
        
        bank_config = self.bank_config.get(bank_type, {})
        if not bank_config:
            bank_config = self.config.get('bank_statement', {})
        
        extracted = {}
        
        extracted['account_number'] = self._extract_account_number(text, bank_type, bank_config)
        extracted['account_holder_name'] = self._extract_account_holder(text, bank_type, bank_config)
        extracted['statement_date'] = self._extract_statement_date(text, bank_type, bank_config)
        extracted['opening_balance'] = self._extract_opening_balance(text, bank_type, bank_config)
        extracted['closing_balance'] = self._extract_closing_balance(text, bank_type, bank_config)
        extracted['total_debit'] = self._extract_total_debit(text, bank_type, bank_config)
        extracted['total_credit'] = self._extract_total_credit(text, bank_type, bank_config)
        extracted['statement_period_from'] = self._extract_period_from(text, bank_type, bank_config, extracted.get('statement_date'))
        extracted['statement_period_to'] = self._extract_period_to(text, bank_type, bank_config, extracted.get('statement_date'))
        
        # STEP 3 FIX: Handle bank-specific optional fields
        if bank_type == 'cimb':
            # CIMB statements don't have summary section with total debit/credit
            # This is a format limitation, not an extraction bug
            if not extracted.get('total_debit'):
                extracted['total_debit'] = None
                logger.info("CIMB: total_debit not available in format (expected)")
            if not extracted.get('total_credit'):
                extracted['total_credit'] = None
                logger.info("CIMB: total_credit not available in format (expected)")
        
        if bank_type == 'bsn':
            available_balance = self._extract_available_balance_bsn(text)
            if available_balance:
                extracted['available_balance'] = available_balance
                extracted['closing_balance'] = available_balance
        
        for key in ['opening_balance', 'closing_balance', 'total_debit', 'total_credit', 'available_balance']:
            if key in extracted and extracted[key]:
                extracted[key] = CurrencyFormatter.clean_currency(extracted[key])
        
        if not extracted.get('opening_balance'):
            extracted['opening_balance'] = "0.00"
        if not extracted.get('closing_balance'):
            extracted['closing_balance'] = "0.00"
        
        logger.info(f"Final extracted data for {bank_type}: {extracted}")
        return extracted
    
    def _extract_account_number(self, text: str, bank_type: str, config: dict) -> Optional[str]:
        field_config = config.get('account_number', {})
        keywords = field_config.get('keywords', [])
        pattern = field_config.get('pattern')
        
        if bank_type == 'cimb':
            match = re.search(r'(\d{2}-\d{7}-\d{1})', text)
            if match:
                return match.group(1).strip()
        
        if bank_type == 'bsn':
            match = re.search(r'BSN\s+PENYATA\s+AKAUN\s+(\d{16})', text)
            if match:
                return match.group(1).strip()
        
        if bank_type == 'public_islamic':
            match = re.search(r'(\d{10})\s+Nombor Akaun', text)
            if match:
                return match.group(1).strip()
        
        if bank_type == 'bank_islam':
            match = re.search(r'ACCOUNT NO\s+(\d{14})', text)
            if match:
                return match.group(1).strip()
        
        for keyword in keywords:
            match = re.search(rf'{keyword}[:\s\.]*({pattern})', text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        if pattern:
            match = re.search(pattern, text)
            if match:
                return match.group(0).strip()
        
        return None
    
    def _extract_account_holder(self, text: str, bank_type: str, config: dict) -> Optional[str]:
        field_config = config.get('account_holder_name', {})
        pattern = field_config.get('pattern')
        
        # Try bank-specific pattern from config first
        if pattern:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1) if match.lastindex and match.lastindex >= 1 else match.group(0)
                cleaned_name = ' '.join(name.upper().split())
                logger.info(f"Extracted account holder via config pattern: {cleaned_name}")
                return cleaned_name
        
        # Bank-specific extraction logic
        if bank_type == 'public_islamic':
            # Pattern 1: Name before 3-digit code and account number
            match = re.search(r'((?:MOHAMAD|ENCIK|PUAN|CIKGU|TN|TUAN|DATO)\s+[A-Z\s]+?(?:BIN|BINTI|ANAK)?\s+[A-Z\s]+?)(?=\s+\d{3}\s+\d{10})', text, re.IGNORECASE)
            if match:
                cleaned_name = ' '.join(match.group(1).upper().split())
                logger.info(f"Extracted Public Islamic account holder: {cleaned_name}")
                return cleaned_name
            
            # Pattern 2: Name before "PENYATA AKAUN"
            match = re.search(r'((?:MOHAMAD|ENCIK|PUAN|CIKGU)\s+[A-Z\s]+?(?:BIN|BINTI|ANAK)\s+[A-Z\s]+?)(?=\s+(?:PENYATA AKAUN|STATEMENT OF ACCOUNT))', text, re.IGNORECASE)
            if match:
                cleaned_name = ' '.join(match.group(1).upper().split())
                logger.info(f"Extracted Public Islamic account holder (alt): {cleaned_name}")
                return cleaned_name
        
        elif bank_type == 'cimb':
            # CIMB: Name before address
            match = re.search(r'([A-Z][A-Za-z]+\s+[A-Z][A-Za-z]+\s+(?:BINTI|BIN)\s+[A-Z][A-Za-z]+)(?=\s+\d+,?\s+(?:JALAN|LOT|NO\.))', text, re.IGNORECASE)
            if match:
                cleaned_name = ' '.join(match.group(1).upper().split())
                logger.info(f"Extracted CIMB account holder: {cleaned_name}")
                return cleaned_name
        
        elif bank_type == 'bsn':
            # BSN: Name before "No.Akaun"
            match = re.search(r'([A-Z][A-Z\s]+?(?:BIN|BINTI|ANAK)\s+[A-Z\s]+?)(?=\s+No\.Akaun)', text, re.IGNORECASE)
            if match:
                cleaned_name = ' '.join(match.group(1).upper().split())
                logger.info(f"Extracted BSN account holder: {cleaned_name}")
                return cleaned_name
        
        elif bank_type == 'bank_islam':
            # Bank Islam: Name before TARIKH
            match = re.search(r'((?:ENCIK|PUAN|CIKGU)\s+[A-Z\s]+?)(?=\s+TARIKH)', text, re.IGNORECASE)
            if match:
                cleaned_name = ' '.join(match.group(1).upper().split())
                logger.info(f"Extracted Bank Islam account holder: {cleaned_name}")
                return cleaned_name
        
        # Generic fallback patterns
        match = re.search(r'((?:ENCIK|PUAN|CIKGU)\s+[A-Z\s]+?)(?=\s+(?:TARIKH|STATEMENT|DATE|JALAN|LOT|NO\.|NOMBOR))', text, re.IGNORECASE)
        if match:
            cleaned_name = ' '.join(match.group(1).upper().split())
            logger.info(f"Extracted account holder (generic title): {cleaned_name}")
            return cleaned_name
        
        match = re.search(r'([A-Z][A-Z\s]+?(?:ANAK|BINTI|BIN)\s+[A-Z]+)(?=\s+(?:No\.Akaun|Account\s+No|DIA\s+RUMAH|\d{10,}))', text, re.IGNORECASE)
        if match:
            cleaned_name = ' '.join(match.group(1).upper().split())
            logger.info(f"Extracted account holder (generic BIN/BINTI): {cleaned_name}")
            return cleaned_name
        
        logger.warning(f"Could not extract account holder for bank: {bank_type}")
        return None
    
    def _extract_statement_date(self, text: str, bank_type: str, config: dict) -> Optional[str]:
        field_config = config.get('statement_date', {})
        keywords = field_config.get('keywords', [])
        pattern = field_config.get('pattern')
        
        # Public Islamic specific formats - handle both "DD Month YYYY" and "YYYY Month DD"
        if bank_type == 'public_islamic':
            # Try "YYYY Month DD" format (e.g., "2025 May 20")
            match = re.search(r'(\d{4})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})', text, re.IGNORECASE)
            if match:
                year, month, day = match.group(1), match.group(2), match.group(3)
                formatted_date = f"{day} {month} {year}"
                logger.info(f"Extracted Public Islamic statement date (YYYY Month DD): {formatted_date}")
                return formatted_date
            
            # Try "DD Month YYYY" format (e.g., "20 May 2025")
            match = re.search(r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})', text, re.IGNORECASE)
            if match:
                formatted_date = match.group(0).strip()
                logger.info(f"Extracted Public Islamic statement date (DD Month YYYY): {formatted_date}")
                return formatted_date
        
        # Try with keywords first
        for keyword in keywords:
            if pattern:
                match = re.search(rf'{keyword}[:\s]*({pattern})', text, re.IGNORECASE)
                if match:
                    date_str = match.group(1)
                    validated = self._validate_and_fix_date(date_str)
                    if validated:
                        logger.info(f"Extracted statement date via keyword '{keyword}': {validated}")
                        return validated
        
        # Fallback: search for date pattern directly near top of document
        if pattern:
            top_text = text[:500]
            matches = re.finditer(pattern, top_text)
            for match in matches:
                date_str = match.group(0).strip()
                validated = self._validate_and_fix_date(date_str)
                if validated:
                    logger.info(f"Extracted statement date via pattern fallback: {validated}")
                    return validated
        
        return None
    
    def _extract_opening_balance(self, text: str, bank_type: str, config: dict) -> Optional[str]:
        field_config = config.get('opening_balance', {})
        keywords = field_config.get('keywords', [])
        
        for keyword in keywords:
            match = re.search(rf'{keyword}[:\s]*(?:RM)?[:\s]*([0-9,\.]+)', text, re.IGNORECASE)
            if match:
                value = match.group(1)
                normalized = NumberFormatter.normalize(value, bank_type)
                return str(normalized) if normalized else None
        
        return None
    
    def _extract_closing_balance(self, text: str, bank_type: str, config: dict) -> Optional[str]:
        field_config = config.get('closing_balance', {})
        keywords = field_config.get('keywords', [])
        position = field_config.get('position')
        
        if bank_type == 'bsn' and position == 'summary_section':
            return self._extract_available_balance_bsn(text)
        
        # Bank Islam specific: Calculate from Opening + Credit - Debit
        if bank_type == 'bank_islam':
            logger.info("Bank Islam: Calculating closing balance from Opening + Credit - Debit")
            opening = self._extract_opening_balance(text, bank_type, config)
            credit = self._extract_total_credit(text, bank_type, config)
            debit = self._extract_total_debit(text, bank_type, config)
            
            # Use cached values if current extraction is None
            if not opening and self.cached_opening_balance:
                opening = self.cached_opening_balance
                logger.info(f"Bank Islam: Using cached opening balance: {opening}")
            if not credit and self.cached_total_credit:
                credit = self.cached_total_credit
                logger.info(f"Bank Islam: Using cached total credit: {credit}")
            if not debit and self.cached_total_debit:
                debit = self.cached_total_debit
                logger.info(f"Bank Islam: Using cached total debit: {debit}")
            
            if opening and credit and debit:
                try:
                    opening_val = float(opening.replace(',', ''))
                    credit_val = float(credit.replace(',', ''))
                    debit_val = float(debit.replace(',', ''))
                    
                    closing_val = opening_val + credit_val - debit_val
                    result = f"{closing_val:.2f}"
                    logger.info(f"Bank Islam closing balance calculated: {opening} + {credit} - {debit} = {result}")
                    return result
                except Exception as e:
                    logger.warning(f"Bank Islam closing balance calculation failed: {str(e)}")
        
        if bank_type == 'public_islamic':
            closing_patterns = [
                r'(?:Baki Penutup|Closing Balance)[:\s]*(?:RM)?[:\s]*([0-9,\.]+)',
                r'Closing Balance In This Statement[:\s]*([0-9,\.]+)',
                r'([0-9,\.]+)\s*(?:Baki Penutup|Closing Balance)'
            ]
            
            for pattern in closing_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value = match.group(1)
                    normalized = NumberFormatter.normalize(value, bank_type)
                    if normalized:
                        logger.info(f"Public Islamic closing balance found: {value} -> {normalized}")
                        return str(normalized)
            
            summary_match = re.search(r'(?:RINGKASAN|SUMMARY|HIGHLIGHTS)', text, re.IGNORECASE)
            if summary_match:
                summary_text = text[summary_match.start():summary_match.start()+1000]
                match = re.search(r'([0-9,\.]+)\s+[^\d]*?(?:Baki Penutup|Closing Balance)', summary_text, re.IGNORECASE)
                if match:
                    value = match.group(1)
                    normalized = NumberFormatter.normalize(value, bank_type)
                    if normalized:
                        return str(normalized)
        
        for keyword in keywords:
            match = re.search(rf'{keyword}[:\s]*(?:RM)?[:\s]*([0-9,\.]+)', text, re.IGNORECASE)
            if match:
                value = match.group(1)
                normalized = NumberFormatter.normalize(value, bank_type)
                return str(normalized) if normalized else None
        
        balance_lines = re.findall(r'\d{1,2}/\d{1,2}/\d{2,4}.*?([0-9,\.]+)', text, re.MULTILINE)
        if balance_lines:
            value = balance_lines[-1]
            normalized = NumberFormatter.normalize(value, bank_type)
            return str(normalized) if normalized else None
        
        return None
    
    def _extract_available_balance_bsn(self, text: str) -> Optional[str]:
        match = re.search(r'(?:Baki Sedia Ada|Available Balance)[:\s]*([0-9,\.]+)', text, re.IGNORECASE)
        if match:
            value = match.group(1)
            return str(NumberFormatter.normalize(value, 'bsn'))
        return None
    
    def _extract_total_debit(self, text: str, bank_type: str, config: dict) -> Optional[str]:
        field_config = config.get('total_debit', {})
        keywords = field_config.get('keywords', [])
        section_marker = field_config.get('section_marker')
        
        if bank_type == 'public_islamic':
            summary_match = re.search(r'(?:RINGKASAN|SUMMARY|HIGHLIGHTS)', text, re.IGNORECASE)
            if summary_match:
                summary_text = text[summary_match.start():summary_match.start()+1000]
                debit_match = re.search(r'(?:Jumlah Debit|Total Debits)', summary_text, re.IGNORECASE)
                if debit_match:
                    text_before_label = summary_text[:debit_match.start()]
                    numbers = re.findall(r'(\d{1,3}(?:,\d{3})+\.\d{2})', text_before_label)
                    if numbers:
                        value = numbers[-1]
                        normalized = NumberFormatter.normalize(value, bank_type)
                        return str(normalized) if normalized else None
        
        if section_marker:
            marker_match = re.search(section_marker, text, re.IGNORECASE)
            if marker_match:
                text = text[marker_match.start():]
        
        for keyword in keywords:
            match = re.search(rf'{keyword}[:\s]*(?:RM)?[:\s]*([0-9,\.]+)', text, re.IGNORECASE)
            if match:
                value = match.group(1)
                normalized = NumberFormatter.normalize(value, bank_type)
                return str(normalized) if normalized else None
        
        return None
    
    def _extract_total_credit(self, text: str, bank_type: str, config: dict) -> Optional[str]:
        field_config = config.get('total_credit', {})
        keywords = field_config.get('keywords', [])
        section_marker = field_config.get('section_marker')
        
        if bank_type == 'public_islamic':
            summary_match = re.search(r'(?:RINGKASAN|SUMMARY|HIGHLIGHTS)', text, re.IGNORECASE)
            if summary_match:
                summary_text = text[summary_match.start():summary_match.start()+1000]
                match = re.search(r'([0-9,\.]+)\s+[^\d]*?(?:Jumlah Kredit|Total Credits)', summary_text, re.IGNORECASE)
                if match:
                    value = match.group(1)
                    normalized = NumberFormatter.normalize(value, bank_type)
                    return str(normalized) if normalized else None
        
        if section_marker:
            marker_match = re.search(section_marker, text, re.IGNORECASE)
            if marker_match:
                text = text[marker_match.start():]
        
        for keyword in keywords:
            match = re.search(rf'{keyword}[:\s]*(?:RM)?[:\s]*([0-9,\.]+)', text, re.IGNORECASE)
            if match:
                value = match.group(1)
                normalized = NumberFormatter.normalize(value, bank_type)
                return str(normalized) if normalized else None
        
        return None
    
    def _extract_period_from(self, text: str, bank_type: str, config: dict, statement_date: str) -> Optional[str]:
        field_config = config.get('statement_period_from', {})
        keywords = field_config.get('keywords', [])
        pattern = field_config.get('pattern')
        
        for keyword in keywords:
            match = re.search(rf'{keyword}[:\s]*({pattern})', text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        date_range_match = re.search(r'(\d{2}/\d{2}/\d{2,4})\s*(?:-|to|TO)\s*(\d{2}/\d{2}/\d{2,4})', text, re.IGNORECASE)
        if date_range_match:
            return date_range_match.group(1)
        
        return self._extract_first_transaction_date(text, statement_date)
    
    def _extract_period_to(self, text: str, bank_type: str, config: dict, statement_date: str) -> Optional[str]:
        field_config = config.get('statement_period_to', {})
        keywords = field_config.get('keywords', [])
        pattern = field_config.get('pattern')
        
        for keyword in keywords:
            match = re.search(rf'{keyword}[:\s]*({pattern})', text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        date_range_match = re.search(r'(\d{2}/\d{2}/\d{2,4})\s*(?:-|to|TO)\s*(\d{2}/\d{2}/\d{2,4})', text, re.IGNORECASE)
        if date_range_match:
            return date_range_match.group(2)
        
        return self._extract_last_transaction_date(text, statement_date)
    
    def _extract_field(self, text: str, field_name: str) -> Optional[str]:
        try:
            if field_name in self.config.get("payslip", {}):
                field_config = self.config["payslip"][field_name]
            elif field_name in self.config.get("bank_statement", {}):
                field_config = self.config["bank_statement"][field_name]
            else:
                logger.warning(f"Field not found in config: {field_name}")
                return None
            
            if field_config.get("pattern"):
                match = re.search(field_config["pattern"], text, re.IGNORECASE)
                if match:
                    return match.group(0)
            
            keywords = field_config.get("keywords", [])
            for keyword in keywords:
                pattern = f"{keyword}[:\\s]+([^\\n]+?)(?=\\n|$|[A-Z][a-z])"
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    value = re.sub(r'\s+', ' ', value)
                    value = re.sub(r'[^\w\s\-./,RM]', '', value).strip()
                    if value and len(value) > 1:
                        return value
            
            return None
        
        except Exception as e:
            logger.error(f"Error extracting field {field_name}: {str(e)}")
            return None
    
    def _extract_first_transaction_date(self, text: str, statement_date: str) -> Optional[str]:
        try:
            year = statement_date.split('/')[-1] if statement_date else "2025"
            
            MONTH_MAP = {
                "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04",
                "MAY": "05", "JUN": "06", "JUL": "07", "AUG": "08",
                "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12"
            }
            
            # STEP 1 FIX: For CIMB, look for dates AFTER "Transaction Details" section
            # This prevents extracting dates from bonus points or other sections
            transaction_text = text
            if "Transaction Details" in text or "Butir-butir Transaksi" in text:
                if "Transaction Details" in text:
                    start_idx = text.index("Transaction Details")
                    logger.info("Found 'Transaction Details' section for date extraction")
                else:
                    start_idx = text.index("Butir-butir Transaksi")
                    logger.info("Found 'Butir-butir Transaksi' section for date extraction")
                
                transaction_text = text[start_idx:]
                logger.debug(f"Searching for dates in transaction section (length: {len(transaction_text)})")
            
            # BSN format: DDMON (e.g., "01JAN")
            bsn_dates = re.findall(r'(\d{2})(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)', transaction_text)
            if bsn_dates:
                day, month = bsn_dates[0]
                result = f"{day}/{MONTH_MAP[month]}/{year}"
                logger.info(f"Extracted first transaction date (BSN format): {result}")
                return result
            
            # Standard format: DD/MM/YYYY or D/MM/YYYY
            standard_dates = re.findall(r'(\d{1,2}/\d{2}/\d{2,4})', transaction_text)
            if standard_dates:
                for date in standard_dates:
                    parts = date.split('/')
                    if len(parts[2]) == 2:
                        parts[2] = "20" + parts[2]
                    if len(parts[0]) == 1:
                        parts[0] = "0" + parts[0]
                    normalized = f"{parts[0]}/{parts[1]}/{parts[2]}"
                    
                    # Validate date
                    validated = self._validate_date(normalized)
                    if validated and validated != statement_date:
                        logger.info(f"Extracted first transaction date: {validated}")
                        return validated
            
            logger.warning("No valid first transaction date found")
            return None
        except Exception as e:
            logger.warning(f"Failed to extract first transaction date: {e}")
            return None
    
    def _extract_last_transaction_date(self, text: str, statement_date: str) -> Optional[str]:
        try:
            year = statement_date.split('/')[-1] if statement_date else "2025"
            
            MONTH_MAP = {
                "JAN": "01", "FEB": "02", "MAR": "03", "APR": "04",
                "MAY": "05", "JUN": "06", "JUL": "07", "AUG": "08",
                "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12"
            }
            
            # STEP 2 FIX: For CIMB, look for dates BEFORE "End of Statement"
            # For other banks, look before summary section
            search_text = text
            
            # Check for CIMB end marker
            if "End of Statement" in text or "Penyata Tamat" in text:
                if "End of Statement" in text:
                    end_idx = text.index("End of Statement")
                    logger.info("Found 'End of Statement' marker for last date extraction")
                else:
                    end_idx = text.index("Penyata Tamat")
                    logger.info("Found 'Penyata Tamat' marker for last date extraction")
                
                search_text = text[:end_idx]
            # Check for other banks' summary markers
            elif re.search(r'(?:Baki Sedia Ada|Available Balance|RINGKASAN|SUMMARY)', text, re.IGNORECASE):
                summary_match = re.search(r'(?:Baki Sedia Ada|Available Balance|RINGKASAN|SUMMARY)', text, re.IGNORECASE)
                search_text = text[:summary_match.start()]
                logger.info("Found summary section marker for last date extraction")
            
            logger.debug(f"Searching for last date in text (length: {len(search_text)})")
            
            # BSN format: DDMON (e.g., "25AUG")
            bsn_dates = re.findall(r'(\d{2})(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)', search_text)
            if bsn_dates:
                day, month = bsn_dates[-1]
                result = f"{day}/{MONTH_MAP[month]}/{year}"
                logger.info(f"Extracted last transaction date (BSN format): {result}")
                return result
            
            # Standard format: DD/MM/YYYY or D/MM/YYYY
            standard_dates = re.findall(r'(\d{1,2}/\d{2}/\d{2,4})', search_text)
            if standard_dates:
                # Iterate from last to first to find valid date
                for date in reversed(standard_dates):
                    parts = date.split('/')
                    if len(parts[2]) == 2:
                        parts[2] = "20" + parts[2]
                    if len(parts[0]) == 1:
                        parts[0] = "0" + parts[0]
                    normalized = f"{parts[0]}/{parts[1]}/{parts[2]}"
                    
                    # Validate date and ensure it's not the statement date
                    validated = self._validate_date(normalized)
                    if validated and validated != statement_date:
                        logger.info(f"Extracted last transaction date: {validated}")
                        return validated
            
            logger.warning("No valid last transaction date found")
            return None
        except Exception as e:
            logger.warning(f"Failed to extract last transaction date: {e}")
            return None
    
    def calculate_confidence(self, extracted_data: Dict[str, Any]) -> float:
        if not extracted_data:
            return 0.0
        
        total_fields = len(extracted_data)
        filled_fields = sum(1 for v in extracted_data.values() if v is not None)
        
        confidence = filled_fields / total_fields if total_fields > 0 else 0.0
        return round(confidence, 2)
    
    def compute_confidence_detailed(
        self,
        ocr_conf: Optional[float] = None,
        regex_ok: bool = False,
        prox_score: float = 0.0,
        source: str = "ocr"
    ) -> Tuple[float, Dict[str, Any]]:
        weights = self.confidence_config.get("weights", {
            "ocr": 0.45,
            "regex": 0.30,
            "proximity": 0.20,
            "source": 0.05
        })
        
        default_ocr = self.confidence_config.get("default_ocr_confidence", 0.6)
        pdf_bonus = self.confidence_config.get("pdf_source_bonus", 0.15)
        
        ocr = ocr_conf if ocr_conf is not None else default_ocr
        regex = 1.0 if regex_ok else 0.0
        source_bonus = pdf_bonus if source == "pdf" else 0.0
        
        raw_score = (
            weights["ocr"] * ocr +
            weights["regex"] * regex +
            weights["proximity"] * prox_score +
            weights["source"] * source_bonus
        )
        
        final = max(0.0, min(1.0, raw_score))
        
        breakdown = {
            "ocr_confidence": round(ocr, 3),
            "regex_match": bool(regex_ok),
            "proximity_score": round(prox_score, 3),
            "source_bonus": round(source_bonus, 3),
            "weights_used": weights
        }
        
        return final, breakdown

    
    def _extract_field_spatial(self, tokens: List[Dict[str, Any]], lines: List[Dict[str, Any]], 
                               field_name: str, config: Dict[str, Any]) -> Optional[str]:
        
        field_config = config.get(field_name, {})
        
        keywords = field_config.get('keywords', [])
        fallback_patterns = field_config.get('fallback_patterns', [])
        
        label_keywords = list(keywords)
        for pattern in fallback_patterns:
            match = re.search(r'^([A-Za-z\s/]+)', pattern)
            if match:
                keyword = match.group(1).strip()
                if keyword and keyword not in label_keywords:
                    label_keywords.append(keyword)
        
        if not label_keywords:
            label_keywords = [field_name.replace('_', ' ')]
        
        logger.debug(f"Searching for {field_name} with keywords: {label_keywords}")
        
        label_token = self.spatial_search.find_label_token(tokens, label_keywords)
        
        if not label_token:
            logger.debug(f"Label not found for {field_name}")
            return None
        
        is_numeric_field = field_name in ['gross_income', 'net_income', 'total_deduction', 
                                          'opening_balance', 'closing_balance']
        
        for line in lines:
            if label_token in line['tokens']:
                if is_numeric_field:
                    exclusion_keywords = field_config.get('exclusion_keywords', [])
                    value_token = self.spatial_search.find_right_neighbor(
                        label_token, line['tokens'], field_name, exclusion_keywords
                    )
                else:
                    value_token = self._find_text_value(label_token, line['tokens'], field_name)
                
                if value_token:
                    self.layout_analyzer.mark_token_used(value_token, field_name)
                    logger.info(f"Extracted {field_name} from same line: {value_token['text']}")
                    return value_token['text']
                break
        
        if is_numeric_field:
            exclusion_keywords = field_config.get('exclusion_keywords', [])
            value_token = self.spatial_search.find_below_label(
                label_token, tokens, field_name, exclusion_keywords
            )
            
            if value_token:
                self.layout_analyzer.mark_token_used(value_token, field_name)
                logger.info(f"Extracted {field_name} from below: {value_token['text']}")
                return value_token['text']
        
        return None
    
    def _find_text_value(self, label_token: Dict[str, Any], line_tokens: List[Dict[str, Any]], 
                        field_name: str) -> Optional[Dict[str, Any]]:
        
        candidates = []
        
        for token in line_tokens:
            if token['x0'] <= label_token['x1']:
                continue
            
            if self.layout_analyzer.is_token_used(token):
                continue
            
            is_numeric_only = re.match(r'^[\d,.\s\-]+$', token['text'])
            
            if field_name == 'id_number':
                if not is_numeric_only and not re.search(r'\d', token['text']):
                    continue
            else:
                if is_numeric_only:
                    continue
            
            distance = token['x0'] - label_token['x1']
            candidates.append({
                'token': token,
                'distance': distance
            })
        
        if not candidates:
            return None
        
        candidates.sort(key=lambda c: c['distance'])
        return candidates[0]['token']
