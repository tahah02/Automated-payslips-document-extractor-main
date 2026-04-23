import os
import json
import json
from typing import Any, Dict, Optional
from typing import Any, Dict, Optional
import logging
import logging
from datetime import datetime
from datetime import datetime


logger = logging.getLogger(__name__)

BASE_PATH = os.path.join(os.path.dirname(__file__), "..", "config")
BASE_CONFIG_FILE = os.path.join(BASE_PATH, "pipeline_config.json")
EXTRACTION_CONFIG_FILE = os.path.join(BASE_PATH, "extraction_config.json")
OCR_CONFIG_FILE = os.path.join(BASE_PATH, "ocr_config.json")
PREPROCESSING_CONFIG_FILE = os.path.join(BASE_PATH, "preprocessing_config.json")

_CONFIG_CACHE: Dict[str, Dict[str, Any]] = {}

def load_json(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Config file not found: {path}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {path}: {str(e)}")
        return {}

def merge_safe(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = base.copy()
    for k, v in override.items():
        if isinstance(v, list):
            out[k] = v
        elif isinstance(v, dict) and k in out and isinstance(out[k], dict):
            out[k] = merge_safe(out[k], v)
        else:
            out[k] = v
    return out

def check_version_compatibility(config: Dict) -> bool:
    config_version = config.get("config_version")
    schema_version = config.get("schema_version")
    
    if not config_version or not schema_version:
        logger.error("Missing version fields in config")
        return False
    
    major_version = config_version.split('.')[0]
    schema_major = schema_version.split('.')[0]
    
    if major_version != schema_major:
        logger.error(f"Incompatible versions: config={config_version}, schema={schema_version}")
        return False
    
    return True

def load_config(template: Optional[str] = None) -> Dict[str, Any]:
    base = load_json(BASE_CONFIG_FILE)
    
    if not check_version_compatibility(base):
        logger.warning("Version compatibility check failed, using config anyway")
    
    extraction = load_json(EXTRACTION_CONFIG_FILE)
    if extraction:
        base["extraction_fields"] = extraction
    
    ocr = load_json(OCR_CONFIG_FILE)
    if ocr:
        base["ocr"] = ocr
    
    if template:
        tmpl_file = os.path.join(BASE_PATH, "templates", f"{template}.json")
        if os.path.exists(tmpl_file):
            logger.info(f"Loading template config: {template}")
            tmpl = load_json(tmpl_file)
            if check_version_compatibility(tmpl):
                base = merge_safe(base, tmpl)
            else:
                logger.warning(f"Template {template} version incompatible, skipping")
        else:
            logger.warning(f"Template config not found: {tmpl_file}")
    
    max_upload = os.getenv("API_MAX_UPLOAD_MB")
    if max_upload:
        base.setdefault("api", {})["max_upload_mb"] = int(max_upload)
    
    ocr_engine = os.getenv("OCR_ENGINE")
    if ocr_engine:
        base.setdefault("ocr", {})["engine"] = ocr_engine
    
    confidence_threshold = os.getenv("MIN_CONFIDENCE_SCORE")
    if confidence_threshold:
        base.setdefault("confidence", {})["min_score"] = float(confidence_threshold)
    
    return base

def get_config(template: Optional[str] = None, reload: bool = False) -> Dict[str, Any]:
    cache_key = template or "default"
    
    if reload or cache_key not in _CONFIG_CACHE:
        _CONFIG_CACHE[cache_key] = load_config(template)
    
    return _CONFIG_CACHE[cache_key]

def reload_config_safe(template: Optional[str] = None, actor: str = "system") -> Dict[str, Any]:
    cache_key = template or "default"
    old_config = _CONFIG_CACHE.get(cache_key, {})
    old_version = old_config.get("config_version", "unknown")
    
    try:
        new_config = load_config(template)
        
        if not check_version_compatibility(new_config):
            raise ValueError("Version compatibility check failed")
        
        new_version = new_config.get("config_version")
        
        new_config["reload_metadata"] = {
            "actor": actor,
            "timestamp": datetime.now().isoformat(),
            "previous_version": old_version
        }
        
        _CONFIG_CACHE[cache_key] = new_config
        logger.info(f"Config reloaded: {old_version} → {new_version} by {actor}")
        
        return new_config
        
    except Exception as e:
        logger.error(f"Config reload failed: {str(e)}")
        raise

def get_classification_config(template: Optional[str] = None) -> Dict[str, Any]:
    config = get_config(template)
    return config.get("classification", {})

def get_confidence_config(template: Optional[str] = None) -> Dict[str, Any]:
    config = get_config(template)
    return config.get("confidence", {})

def get_validation_config(template: Optional[str] = None) -> Dict[str, Any]:
    config = get_config(template)
    return config.get("validation", {})

def get_proximity_config(template: Optional[str] = None) -> Dict[str, Any]:
    config = get_config(template)
    return config.get("proximity", {})

def get_table_config(template: Optional[str] = None) -> Dict[str, Any]:
    config = get_config(template)
    return config.get("table_extraction", {})

def get_pdf_mode_config(template: Optional[str] = None) -> Dict[str, Any]:
    config = get_config(template)
    return config.get("pdf_mode_detection", {})

def get_extraction_config(template: Optional[str] = None) -> Dict[str, Any]:
    config = get_config(template)
    return config.get("extraction", {})

def get_text_constraints_config(template: Optional[str] = None) -> Dict[str, Any]:
    config = get_config(template)
    return config.get("text_constraints", {})

def get_feature_flags(template: Optional[str] = None) -> Dict[str, Any]:
    config = get_config(template)
    return config.get("features", {})
