import json
FIELDS=("brand","color","product_type","style","material","model_number")
def _prompt(instruction,title,bullets):
    schema=json.dumps({k:None for k in FIELDS})
    return (instruction+" Return only one JSON object with string or null values and exactly these keys: "+
            ", ".join(FIELDS)+". Do not invent missing values. Schema: "+schema+
            "\nProduct title: "+title+"\nBullet points: "+bullets)
def zero_shot_prompt(item_name,bullet_points):
    return _prompt("Extract product attributes using only evidence in the supplied text.",item_name,bullet_points)
def role_based_prompt(item_name,bullet_points):
    return _prompt("You are a careful e-commerce catalog data-quality analyst.",item_name,bullet_points)
def cot_prompt(item_name,bullet_points):
    return _prompt("Inspect the evidence carefully but do not reveal reasoning; return the final extraction only.",item_name,bullet_points)
def structured_prompt(item_name,bullet_points):
    return _prompt("Follow the JSON schema exactly and use null when an attribute is not supported.",item_name,bullet_points)
def few_shot_prompt(item_name,bullet_points,examples):
    if not examples: raise ValueError("Few-shot prompting requires training demonstrations")
    demos=[{"title":x["item_name"],"bullets":x["bullet_points"],"output":x["gold"]} for x in examples]
    return ("Learn the format from examples; use only evidence in the current product. Examples: "+
            json.dumps(demos,ensure_ascii=False)+"\nCurrent title: "+item_name+
            "\nCurrent bullets: "+bullet_points+"\nReturn JSON only.")
PROMPT_MAP={"zero_shot":zero_shot_prompt,"few_shot":few_shot_prompt,"cot":cot_prompt,
            "structured":structured_prompt,"role_based":role_based_prompt}
