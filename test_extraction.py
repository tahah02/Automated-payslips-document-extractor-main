import sys
sys.path.insert(0, '.')

from extractors.payslip_extractor import PayslipExtractor
import pdfplumber

test_text = """No Siri : 01631
PENYATA GAJI BULANAN
HAPPY CHINESE NEW YEAR
Nama : MUHAMMAD ASRI BIN IDRIS Bulan : JANUARI 2025
No Gaji : 266006 Pusat : 0076
No KP : 810614045225 Pejabat : BAHAGIAN KAWALAN KREDIT
PENDAPATAN AMAUN (RM) POTONGAN AMAUN (RM)
GAJI POKOK 4,414.34 BADAN UGAMA/KEBAJIKN 3.00
BANTUAN SARA HIDUP 350.00 KESATUAN PEG MARA 5.00
IMB TETAP PERUMAHAN 300.00 BIRO ANGKASA 909.00
ELAUN KHIDMAT AWAM 160.00 TABUNG HAJI 30.00
KOPERASI BUMIRA BHD 506.50
KHAIRAT - 10 PENERIMA 20.00
SEWA LETAK KERETA 35.00
Jumlah Pendapatan : 5,224.34 Jumlah Potongan : 1,508.50
Gaji Bersih : 3,715.84
Peratus Gaji Bersih : 71.70%
Caruman Majikan
KWSP/ Pencen : 772.51
SOCSO :
Bank : CIMB No. Akaun : 13020103723527
GAJI ANDA ADALAH DIBAYAR MELALUI BANK PADA 22/01/2025
M/S : 1/22"""

print("Testing Payslip Extraction...")
print("=" * 60)

extractor = PayslipExtractor()

pdf_path = "uploads/raw/0a7b77ca-fa92-4565-9a5a-964c2413e254.pdf"
try:
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]
        text = page.extract_text()
        result = extractor.extract_payslip_fields(text, tokens=None, page=page)
        
        print("\nExtraction Results:")
        print("-" * 60)
        for key, value in result.items():
            print(f"{key:20s}: {value}")
        
        confidence = extractor.calculate_confidence(result)
        print(f"\nConfidence Score: {confidence}")
        
except FileNotFoundError:
    print(f"PDF file not found: {pdf_path}")
    print("\nTesting with text only...")
    result = extractor.extract_payslip_fields(test_text, tokens=None, page=None)
    
    print("\nExtraction Results:")
    print("-" * 60)
    for key, value in result.items():
        print(f"{key:20s}: {value}")
    
    confidence = extractor.calculate_confidence(result)
    print(f"\nConfidence Score: {confidence}")

print("\n" + "=" * 60)
print("Expected values:")
print("  name              : MUHAMMAD ASRI BIN IDRIS")
print("  id_number         : 810614045225")
print("  gross_income      : 5224.34")
print("  total_deduction   : 1508.50")
print("  net_income        : 3715.84")
print("  month_year        : 01/2025")
