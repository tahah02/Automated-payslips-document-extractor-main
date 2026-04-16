class BankDetector:
    
    BANK_PATTERNS = {
        'bsn': {
            'primary': ['BSN PENYATA AKAUN', 'BSN GIRO'],
            'secondary': ['BANK SIMPANAN NASIONAL'],
            'min_confidence': 0.9
        },
        'public_islamic': {
            'primary': ['PUBLIC ISLAMIC BANK'],
            'secondary': ['PUBLIC BANK BERHAD', 'publicislamicbank'],
            'min_confidence': 0.9
        },
        'bank_islam': {
            'primary': ['BANKCISLAM', 'BANK ISLAM'],
            'secondary': ['bankislam.com', 'Menara Bank Islam'],
            'min_confidence': 0.9
        },
        'cimb': {
            'primary': ['CIMB BANK', 'CIMB Bank Berhad'],
            'secondary': ['cimbbank.com', 'cimbclicks'],
            'min_confidence': 0.9
        }
    }
    
    @staticmethod
    def detect(text):
        text_upper = text.upper()
        
        for bank, patterns in BankDetector.BANK_PATTERNS.items():
            for keyword in patterns['primary']:
                if keyword.upper() in text_upper:
                    return bank, 1.0
            
            for keyword in patterns['secondary']:
                if keyword.upper() in text_upper:
                    return bank, 0.8
        
        return 'generic', 0.3
    
    @staticmethod
    def detect_from_pages(pages_text):
        if not pages_text:
            return 'generic', 0.3
        
        first_page = pages_text[0] if isinstance(pages_text, list) else pages_text
        return BankDetector.detect(first_page)
