from typing import List, Dict
import json

def zero_shot_prompt(item_name: str, bullet_points: str) -> str:
    return f"""Extract the following attributes from the product information and return ONLY a valid JSON object.

Attributes to extract:
- brand
- color
- product_type
- style
- material
- model_number
- key_features (list of strings)

Product Title: {item_name}
Bullet Points: {bullet_points}

Return only the JSON object, no extra text.
"""

def few_shot_prompt(item_name: str, bullet_points: str, examples: List[Dict]) -> str:
    example_text = ""
    for i, ex in enumerate(examples, 1):
        example_text += f"""
Example {i}:
Title: {ex['item_name']}
Bullets: {ex['bullet_points']}
Output: {json.dumps(ex['gold'], ensure_ascii=False)}
"""
    
    return f"""Extract product attributes into a JSON object. Follow the examples carefully.

{example_text}

Now extract for this product:
Title: {item_name}
Bullets: {bullet_points}

Return ONLY the JSON object.
"""

def cot_prompt(item_name: str, bullet_points: str) -> str:
    return f"""Extract product attributes step by step.

Product Title: {item_name}
Bullet Points: {bullet_points}

Think step by step:
1. Identify the brand
2. Identify the color
3. Identify the product type
4. Identify style
5. Identify material
6. Identify model number
7. List 2-4 key features

After reasoning, return ONLY the final JSON object with keys:
brand, color, product_type, style, material, model_number, key_features
"""

def structured_prompt(item_name: str, bullet_points: str) -> str:
    return f"""You are a product attribute extraction expert.

Extract attributes and return a JSON object that strictly follows this schema:

{{
  "brand": "string or null",
  "color": "string or null",
  "product_type": "string or null",
  "style": "string or null",
  "material": "string or null",
  "model_number": "string or null",
  "key_features": ["string"]
}}

Product Title: {item_name}
Bullet Points: {bullet_points}

Return ONLY valid JSON. No explanation.
"""