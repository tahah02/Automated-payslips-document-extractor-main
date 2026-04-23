import logging
import cv2
import numpy as np
from typing import Tuple, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ScannedPDFOptimizer:    
    def __init__(self):
        self.blur_kernel = (5, 5)
        self.morph_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    
    def optimize_image(self, image_path: str, adaptive: bool = True) -> np.ndarray:
        try:
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"Failed to read image: {image_path}")
                return None
            
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            gray = self._deskew(gray)
            
            
            gray = self._enhance_contrast(gray)
            
            gray = self._denoise(gray)
            
            
            logger.info(f"Image optimization completed: {image_path}")
            return gray
            
        except Exception as e:
            logger.error(f"Image optimization failed: {str(e)}")
            return None
    
    def _deskew(self, image: np.ndarray) -> np.ndarray:
        try:
            edges = cv2.Canny(image, 50, 150)
            lines = cv2.HoughLines(edges, 1, np.pi / 180, 100)
            
            if lines is None or len(lines) == 0:
                return image
            
            angles = []
            for line in lines[:20]: 
                rho, theta = line[0]
                angle = np.degrees(theta) - 90
                if abs(angle) < 45: 
                    angles.append(angle)
            
            if not angles:
                return image
            
            avg_angle = np.median(angles)
            
            if abs(avg_angle) > 0.5:
                h, w = image.shape
                center = (w // 2, h // 2)
                rotation_matrix = cv2.getRotationMatrix2D(center, avg_angle, 1.0)
                image = cv2.warpAffine(image, rotation_matrix, (w, h), 
                                      borderMode=cv2.BORDER_REPLICATE)
                logger.debug(f"Deskewed image by {avg_angle:.2f} degrees")
            
            return image
            
        except Exception as e:
            logger.warning(f"Deskew failed: {str(e)}, continuing without deskew")
            return image
    
    def _enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        try:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(image)
            logger.debug("Contrast enhanced using CLAHE")
            return enhanced
        except Exception as e:
            logger.warning(f"Contrast enhancement failed: {str(e)}")
            return image
    
    def _denoise(self, image: np.ndarray) -> np.ndarray:
        try:
            denoised = cv2.bilateralFilter(image, 9, 75, 75)
            logger.debug("Image denoised")
            return denoised
        except Exception as e:
            logger.warning(f"Denoising failed: {str(e)}")
            return image
    
    def _binarize(self, image: np.ndarray) -> np.ndarray:
        try:
            _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            logger.debug("Image binarized")
            return binary
        except Exception as e:
            logger.warning(f"Binarization failed: {str(e)}")
            return image
    
    def estimate_quality(self, image: np.ndarray) -> float:
        try:
            laplacian_var = cv2.Laplacian(image, cv2.CV_64F).var()
            
            quality = min(1.0, laplacian_var / 500.0)
            
            logger.debug(f"Image quality score: {quality:.2f}")
            return quality
            
        except Exception as e:
            logger.warning(f"Quality estimation failed: {str(e)}")
            return 0.5
    
    def get_optimal_dpi(self, image: np.ndarray, base_dpi: int = 300) -> int:
        quality = self.estimate_quality(image)
        
        if quality < 0.3:
            optimal_dpi = 400  # Very poor quality, use high DPI
        elif quality < 0.6:
            optimal_dpi = 300  # Poor quality
        else:
            optimal_dpi = 200  # Good quality, can use lower DPI for speed
        
        logger.info(f"Optimal DPI: {optimal_dpi} (quality: {quality:.2f})")
        return optimal_dpi
    
    def save_optimized_image(self, image: np.ndarray, output_path: str) -> bool:
        try:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(output_path, image)
            logger.info(f"Optimized image saved: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save optimized image: {str(e)}")
            return False
