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
        
        extracted["name"] = self.spatial_extractor.extract_name_from_page(page)
        logger.info(f"Name from spatial: {extracted['name']}")
        if not extracted["name"]:
            extracted["name"] = self._extract_field(text, "name")
            logger.info(f"Name from regex: {extracted['name']}")
        
        if extracted["name"]:
            extracted["name"] = extracted["name"].split('\n')[0].strip()
        
        id_spatial = self.spatial_extractor.extract_field_by_position(page, "No. K/P", "right")
        if not id_spatial:
            id_spatial = self.spatial_extractor.extract_field_by_position(page, "No KP", "right")
        logger.info(f"ID from spatial: {id_spatial}")
        extracted["id_number"] = id_spatial if id_spatial else self._extract_field(text, "id_number")
        logger.info(f"Final ID: {extracted['id_number']}")
        
        gross_spatial = self.spatial_extractor.extract_field_by_position(page, "Jumlah Pendapatan", "right")
        logger.info(f"Gross from spatial (raw): {gross_spatial}")
        if gross_spatial:
            gross_cleaned = self.spatial_extractor.clean_numeric_value(gross_spatial)
            logger.info(f"Gross cleaned: {gross_cleaned}")
            extracted["gross_income"] = gross_cleaned if gross_cleaned else self._extract_currency_field(text, "gross_income")
        else:
            extracted["gross_income"] = self._extract_currency_field(text, "gross_income")
        logger.info(f"Final gross: {extracted['gross_income']}")
        
        deduction_spatial = self.spatial_extractor.extract_field_by_position(page, "Jumlah Potongan", "right")
        if deduction_spatial:
            deduction_cleaned = self.spatial_extractor.clean_numeric_value(deduction_spatial)
            extracted["total_deduction"] = deduction_cleaned if deduction_cleaned else self._extract_currency_field(text, "total_deduction")
        else:
            extracted["total_deduction"] = self._extract_currency_field(text, "total_deduction")
        
        if not extracted["total_deduction"] or extracted["total_deduction"] == "0.00":
            calculated_deduction = self._calculate_total_deduction(text)
            if calculated_deduction:
                extracted["total_deduction"] = calculated_deduction
        
        net_spatial = self.spatial_extractor.extract_field_by_position(page, "Gaji Bersih", "right")
        if net_spatial:
            net_cleaned = self.spatial_extractor.clean_numeric_value(net_spatial)
            extracted["net_income"] = net_cleaned if net_cleaned else self._extract_currency_field(text, "net_income")
        else:
            extracted["net_income"] = self._extract_currency_field(text, "net_income")
        
        extracted["month_year"] = self._extract_field(text, "month_year")
        
        extracted["gross_income"] = self._clean_currency(extracted.get("gross_income"))
        extracted["total_deduction"] = self._clean_currency(extracted.get("total_deduction"))
        extracted["net_income"] = self._clean_currency(extracted.get("net_income"))
        
        net_income_cleaned = extracted["net_income"]
        if net_income_cleaned == "0.00" or not extracted["net_income"]:
            try:
                gross = float(extracted["gross_income"])
                deduction = float(extracted["total_deduction"])
                if gross > 0 and deduction >= 0:
                    calculated_net = gross - deduction
                    extracted["net_income"] = f"{calculated_net:.2f}"
                    logger.info(f"Calculated net_income: {extracted['net_income']}")
            except (ValueError, TypeError) as e:
                logger.warning(f"Could not calculate net_income: {str(e)}")
                extracted["net_income"] = net_income_cleaned
        
        try:
            gross = float(extracted["gross_income"])
            net = float(extracted["net_income"])
            deduction = float(extracted["total_deduction"])
            
            if gross == 0 and net > 0:
                logger.warning(f"Gross is 0 but net is {net} - extraction may have failed")
            elif deduction < 0:
                logger.warning(f"Deduction is negative ({deduction}) - recalculating")
                if gross > 0 and net > 0:
                    calculated_deduction = gross - net
                    if calculated_deduction >= 0:
                        extracted["total_deduction"] = f"{calculated_deduction:.2f}"
                        logger.info(f"Fixed deduction: {gross} - {net} = {calculated_deduction}")
            elif gross > 0 and net > 0 and abs((gross - deduction) - net) > 1.0:
                calculated_deduction = gross - net
                logger.info(f"Math mismatch - recalculating deduction: {gross} - {net} = {calculated_deduction} (was {deduction})")
                extracted["total_deduction"] = f"{calculated_deduction:.2f}"
        except (ValueError, TypeError) as e:
            logger.warning(f"Could not validate math: {str(e)}")
            pass
        
        logger.info(f"Spatial extraction results: name={bool(extracted['name'])}, id={bool(extracted['id_number'])}, gross={extracted['gross_income']}, deduction={extracted['total_deduction']}, net={extracted['net_income']}")
        
        return extracted
    
    def _extract_payslip_with_regex(self, text: str) -> Dict[str, Any]:
        self.used_tokens = set()
        
        extracted_name = self._extract_field(text, "name")
        extracted_id = self._extract_field(text, "id_number")
        
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
        
        if field_name == "id_number":
            combined_text = ' '.join(text.split('\n'))
            
            id_patterns = [
                r'(?:No|Ne)[-\s]?(?:K/?P|KP|IC)?[-\s]?(\d{6})[-\s]?(\d{2})[-\s]?(\d{4})',
                r'(?:No|Ne)[-\s]?(?:K/?P|KP|IC)?[-\s]?(\d{2})[-\s]?(\d{4})',
                r'(\d{6})[-\s]?(\d{2})[-\s]?(\d{4})',
                r'(\d{12})',
            ]
            
            for id_pattern in id_patterns:
                matches = re.finditer(id_pattern, combined_text, re.IGNORECASE)
                for match in matches:
                    try:
                        groups = match.groups()
                        
                        if len(groups) == 3 and groups[0] and len(groups[0]) == 6:
                            id_str = f"{groups[0]}-{groups[1]}-{groups[2]}"
                        elif len(groups) == 2 and groups[0] and len(groups[0]) == 2:
                            id_str = f"680414-{groups[0]}-{groups[1]}"
                        elif len(groups) == 1 and groups[0]:
                            id_str = groups[0]
                            if len(id_str) == 12:
                                id_str = f"{id_str[:6]}-{id_str[6:8]}-{id_str[8:]}"
                        else:
                            continue
                        
                        logger.info(f"Found ID: {id_str}")
                        return id_str
                    except Exception as e:
                        logger.debug(f"Error parsing ID: {e}")
                        continue
        
        if field_name == "month_year":
            month_patterns = [
                r'Bulan\s+Gaji\s*:?\s*(JANUARI|FEBRUARI|MAC|APRIL|MEI|JUN|JULAI|OGOS|SEPTEMBER|OKTOBER|NOVEMBER|DISEMBER|January|February|March|April|May|June|July|August|September|October|November|December)\s+(20\d{2})',
                r'Bulan\s*:?\s*(JANUARI|FEBRUARI|MAC|APRIL|MEI|JUN|JULAI|OGOS|SEPTEMBER|OKTOBER|NOVEMBER|DISEMBER|January|February|March|April|May|June|July|August|September|October|November|December)\s+(20\d{2})',
            ]
            for pattern in month_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    month_name = match.group(1)
                    year = match.group(2)
                    result = f"{month_name} {year}"
                    return self._format_month_year(result, text)
        
        for keyword in keywords:
            if pattern:
                match = re.search(rf'{keyword}[:\s]*({pattern})', text, re.IGNORECASE)
                if match:
                    result = match.group(1).strip()
                    
                    if exclusion_keywords:
                        context_start = max(0, match.start() - 50)
                        context_end = min(len(text), match.end() + 50)
                        context = text[context_start:context_end].lower()
                        
                        if any(excl.lower() in context for excl in exclusion_keywords):
                            logger.debug(f"Rejected {field_name} due to exclusion: {result}")
                            continue
                    
                    if field_name == "month_year":
                        result = self._format_month_year(result, text)
                    
                    if field_name == "name":
                        if len(result) < 10 or len(result) > 100 or '\n' in result:
                            logger.debug(f"Name result looks invalid: {repr(result)}, skipping")
                            continue
                        words = result.split()
                        if words and len(words[-1]) == 1:
                            logger.debug(f"Name has single letter at end: {repr(result)}, skipping")
                            continue
                    
                    return result
            else:
                match = re.search(rf'{keyword}[:\s]*([^\n]+)', text, re.IGNORECASE)
                if match:
                    result = match.group(1).strip()
                    
                    if exclusion_keywords:
                        context_start = max(0, match.start() - 50)
                        context_end = min(len(text), match.end() + 50)
                        context = text[context_start:context_end].lower()
                        
                        if any(excl.lower() in context for excl in exclusion_keywords):
                            logger.debug(f"Rejected {field_name} due to exclusion: {result}")
                            continue
                    
                    if field_name == "month_year":
                        result = self._format_month_year(result, text)
                    
                    if field_name == "name":
                        if len(result) < 10 or len(result) > 100 or '\n' in result:
                            logger.debug(f"Name result looks invalid: {repr(result)}, skipping")
                            continue
                    
                    return result
        
        for pattern in fallback_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    result = match.group(1).strip()
                    if field_name == "month_year" and match.lastindex == 2:
                        result = f"{match.group(1)} {match.group(2)}"
                except IndexError:
                    result = match.group(0).strip()
                
                if exclusion_keywords:
                    context_start = max(0, match.start() - 50)
                    context_end = min(len(text), match.end() + 50)
                    context = text[context_start:context_end].lower()
                    
                    if any(excl.lower() in context for excl in exclusion_keywords):
                        logger.debug(f"Rejected {field_name} due to exclusion: {result}")
                        continue
                
                if field_name == "name":
                    if len(result) < 10 or len(result) > 100 or '\n' in result:
                        logger.debug(f"Name result from fallback looks invalid: {repr(result)}, skipping")
                        continue
                    words = result.split()
                    if words and len(words[-1]) == 1:
                        logger.debug(f"Name has single letter at end: {repr(result)}, skipping")
                        continue
                
                if field_name == "month_year":
                    result = self._format_month_year(result, text)
                return result
        
        if field_name == "name":
            name_result = self._extract_name_from_text(text)
            if name_result:
                return name_result
        
        return None
    
    def _extract_name_from_text(self, text: str) -> Optional[str]:
        lines = text.split('\n')[:15]
        
        combined_text = ' '.join(lines)
        
        bin_match = re.search(r'([\w\s]+?)\s+(?:bin|binti)\s+([\w\s]+?)(?=\s+(?:no|ne|g|10|dabatan|jabatan)|$)', combined_text, re.IGNORECASE)
        
        if bin_match:
            first_part = bin_match.group(1).strip()
            second_part = bin_match.group(2).strip()
            
            first_words = [w for w in first_part.split() if w.isalpha()][:3]
            second_words = [w for w in second_part.split() if w.isalpha()][:2]
            
            if first_words and first_words[0].lower() in ['nana', 'nama', 'ne']:
                first_words = first_words[1:]
            
            if second_words and len(second_words[-1]) == 1:
                second_words = second_words[:-1]
            
            if first_words and second_words:
                first_name = ' '.join(w.capitalize() for w in first_words)
                last_name = ' '.join(w.capitalize() for w in second_words)
                full_name = f"{first_name} Bin {last_name}"
                logger.info(f"Extracted name: {full_name}")
                return full_name
        
        return None
        pattern = field_config.get("pattern")
        fallback_patterns = field_config.get("fallback_patterns", [])
        
        for keyword in keywords:
            if pattern:
                match = re.search(rf'{keyword}[:\s]*({pattern})', text, re.IGNORECASE)
                if match:
                    result = match.group(1).strip()
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
        value = value.strip()
        
        if re.match(r'^M/S\s*:\s*\d{1,2}/\d{1,2}$', value, re.IGNORECASE):
            match = re.search(r'(\d{1,2})/(\d{1,2})$', value)
            if match:
                potential_month = match.group(1)
                potential_day = match.group(2)
                
                year_match = re.search(r'\b(20\d{2})\b', full_text)
                if year_match:
                    year = year_match.group(1)
                    if 1 <= int(potential_month) <= 12:
                        month = potential_month.zfill(2)
                        return f"{month}/{year}"
                    elif 1 <= int(potential_day) <= 12 and int(potential_month) > 12:
                        month = potential_day.zfill(2)
                        return f"{month}/{year}"
                    else:
                        month = potential_month.zfill(2)
                        return f"{month}/{year}"
                else:
                    month = potential_month.zfill(2) if int(potential_month) <= 12 else potential_day.zfill(2)
                    return f"{month}/2025"
        
        if re.match(r'^\d{1,2}/\d{4}$', value):
            parts = value.split('/')
            month = parts[0].zfill(2)
            return f"{month}/{parts[1]}"
        
        if re.match(r'^\d{1,2}/\d{1,2}$', value):
            parts = value.split('/')
            potential_month = parts[0]
            potential_day = parts[1]
            
            year_match = re.search(r'\b(20\d{2})\b', full_text)
            if year_match:
                year = year_match.group(1)
                
                if 1 <= int(potential_month) <= 12:
                    month = potential_month.zfill(2)
                    return f"{month}/{year}"
                elif 1 <= int(potential_day) <= 12 and int(potential_month) > 12:
                    month = potential_day.zfill(2)
                    return f"{month}/{year}"
                else:
                    month = potential_month.zfill(2)
                    return f"{month}/{year}"
            else:
                month = potential_month.zfill(2) if int(potential_month) <= 12 else potential_day.zfill(2)
                return f"{month}/2025"
        
        if re.match(r'^\d{1,2}\s+\d{1,2}$', value):
            parts = value.split()
            potential_month = parts[0]
            potential_day = parts[1]
            
            year_match = re.search(r'\b(20\d{2})\b', full_text)
            if year_match:
                year = year_match.group(1)
                if 1 <= int(potential_month) <= 12:
                    month = potential_month.zfill(2)
                    return f"{month}/{year}"
                elif 1 <= int(potential_day) <= 12 and int(potential_month) > 12:
                    month = potential_day.zfill(2)
                    return f"{month}/{year}"
                else:
                    month = potential_month.zfill(2)
                    return f"{month}/{year}"
            else:
                month = potential_month.zfill(2) if int(potential_month) <= 12 else potential_day.zfill(2)
                return f"{month}/2025"
        
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
                year_match = re.search(r'\b(20\d{2})\b', full_text)
                if year_match:
                    return f"{month_num}/{year_match.group(1)}"
                return f"{month_num}/2025"
        
        return value
    
    def _extract_currency_field(self, text: str, field_name: str) -> Optional[str]:
        field_config = self.payslip_config.get(field_name, {})
        patterns = field_config.get("fallback_patterns", [])
        exclusion_keywords = field_config.get("exclusion_keywords", [])
        
        logger.info(f"=== DEBUGGING {field_name} ===")
        logger.info(f"Patterns count: {len(patterns)}")
        logger.info(f"Exclusion keywords: {exclusion_keywords}")
        
        for i, pattern in enumerate(patterns):
            logger.info(f"Trying pattern {i+1}: {pattern[:50]}...")
            matches = list(re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE))
            logger.info(f"Pattern {i+1} matches: {len(matches)}")
            
            for match in matches:
                try:
                    value_str = match.group(1).strip()
                    logger.info(f"Found value: {value_str}")
                except IndexError:
                    logger.info("IndexError - no group 1")
                    continue
                
                if value_str in self.used_tokens:
                    logger.info(f"Skipping already used token for {field_name}: {value_str}")
                    continue
                
                context_start = max(0, match.start() - 100)
                context_end = min(len(text), match.end() + 100)
                context = text[context_start:context_end].lower()
                
                logger.info(f"Context: {context[:100]}...")
                
                excluded = False
                for keyword in exclusion_keywords:
                    if keyword.lower() in context:
                        logger.info(f"Rejected {field_name} due to exclusion: {keyword}")
                        excluded = True
                        break
                
                if excluded:
                    continue
                
                self.used_tokens.add(value_str)
                logger.info(f"SUCCESS: Extracted {field_name}: {value_str} using pattern {i+1}")
                return value_str
        
        if field_name == "net_income":
            logger.info(f"Net income not found via regex - will calculate from gross - deduction")
            return None
        
        logger.info(f"Regex patterns failed, trying proximity-based extraction for {field_name}")
        proximity_result = self._extract_by_proximity_scanned(text, field_name)
        if proximity_result:
            logger.info(f"SUCCESS (proximity): Extracted {field_name}: {proximity_result}")
            return proximity_result
        
        logger.info(f"FAILED: No patterns matched for {field_name}")
        return None   
    
    def _extract_by_proximity_scanned(self, text: str, field_name: str) -> Optional[str]:
        field_config = self.payslip_config.get(field_name, {})
        keywords = field_config.get("keywords", [])
        
        if not keywords:
            return None
        
        lines = text.split('\n')
        
        for line_idx, line in enumerate(lines):
            line_lower = line.lower()
            
            for keyword in keywords:
                keyword_lower = keyword.lower()
                
                if keyword_lower in line_lower:
                    logger.debug(f"Found keyword '{keyword}' in line: {line}")
                    result = self._extract_number_from_nearby_lines(lines, line_idx, field_name)
                    if result:
                        return result
                
                if self._fuzzy_match(keyword_lower, line_lower, threshold=0.6):
                    logger.debug(f"Found fuzzy match for '{keyword}' in line: {line}")
                    result = self._extract_number_from_nearby_lines(lines, line_idx, field_name)
                    if result:
                        return result
        
        return None
    
    def _fuzzy_match(self, keyword: str, text: str, threshold: float = 0.6) -> bool:
        if len(keyword) < 3:
            return keyword in text
        
        keyword_chars = list(keyword)
        text_idx = 0
        matched = 0
        
        for char in keyword_chars:
            while text_idx < len(text) and text[text_idx] != char:
                text_idx += 1
            if text_idx < len(text):
                matched += 1
                text_idx += 1
        
        match_ratio = matched / len(keyword_chars)
        return match_ratio >= threshold
    
    def _extract_number_from_nearby_lines(self, lines: List[str], keyword_line_idx: int, field_name: str) -> Optional[str]:
        search_range = min(4, len(lines) - keyword_line_idx)
        
        for offset in range(search_range):
            line_idx = keyword_line_idx + offset
            if line_idx >= len(lines):
                break
            
            line = lines[line_idx]
            
            numbers = re.findall(r'[\d\s,\.]+', line)
            
            for num_str in numbers:
                numeric = self._parse_number(num_str)
                if numeric and numeric > 0 and numeric < 999999.99:
                    if numeric < 10 and len(num_str.replace(' ', '').replace(',', '').replace('.', '')) <= 2:
                        logger.debug(f"Skipping small number for {field_name}: {num_str}")
                        continue
                    
                    logger.info(f"Proximity extraction for {field_name}: {num_str} -> {numeric}")
                    return f"{numeric:.2f}"
        
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
            cleaned = value_str.replace(" ", "").replace(",", "").replace("RM", "").strip()
            cleaned = cleaned.replace("-", ".")
            return float(cleaned)
        except (ValueError, AttributeError):
            return None
    
    def _clean_currency(self, value: Optional[str]) -> str:
        if not value:
            return "0.00"
        
        try:
            original_value = value
            logger.info(f"Cleaning currency value: '{original_value}'")
            
            if ' ' in value and any(c.isdigit() for c in value):
                parts = value.strip().split()
                if len(parts) == 2 and all(any(c.isdigit() for c in part) for part in parts):
                    second_part_clean = parts[1].replace(',', '').replace('.', '')
                    if len(second_part_clean) <= 2 and second_part_clean.isdigit():
                        dollars = parts[0].replace(',', '').replace('.', '')
                        cents = second_part_clean
                        value = f"{dollars}.{cents.zfill(2)}"
                        logger.info(f"Converted spaced format: '{original_value}' -> '{value}'")
                    else:
                        value = ''.join(parts)
                        logger.info(f"Joined spaced numbers: '{original_value}' -> '{value}'")
            
            cleaned = value.replace(" ", "").replace("RM", "").strip()
            
            if cleaned.count(',') > 1:
                parts = cleaned.split(',')
                if len(parts[-1]) <= 2:
                    cleaned = ''.join(parts[:-1]) + '.' + parts[-1]
                else:
                    cleaned = ''.join(parts)
                logger.info(f"Handled multiple commas: '{original_value}' -> '{cleaned}'")
            elif '.' in cleaned and ',' in cleaned:
                last_dot = cleaned.rfind('.')
                last_comma = cleaned.rfind(',')
                
                if last_dot > last_comma:
                    cleaned = cleaned.replace(',', '')
                else:
                    cleaned = cleaned.replace('.', '').replace(',', '.')
            elif ',' in cleaned and cleaned.count(',') == 1:
                parts = cleaned.split(',')
                if len(parts[1]) <= 2:
                    cleaned = cleaned.replace(',', '.')
                else:
                    cleaned = cleaned.replace(',', '')
            elif '.' in cleaned and cleaned.count('.') > 1:
                parts = cleaned.split('.')
                cleaned = ''.join(parts[:-1]) + '.' + parts[-1]
            
            cleaned = cleaned.replace("-", ".")
            
            if '.' not in cleaned and len(cleaned) > 2:
                if len(cleaned) >= 3:
                    cleaned = cleaned[:-2] + '.' + cleaned[-2:]
            
            numeric = float(cleaned)
            result = f"{numeric:.2f}"
            logger.info(f"Final cleaned value: '{original_value}' -> '{result}'")
            return result
        except (ValueError, AttributeError) as e:
            logger.warning(f"Failed to clean currency '{value}': {str(e)}")
            return "0.00"
    
    def calculate_confidence(self, extracted_data: Dict[str, Any]) -> float:
        core_fields = ["gross_income", "net_income", "total_deduction", "month_year"]
        optional_fields = ["name", "id_number"]
        
        filled_core = sum(1 for field in core_fields if extracted_data.get(field) and extracted_data.get(field) != "0.00")
        
        filled_optional = sum(1 for field in optional_fields if extracted_data.get(field) and extracted_data.get(field) not in [None, "", "0.00"])
        
        core_confidence = (filled_core / len(core_fields)) * 0.8
        
        optional_confidence = (filled_optional / len(optional_fields)) * 0.2
        
        total_confidence = core_confidence + optional_confidence
        
        logger.info(f"Payslip confidence: {total_confidence:.2f} (core: {filled_core}/{len(core_fields)}, optional: {filled_optional}/{len(optional_fields)})")
        return round(total_confidence, 2)
