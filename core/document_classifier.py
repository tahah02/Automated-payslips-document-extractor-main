import json
import logging
from typing import Tuple, List
from pathlib import Path

logger = logging.getLogger(__name__)


class DocumentClassifier:
    
    BANK_STATEMENT_KEYWORDS = []
    PAYSLIP_KEYWORDS = []
    
    @classmethod
    def _load_keywords(cls):
        if cls.BANK_STATEMENT_KEYWORDS and cls.PAYSLIP_KEYWORDS:
            return
        
        config_path = Path("config/document_classification_config.json")
        
        try:
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    cls.BANK_STATEMENT_KEYWORDS = config.get('bank_statement_keywords', [])
                    cls.PAYSLIP_KEYWORDS = config.get('payslip_keywords', [])
                    logger.info(f"Loaded {len(cls.BANK_STATEMENT_KEYWORDS)} bank statement keywords and {len(cls.PAYSLIP_KEYWORDS)} payslip keywords from config")
            else:
                logger.warning(f"Config file not found: {config_path}, using empty keyword lists")
                cls.BANK_STATEMENT_KEYWORDS = []
                cls.PAYSLIP_KEYWORDS = []
        except Exception as e:
            logger.error(f"Error loading classification config: {str(e)}")
            cls.BANK_STATEMENT_KEYWORDS = []
            cls.PAYSLIP_KEYWORDS = []
    
    @staticmethod
    def classify(text: str) -> Tuple[str, float]:
        DocumentClassifier._load_keywords()
        
        if not text:
            logger.warning("Empty text provided for classification")
            return "unknown", 0.0
        
        text_lower = text.lower()
        text_no_spaces = text_lower.replace(' ', '')
        
        bank_score = 0
        payslip_score = 0
        
        for keyword in DocumentClassifier.BANK_STATEMENT_KEYWORDS:
            keyword_lower = keyword.lower()
            if keyword_lower in text_lower or keyword_lower.replace(' ', '') in text_no_spaces:
                bank_score += 1
                logger.debug(f"Found bank keyword: {keyword}")
        
        for keyword in DocumentClassifier.PAYSLIP_KEYWORDS:
            keyword_lower = keyword.lower()
            if keyword_lower in text_lower or keyword_lower.replace(' ', '') in text_no_spaces:
                payslip_score += 1
                logger.debug(f"Found payslip keyword: {keyword}")
        
        logger.info(f"Classification scores - Bank: {bank_score}, Payslip: {payslip_score}")
        
        total_score = bank_score + payslip_score
        
        if total_score == 0:
            logger.warning("No keywords matched - unable to classify document")
            return "unknown", 0.0
        
        if bank_score > payslip_score:
            confidence = bank_score / total_score
            document_type = "bank_statement"
            logger.info(f"Classified as BANK STATEMENT (confidence: {confidence:.2f})")
            return document_type, round(confidence, 2)
        elif payslip_score > bank_score:
            confidence = payslip_score / total_score
            document_type = "payslip"
            logger.info(f"Classified as PAYSLIP (confidence: {confidence:.2f})")
            return document_type, round(confidence, 2)
        else:
            logger.warning("Equal scores - defaulting to bank_statement with low confidence")
            return "bank_statement", 0.5
    
    @staticmethod
    def is_bank_statement(text: str) -> bool:
        doc_type, confidence = DocumentClassifier.classify(text)
        return doc_type == "bank_statement" and confidence > 0.5
    
    @staticmethod
    def is_payslip(text: str) -> bool:
        doc_type, confidence = DocumentClassifier.classify(text)
        return doc_type == "payslip" and confidence > 0.5
