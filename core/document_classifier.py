import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class DocumentClassifier:
    """
    Simple keyword-based document classifier to distinguish between
    bank statements and payslips.
    """
    
    # Keywords that indicate a bank statement
    BANK_STATEMENT_KEYWORDS = [
        'account number', 'account no', 'nombor akaun', 'no akaun',
        'statement date', 'tarikh penyata', 'penyata akaun',
        'opening balance', 'closing balance', 'baki pembukaan', 'baki penutup',
        'total debit', 'total credit', 'jumlah debit', 'jumlah kredit',
        'transaction', 'transaksi', 'urus niaga',
        'statement period', 'tempoh penyata',
        'available balance', 'baki sedia ada',
        'bank statement', 'penyata bank',
        'current account', 'savings account', 'akaun semasa', 'akaun simpanan'
    ]
    
    # Keywords that indicate a payslip
    PAYSLIP_KEYWORDS = [
        'payslip', 'pay slip', 'slip gaji', 'penyata gaji',
        'salary', 'gaji', 'pendapatan',
        'gross income', 'gross salary', 'jumlah pendapatan', 'gaji kasar',
        'net income', 'net salary', 'gaji bersih', 'pendapatan bersih',
        'deduction', 'potongan',
        'epf', 'kwsp', 'kumpulan wang simpanan pekerja',
        'socso', 'perkeso', 'pertubuhan keselamatan sosial',
        'pcb', 'income tax', 'cukai pendapatan',
        'allowance', 'elaun',
        'overtime', 'kerja lebih masa',
        'basic salary', 'gaji pokok', 'gaji asas',
        'employee', 'pekerja', 'staff', 'kakitangan',
        'employer', 'majikan', 'company'
    ]
    
    @staticmethod
    def classify(text: str) -> Tuple[str, float]:
        """
        Classify document as 'bank_statement' or 'payslip' based on keyword matching.
        
        Args:
            text: Extracted text from document
            
        Returns:
            Tuple of (document_type, confidence_score)
            - document_type: 'bank_statement' or 'payslip'
            - confidence_score: 0.0 to 1.0
        """
        if not text:
            logger.warning("Empty text provided for classification")
            return "unknown", 0.0
        
        # Convert to lowercase for case-insensitive matching
        text_lower = text.lower()
        
        # Count keyword matches
        bank_score = 0
        payslip_score = 0
        
        # Count bank statement keywords
        for keyword in DocumentClassifier.BANK_STATEMENT_KEYWORDS:
            if keyword.lower() in text_lower:
                bank_score += 1
                logger.debug(f"Found bank keyword: {keyword}")
        
        # Count payslip keywords
        for keyword in DocumentClassifier.PAYSLIP_KEYWORDS:
            if keyword.lower() in text_lower:
                payslip_score += 1
                logger.debug(f"Found payslip keyword: {keyword}")
        
        logger.info(f"Classification scores - Bank: {bank_score}, Payslip: {payslip_score}")
        
        # Determine document type
        total_score = bank_score + payslip_score
        
        if total_score == 0:
            logger.warning("No keywords matched - unable to classify document")
            return "unknown", 0.0
        
        # Calculate confidence based on score difference
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
            # Equal scores - default to bank statement with low confidence
            logger.warning("Equal scores - defaulting to bank_statement with low confidence")
            return "bank_statement", 0.5
    
    @staticmethod
    def is_bank_statement(text: str) -> bool:
        """
        Check if document is a bank statement.
        
        Args:
            text: Extracted text from document
            
        Returns:
            True if classified as bank statement, False otherwise
        """
        doc_type, confidence = DocumentClassifier.classify(text)
        return doc_type == "bank_statement" and confidence > 0.5
    
    @staticmethod
    def is_payslip(text: str) -> bool:
        """
        Check if document is a payslip.
        
        Args:
            text: Extracted text from document
            
        Returns:
            True if classified as payslip, False otherwise
        """
        doc_type, confidence = DocumentClassifier.classify(text)
        return doc_type == "payslip" and confidence > 0.5
