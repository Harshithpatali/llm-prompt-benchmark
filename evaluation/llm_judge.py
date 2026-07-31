import json
from typing import Dict, Any
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

JUDGE_MODEL = "llama-3.3-70b-versatile"


def llm_as_judge(prediction: Dict, gold: Dict, item_name: str, bullet_points: str) -> Dict[str, Any]:
    """
    Use an LLM to judge the quality of the extracted attributes.
    Returns a score from 1 to 5 + reasoning.
    """

    prompt = f"""You are an expert evaluator for product attribute extraction.

Compare the PREDICTED attributes with the GOLD (correct) attributes.

Product Title: {item_name}
Bullet Points: {bullet_points}

GOLD (Correct) attributes:
{json.dumps(gold, indent=2, ensure_ascii=False)}

PREDICTED attributes:
{json.dumps(prediction, indent=2, ensure_ascii=False)}

Evaluate on a scale of 1 to 5:
5 = Perfect or almost perfect
4 = Mostly correct, minor issues
3 = Partially correct
2 = Mostly wrong
1 = Completely wrong

Respond ONLY in this JSON format:
{{
  "score": <number from 1 to 5>,
  "reason": "<short explanation>",
  "correct_attributes": ["list of correctly extracted attributes"],
  "incorrect_attributes": ["list of wrong or missing attributes"]
}}
"""

    try:
        response = client.chat.completions.create(
            model=JUDGE_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=512,
        )
        raw = response.choices[0].message.content
        
        # Parse the response
        from evaluation.metrics import safe_parse_json
        result = safe_parse_json(raw)
        
        # Ensure required keys exist
        if "score" not in result:
            result = {"score": 1, "reason": "Failed to parse judge response", "correct_attributes": [], "incorrect_attributes": []}
        
        return result

    except Exception as e:
        return {
            "score": 1,
            "reason": f"Judge failed: {str(e)}",
            "correct_attributes": [],
            "incorrect_attributes": []
        }