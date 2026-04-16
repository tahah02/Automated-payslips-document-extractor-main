import logging
from pathlib import Path
from typing import List


logger = logging.getLogger(__name__)

class PDFProcessor:
    
    @staticmethod
    def pdf_to_images(pdf_path: str, output_dir: str = "temp") -> List[str]:
        try:
            import fitz
            
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            pdf_document = fitz.open(pdf_path)
            image_paths = []
            
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                
                image_path = f"{output_dir}/page_{page_num + 1}.png"
                pix.save(image_path)
                image_paths.append(image_path)
                
                logger.info(f"Converted page {page_num + 1} to {image_path}")
            
            pdf_document.close()
            return image_paths
        
        except ImportError:
            logger.error("PyMuPDF not installed. Install with: pip install PyMuPDF")
            raise
        except Exception as e:
            logger.error(f"PDF conversion error: {str(e)}")
            raise
    
    @staticmethod
    def get_pdf_page_count(pdf_path: str) -> int:
        try:
            import fitz
            pdf_document = fitz.open(pdf_path)
            page_count = len(pdf_document)
            pdf_document.close()
            return page_count
        except Exception as e:
            logger.error(f"Error getting page count: {str(e)}")
            raise
