import logging
import cv2
import numpy as np
from typing import Optional, Dict, Any
from pathlib import Path
from core.config import load_json, PREPROCESSING_CONFIG_FILE

logger = logging.getLogger(__name__)


class ScannedPDFOptimizer:    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        if config is None:
            full_config = load_json(PREPROCESSING_CONFIG_FILE)
            self.config = full_config.get('preprocessing', {})
        else:
            self.config = config.get('preprocessing', {})
        
        self.steps_config = self.config.get('steps', {})
        self.enabled = self.config.get('enabled', True)
        
        deskew_cfg = self.steps_config.get('deskew', {})
        self.deskew_enabled = deskew_cfg.get('enabled', True)
        self.deskew_angle_threshold = deskew_cfg.get('angle_threshold', 0.5)
        self.deskew_max_angle = deskew_cfg.get('max_angle', 45)
        
        contrast_cfg = self.steps_config.get('contrast_enhancement', {})
        self.contrast_enabled = contrast_cfg.get('enabled', True)
        self.clahe_clip_limit = contrast_cfg.get('clahe_clip_limit', 2.0)
        self.clahe_tile_size = tuple(contrast_cfg.get('clahe_tile_grid_size', [8, 8]))
        
        denoise_cfg = self.steps_config.get('denoise', {})
        self.denoise_enabled = denoise_cfg.get('enabled', True)
        self.bilateral_d = denoise_cfg.get('bilateral_d', 9)
        self.bilateral_sigma_color = denoise_cfg.get('bilateral_sigma_color', 75)
        self.bilateral_sigma_space = denoise_cfg.get('bilateral_sigma_space', 75)
        
        logger.info(f"ScannedPDFOptimizer initialized - Enabled: {self.enabled}, Deskew: {self.deskew_enabled}, Contrast: {self.contrast_enabled}, Denoise: {self.denoise_enabled}")
    
    def optimize_image(self, image_path: str, adaptive: bool = True) -> np.ndarray:
        try:
            image = cv2.imread(image_path)
            if image is None:
                logger.error(f"Failed to read image: {image_path}")
                return None
            
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            if self.enabled:
                if self.deskew_enabled:
                    gray = self._deskew(gray)
                
                if self.contrast_enabled:
                    gray = self._enhance_contrast(gray)
                
                if self.denoise_enabled:
                    gray = self._denoise(gray)
            else:
                logger.info("Preprocessing disabled in config")
            
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
                if abs(angle) < self.deskew_max_angle:
                    angles.append(angle)
            
            if not angles:
                return image
            
            avg_angle = np.median(angles)
            
            if abs(avg_angle) > self.deskew_angle_threshold:
                h, w = image.shape
                center = (w // 2, h // 2)
                rotation_matrix = cv2.getRotationMatrix2D(center, avg_angle, 1.0)
                image = cv2.warpAffine(image, rotation_matrix, (w, h), borderMode=cv2.BORDER_REPLICATE)
                logger.debug(f"Deskewed image by {avg_angle:.2f} degrees")
            
            return image
            
        except Exception as e:
            logger.warning(f"Deskew failed: {str(e)}")
            return image
    
    def _enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        try:
            clahe = cv2.createCLAHE(clipLimit=self.clahe_clip_limit, tileGridSize=self.clahe_tile_size)
            enhanced = clahe.apply(image)
            logger.debug(f"Contrast enhanced - clip={self.clahe_clip_limit}, tile={self.clahe_tile_size}")
            return enhanced
        except Exception as e:
            logger.warning(f"Contrast enhancement failed: {str(e)}")
            return image
    
    def _denoise(self, image: np.ndarray) -> np.ndarray:
        try:
            denoised = cv2.bilateralFilter(image, self.bilateral_d, self.bilateral_sigma_color, self.bilateral_sigma_space)
            logger.debug(f"Denoised - d={self.bilateral_d}, sigma_color={self.bilateral_sigma_color}, sigma_space={self.bilateral_sigma_space}")
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
            optimal_dpi = 400
        elif quality < 0.6:
            optimal_dpi = 300
        else:
            optimal_dpi = 200
        
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
