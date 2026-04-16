import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ConfigLoader:
    _configs = {}
    
    @staticmethod
    def load_config(config_name: str, config_path: Optional[str] = None) -> Dict[str, Any]:
        if config_name in ConfigLoader._configs:
            return ConfigLoader._configs[config_name]
        
        if config_path is None:
            config_path = f"config/{config_name}.json"
        
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                logger.warning(f"Config file not found: {config_path}, using defaults")
                return {}
            
            with open(config_file, 'r') as f:
                config = json.load(f)
                ConfigLoader._configs[config_name] = config
                logger.info(f"Loaded config: {config_name}")
                return config
        except Exception as e:
            logger.error(f"Error loading config {config_name}: {str(e)}")
            return {}
    
    @staticmethod
    def get_ocr_config() -> Dict[str, Any]:
        config = ConfigLoader.load_config("ocr_config")
        return config.get("ocr", {})
    
    @staticmethod
    def get_extraction_config() -> Dict[str, Any]:
        config = ConfigLoader.load_config("extraction_config")
        return config.get("extraction", {})
    
    @staticmethod
    def get_engine_config() -> Dict[str, Any]:
        config = ConfigLoader.load_config("engine_config")
        return config.get("engine", {})
    
    @staticmethod
    def get_ocr_engine() -> str:
        ocr_config = ConfigLoader.get_ocr_config()
        return ocr_config.get("default_engine", "tesseract")
    
    @staticmethod
    def get_ocr_language() -> str:
        ocr_config = ConfigLoader.get_ocr_config()
        engine = ocr_config.get("default_engine", "tesseract")
        engine_config = ocr_config.get("engines", {}).get(engine, {})
        return engine_config.get("language", "msa")
    
    @staticmethod
    def get_extraction_fields() -> Dict[str, Any]:
        extraction_config = ConfigLoader.get_extraction_config()
        return extraction_config.get("fields", {})
    
    @staticmethod
    def get_validation_config() -> Dict[str, Any]:
        extraction_config = ConfigLoader.get_extraction_config()
        return extraction_config.get("validation", {})
    
    @staticmethod
    def get_processing_config() -> Dict[str, Any]:
        extraction_config = ConfigLoader.get_extraction_config()
        return extraction_config.get("processing", {})
    
    @staticmethod
    def get_server_config() -> Dict[str, Any]:
        engine_config = ConfigLoader.get_engine_config()
        return engine_config.get("server", {})
    
    @staticmethod
    def get_file_handling_config() -> Dict[str, Any]:
        engine_config = ConfigLoader.get_engine_config()
        return engine_config.get("file_handling", {})
    
    @staticmethod
    def get_logging_config() -> Dict[str, Any]:
        engine_config = ConfigLoader.get_engine_config()
        return engine_config.get("logging", {})
    
    @staticmethod
    def get_preprocessing_config() -> Dict[str, Any]:
        ocr_config = ConfigLoader.get_ocr_config()
        return ocr_config.get("preprocessing", {})
    
    @staticmethod
    def reload_all():
        ConfigLoader._configs.clear()
        logger.info("All configs reloaded")
