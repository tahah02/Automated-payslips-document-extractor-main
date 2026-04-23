import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CacheManager:
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = cache_dir
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        self.cache_index_path = f"{cache_dir}/cache_index.json"
        self.cache_index = self._load_cache_index()
    
    def _load_cache_index(self) -> Dict[str, Any]:
        if Path(self.cache_index_path).exists():
            try:
                with open(self.cache_index_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache index: {str(e)}")
                return {}
        return {}
    
    def _save_cache_index(self):
        try:
            with open(self.cache_index_path, 'w') as f:
                json.dump(self.cache_index, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache index: {str(e)}")
    
    def _calculate_file_hash(self, file_path: str) -> str:
        hash_obj = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    
    def get_cache_key(self, file_path: str) -> str:
        file_hash = self._calculate_file_hash(file_path)
        return file_hash
    
    def get_cached_result(self, file_path: str) -> Optional[Dict[str, Any]]:
        cache_key = self.get_cache_key(file_path)
        
        if cache_key not in self.cache_index:
            logger.info(f"Cache miss for {file_path}")
            return None
        
        cache_entry = self.cache_index[cache_key]
        cache_file = cache_entry.get('cache_file')
        timestamp = cache_entry.get('timestamp')
        
        if not Path(cache_file).exists():
            logger.warning(f"Cache file missing: {cache_file}")
            del self.cache_index[cache_key]
            self._save_cache_index()
            return None
        
        try:
            with open(cache_file, 'r') as f:
                result = json.load(f)
            logger.info(f"Cache hit for {file_path} (cached at {timestamp})")
            return result
        except Exception as e:
            logger.error(f"Failed to read cache file: {str(e)}")
            return None
    
    def save_result_to_cache(self, file_path: str, result: Dict[str, Any]) -> bool:
        try:
            cache_key = self.get_cache_key(file_path)
            cache_file = f"{self.cache_dir}/{cache_key}.json"
            
            with open(cache_file, 'w') as f:
                json.dump(result, f, indent=2)
            
            self.cache_index[cache_key] = {
                'cache_file': cache_file,
                'timestamp': datetime.now().isoformat(),
                'original_file': file_path
            }
            
            self._save_cache_index()
            logger.info(f"Result cached for {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to cache result: {str(e)}")
            return False
    
    def clear_old_cache(self, days: int = 7):
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            expired_keys = []
            
            for cache_key, entry in self.cache_index.items():
                timestamp_str = entry.get('timestamp')
                if timestamp_str:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    if timestamp < cutoff_time:
                        expired_keys.append(cache_key)
            
            for cache_key in expired_keys:
                cache_file = self.cache_index[cache_key].get('cache_file')
                if Path(cache_file).exists():
                    Path(cache_file).unlink()
                del self.cache_index[cache_key]
            
            self._save_cache_index()
            logger.info(f"Cleared {len(expired_keys)} expired cache entries")
        except Exception as e:
            logger.error(f"Failed to clear old cache: {str(e)}")
    
    def clear_all_cache(self):
        try:
            for cache_key in list(self.cache_index.keys()):
                cache_file = self.cache_index[cache_key].get('cache_file')
                if Path(cache_file).exists():
                    Path(cache_file).unlink()
            
            self.cache_index = {}
            self._save_cache_index()
            logger.info("All cache cleared")
        except Exception as e:
            logger.error(f"Failed to clear cache: {str(e)}")
