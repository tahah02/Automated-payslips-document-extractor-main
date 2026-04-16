import logging
from typing import List, Dict, Any, Optional, Tuple
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from collections import defaultdict


logger = logging.getLogger(__name__)


class LayoutAnalyzer:
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.layout_config = config.get('layout', {})
        
    def normalize_tolerance(self, tolerance: float, page_height: float) -> float:
        if self.layout_config.get('use_relative_tolerance', False):
            return (tolerance / 100) * page_height
        return tolerance
    
    def normalize_bbox(self, bbox: Any) -> List[float]:
        if isinstance(bbox, list):
            if len(bbox) == 4 and all(isinstance(x, (int, float)) for x in bbox):
                return bbox
            elif len(bbox) == 4 and all(isinstance(x, list) for x in bbox):
                x_coords = [p[0] for p in bbox]
                y_coords = [p[1] for p in bbox]
                return [min(x_coords), min(y_coords), max(x_coords), max(y_coords)]
        return [0, 0, 0, 0]
    
    def create_token(self, text: str, bbox: List[float], confidence: float, page: int = 0) -> Dict[str, Any]:
        normalized_bbox = self.normalize_bbox(bbox)
        return {
            'text': text,
            'bbox': normalized_bbox,
            'x0': normalized_bbox[0],
            'y0': normalized_bbox[1],
            'x1': normalized_bbox[2],
            'y1': normalized_bbox[3],
            'confidence': confidence,
            'page': page,
            '_used_by': None
        }
    
    def group_tokens_to_lines(self, tokens: List[Dict[str, Any]], page_height: Optional[float] = None) -> List[Dict[str, Any]]:
        if not tokens:
            return []
        
        if page_height is None:
            page_height = self.layout_config.get('default_page_height', 1000)
        
        y_tolerance = self.layout_config.get('same_line_tolerance', 5)
        y_tol = self.normalize_tolerance(y_tolerance, page_height)
        
        lines = []
        tokens_sorted = sorted(tokens, key=lambda t: (t['page'], t['y0'], t['x0']))
        
        for token in tokens_sorted:
            y_center = (token['y0'] + token['y1']) / 2
            placed = False
            
            for line in lines:
                if line['page'] != token['page']:
                    continue
                    
                line_y_center = (line['y_min'] + line['y_max']) / 2
                
                if abs(y_center - line_y_center) <= y_tol:
                    line['tokens'].append(token)
                    line['y_min'] = min(line['y_min'], token['y0'])
                    line['y_max'] = max(line['y_max'], token['y1'])
                    line['x_min'] = min(line['x_min'], token['x0'])
                    line['x_max'] = max(line['x_max'], token['x1'])
                    placed = True
                    break
            
            if not placed:
                lines.append({
                    'page': token['page'],
                    'y_min': token['y0'],
                    'y_max': token['y1'],
                    'x_min': token['x0'],
                    'x_max': token['x1'],
                    'tokens': [token]
                })
        
        for line in lines:
            line['tokens'] = sorted(line['tokens'], key=lambda t: t['x0'])
            line['y_center'] = (line['y_min'] + line['y_max']) / 2
        
        lines = sorted(lines, key=lambda l: (l['page'], l['y_min']))
        
        return lines
    
    def get_reading_order_tokens(self, tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        lines = self.group_tokens_to_lines(tokens)
        ordered_tokens = []
        
        for line in lines:
            ordered_tokens.extend(line['tokens'])
        
        return ordered_tokens
    
    def mark_token_used(self, token: Dict[str, Any], field_name: str):
        if self.layout_config.get('enable_token_consumption', True):
            token['_used_by'] = field_name
    
    def is_token_used(self, token: Dict[str, Any]) -> bool:
        if not self.layout_config.get('enable_token_consumption', True):
            return False
        return token.get('_used_by') is not None
    
    def get_token_center(self, token: Dict[str, Any]) -> Tuple[float, float]:
        x_center = (token['x0'] + token['x1']) / 2
        y_center = (token['y0'] + token['y1']) / 2
        return x_center, y_center
    
    def calculate_distance(self, token1: Dict[str, Any], token2: Dict[str, Any]) -> float:
        x1, y1 = self.get_token_center(token1)
        x2, y2 = self.get_token_center(token2)
        return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
