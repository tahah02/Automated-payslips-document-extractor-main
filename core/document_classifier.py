import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class DocumentClassifier:
    
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
    
    PAYSLIP_KEYWORDS = [
        'payslip', 'pay slip', 'slip gaji', 'penyata gaji',
        'salary', 'gaji', 'pendapatan', 'pondapatan', 'pondwpatan', 'pondopatan',
        'gross income', 'gross salary', 'jumlah pendapatan', 'junlah pendapatan', 'junlah pondapatan', 'jumlah pondwpatan', 'gaji kasar',
        'net income', 'net salary', 'gaji bersih', 'glji boraih', '0ji baralh', 'pendapatan bersih',
        'deduction', 'potongan', 'pcrorgan', 'paectjan',
        'epf', 'kwsp', 'kumpulan wang simpanan pekerja',
        'socso', 'perkeso', 'pertubuhan keselamatan sosial',
        'pcb', 'income tax', 'cukai pendapatan', 'cukul', 'cukez', 'cukii',
        'allowance', 'elaun',
        'overtime', 'kerja lebih masa',
        'basic salary', 'gaji pokok', 'gaji asas', 'gji fokck',
        'employee', 'pekerja', 'staff', 'kakitangan',
        'employer', 'majikan', 'company',
        'kerajaan malaysia', 'rerajaan malaysia', 'rerajun naliksia', 'kerrjian',
        'anm', 'jabatan', 'bomba', 'bompa', 'jeba',
        'bulan', 'dulah', 'dvlah',
        'pendiprtam', 'pendmprtin', 'pend patun'
    ]
    
    @staticmethod
    def classify(text: str) -> Tuple[str, float]:
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
