import json
from typing import Dict, Any, List
import numpy as np

def safe_parse_json(text: str) -> Dict:
    """Safely parse LLM output into a dictionary."""
    if not text:
        return {}
    
    text = text.strip()
    
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    
    if text.endswith("```"):
        text = text[:-3]
    
    text = text.strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end+1])
            except:
                return {}
        return {}


def attribute_exact_match(pred: Dict, gold: Dict, fields: List[str] = None) -> Dict[str, float]:
    if fields is None:
        fields = ["brand", "color", "product_type", "style", "material", "model_number"]
    
    results = {}
    for field in fields:
        p = str(pred.get(field, "")).lower().strip() if pred.get(field) else ""
        g = str(gold.get(field, "")).lower().strip() if gold.get(field) else ""
        results[field] = 1.0 if p == g and p != "" else 0.0
    
    results["overall"] = float(np.mean(list(results.values()))) if results else 0.0
    return results


def evaluate_batch(predictions: List[Dict], golds: List[Dict]) -> Dict:
    scores = []
    for pred, gold in zip(predictions, golds):
        scores.append(attribute_exact_match(pred, gold))
    
    avg = {}
    if scores:
        for key in scores[0].keys():
            avg[key] = float(np.mean([s[key] for s in scores]))
    return avg