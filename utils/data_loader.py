import pandas as pd
import json
from typing import List, Dict, Any

def load_data(path: str = "data/final_clean_amazon.jsonl") -> pd.DataFrame:
    df = pd.read_json(path, lines=True)
    return df

def prepare_examples(df: pd.DataFrame, n: int = 5) -> List[Dict]:
    """Prepare few-shot examples"""
    examples = []
    sample = df.sample(n=min(n, len(df)), random_state=42)
    
    for _, row in sample.iterrows():
        examples.append({
            "item_name": row["item_name"],
            "bullet_points": row["bullet_points_text"],
            "gold": {
                "brand": row.get("brand"),
                "color": row.get("color"),
                "product_type": row.get("product_type"),
                "style": row.get("style"),
                "material": row.get("material"),
                "model_number": row.get("model_number"),
                "key_features": row.get("bullet_points", [])[:3]  # simple approximation
            }
        })
    return examples