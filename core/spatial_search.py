import logging
import re
import re
from typing import List, Dict, Any, Optional, Tuple
from typing import List, Dict, Any, Optional, Tuple
from core.utils import parse_number, is_percentage_context
from core.utils import parse_number, is_percentage_context


logger = logging.getLogger(__name__)


class SpatialSearch:
    
    def __init__(self, config: Dict[str, Any], layout_analyzer):
        self.config = config
        self.layout_config = config.get('layout', {})
        self.scoring_config = config.get('scoring', {})
        self.layout_analyzer = layout_analyzer
    
    def should_merge_tokens(self, token1: Dict[str, Any], token2: Dict[str, Any]) -> bool:
        merge_only_numeric = self.layout_config.get('merge_only_numeric', True)
        
        if merge_only_numeric:
            numeric_punct_pattern = r'^[\d,.\s\-]+$'
            if not (re.match(numeric_punct_pattern, token1['text']) and 
                    re.match(numeric_punct_pattern, token2['text'])):
                return False
        
        merge_distance = self.layout_config.get('token_merge_distance', 10)
        horizontal_gap = token2['x0'] - token1['x1']
        
        if horizontal_gap > merge_distance:
            return False
        
        y_tolerance = self.layout_config.get('same_line_tolerance', 5)
        y_center1 = (token1['y0'] + token1['y1']) / 2
        y_center2 = (token2['y0'] + token2['y1']) / 2
        
        if abs(y_center1 - y_center2) > y_tolerance:
            return False
        
        return True
    
    def merge_adjacent_tokens(self, tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not tokens:
            return []
        
        merged = []
        current_group = [tokens[0]]
        
        for i in range(1, len(tokens)):
            if self.should_merge_tokens(current_group[-1], tokens[i]):
                current_group.append(tokens[i])
            else:
                merged_token = self._create_merged_token(current_group)
                merged.append(merged_token)
                current_group = [tokens[i]]
        
        if current_group:
            merged_token = self._create_merged_token(current_group)
            merged.append(merged_token)
        
        return merged
    
    def _create_merged_token(self, tokens: List[Dict[str, Any]]) -> Dict[str, Any]:
        if len(tokens) == 1:
            return tokens[0]
        
        merged_text = ''.join(t['text'] for t in tokens)
        
        x0 = min(t['x0'] for t in tokens)
        y0 = min(t['y0'] for t in tokens)
        x1 = max(t['x1'] for t in tokens)
        y1 = max(t['y1'] for t in tokens)
        
        avg_confidence = sum(t['confidence'] for t in tokens) / len(tokens)
        
        return {
            'text': merged_text,
            'bbox': [x0, y0, x1, y1],
            'x0': x0,
            'y0': y0,
            'x1': x1,
            'y1': y1,
            'confidence': avg_confidence,
            'page': tokens[0]['page'],
            '_used_by': None,
            '_merged_from': len(tokens)
        }
    
    def find_right_neighbor(self, label_token: Dict[str, Any], line_tokens: List[Dict[str, Any]], 
                           field_name: str, exclusion_keywords: List[str] = None) -> Optional[Dict[str, Any]]:
        
        candidates = []
        
        for token in line_tokens:
            if token['x0'] <= label_token['x1']:
                continue
            
            if self.layout_analyzer.is_token_used(token):
                logger.debug(f"Token already used: {token['text']}")
                continue
            
            if not self._is_numeric_token(token['text']):
                continue
            
            if exclusion_keywords:
                context = label_token['text'] + ' ' + token['text']
                if any(kw in context.lower() for kw in exclusion_keywords):
                    logger.info(f"Rejected {field_name}: {token['text']} - exclusion keyword in context")
                    continue
            
            if is_percentage_context(token['text'], label_token['text']):
                logger.info(f"Rejected {field_name}: {token['text']} - percentage context detected")
                continue
            
            distance = token['x0'] - label_token['x1']
            score = self._calculate_candidate_score(token, distance, 'right_neighbor')
            
            candidates.append({
                'token': token,
                'score': score,
                'distance': distance,
                'relationship': 'right_neighbor'
            })
        
        if not candidates:
            return None
        
        candidates.sort(key=lambda c: c['score'], reverse=True)
        best = candidates[0]
        
        min_threshold = self.scoring_config.get('min_confidence_threshold', 0.5)
        if best['score'] < min_threshold:
            logger.info(f"Rejected {field_name}: best score {best['score']:.2f} below threshold {min_threshold}")
            return None
        
        logger.info(f"Chosen {field_name}: {best['token']['text']} - right-neighbor, score={best['score']:.2f}")
        return best['token']
    
    def find_below_label(self, label_token: Dict[str, Any], all_tokens: List[Dict[str, Any]], 
                        field_name: str, exclusion_keywords: List[str] = None) -> Optional[Dict[str, Any]]:
        
        vertical_tolerance = self.layout_config.get('vertical_tolerance', 50)
        candidates = []
        
        for token in all_tokens:
            if token['page'] != label_token['page']:
                continue
            
            if token['y0'] <= label_token['y1']:
                continue
            
            if token['y0'] - label_token['y1'] > vertical_tolerance:
                continue
            
            if self.layout_analyzer.is_token_used(token):
                continue
            
            if not self._is_numeric_token(token['text']):
                continue
            
            if exclusion_keywords:
                context = label_token['text'] + ' ' + token['text']
                if any(kw in context.lower() for kw in exclusion_keywords):
                    logger.info(f"Rejected {field_name}: {token['text']} - exclusion keyword")
                    continue
            
            if is_percentage_context(token['text'], label_token['text']):
                logger.info(f"Rejected {field_name}: {token['text']} - percentage context")
                continue
            
            distance = token['y0'] - label_token['y1']
            score = self._calculate_candidate_score(token, distance, 'below_label')
            
            candidates.append({
                'token': token,
                'score': score,
                'distance': distance,
                'relationship': 'below_label'
            })
        
        if not candidates:
            return None
        
        candidates.sort(key=lambda c: c['score'], reverse=True)
        best = candidates[0]
        
        min_threshold = self.scoring_config.get('min_confidence_threshold', 0.5)
        if best['score'] < min_threshold:
            logger.info(f"Rejected {field_name}: best score {best['score']:.2f} below threshold")
            return None
        
        logger.info(f"Chosen {field_name}: {best['token']['text']} - below-label, score={best['score']:.2f}")
        return best['token']
    
    def _is_numeric_token(self, text: str) -> bool:
        return parse_number(text) is not None
    
    def _calculate_candidate_score(self, token: Dict[str, Any], distance: float, relationship: str) -> float:
        weights = self.scoring_config.get('weights', {
            'ocr_confidence': 0.3,
            'regex_match': 0.3,
            'proximity': 0.25,
            'spatial_relationship': 0.15
        })
        
        ocr_score = token.get('confidence', 0.5)
        
        regex_score = 1.0 if self._is_numeric_token(token['text']) else 0.0
        
        max_distance = 200
        proximity_score = max(0, 1 - (distance / max_distance))
        
        spatial_score = 1.0 if relationship == 'right_neighbor' else 0.7
        
        total_score = (
            weights['ocr_confidence'] * ocr_score +
            weights['regex_match'] * regex_score +
            weights['proximity'] * proximity_score +
            weights['spatial_relationship'] * spatial_score
        )
        
        return total_score
    
    def find_label_token(self, tokens: List[Dict[str, Any]], keywords: List[str]) -> Optional[Dict[str, Any]]:
        for token in tokens:
            token_text_lower = token['text'].lower()
            for keyword in keywords:
                keyword_lower = keyword.lower()
                if keyword_lower in token_text_lower:
                    logger.debug(f"Found label token '{token['text']}' matching keyword '{keyword}'")
                    return token
        
        for token in tokens:
            token_text_lower = token['text'].lower().strip()
            for keyword in keywords:
                keyword_lower = keyword.lower().strip()
                if ' ' in keyword_lower:
                    first_word = keyword_lower.split()[0]
                    if token_text_lower == first_word or first_word in token_text_lower:
                        logger.debug(f"Found label token '{token['text']}' matching first word of '{keyword}'")
                        return token
        
        logger.debug(f"No label token found for keywords: {keywords}")
        return None
