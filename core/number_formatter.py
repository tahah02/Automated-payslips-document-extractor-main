import re

class NumberFormatter:
    
    @staticmethod
    def normalize(value_str, bank_type='generic'):
        if not value_str or not isinstance(value_str, str):
            return 0.0
        
        value_str = value_str.strip()
        
        if not value_str:
            return 0.0
        
        if bank_type == 'bsn':
            if value_str.count('.') > 1:
                parts = value_str.rsplit('.', 1)
                thousands = parts[0].replace('.', '')
                decimal = parts[1] if len(parts) > 1 else '00'
                value_str = f"{thousands}.{decimal}"
            elif ',' in value_str:
                value_str = value_str.replace(',', '')
        else:
            value_str = value_str.replace(',', '')
        
        try:
            return float(value_str)
        except ValueError:
            return 0.0
    
    @staticmethod
    def extract_number(text, pattern=None):
        if not pattern:
            pattern = r'[\d,\.]+\.?\d{0,2}'
        
        match = re.search(pattern, text)
        if match:
            return match.group(0)
        return None
