from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
from pathlib import Path
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="LLM Prompt Benchmark API", version="1.0")

# ---------- Models ----------
class ExtractRequest(BaseModel):
    item_name: str
    bullet_points: str
    strategy: str = "structured"          # zero_shot | few_shot | cot | structured

class ExtractResponse(BaseModel):
    strategy: str
    prediction: Dict[str, Any]
    raw_output: str

# ---------- LLM Client ----------
client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)
MODEL = "llama-3.3-70b-versatile"

from prompts.prompt_templates import (
    zero_shot_prompt, few_shot_prompt, cot_prompt, structured_prompt
)

PROMPT_MAP = {
    "zero_shot": zero_shot_prompt,
    "cot": cot_prompt,
    "structured": structured_prompt,
}

def call_llm(prompt: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=1024,
    )
    return response.choices[0].message.content

# ---------- Routes ----------
@app.get("/")
def root():
    return {"message": "LLM Prompt Benchmark API is running"}

@app.post("/extract", response_model=ExtractResponse)
def extract_attributes(req: ExtractRequest):
    if req.strategy not in PROMPT_MAP and req.strategy != "few_shot":
        raise HTTPException(status_code=400, detail="Invalid strategy")

    if req.strategy == "few_shot":
        # For simplicity we use structured as fallback in API
        # (you can load real examples if needed)
        prompt = structured_prompt(req.item_name, req.bullet_points)
    else:
        prompt_fn = PROMPT_MAP[req.strategy]
        prompt = prompt_fn(req.item_name, req.bullet_points)

    raw = call_llm(prompt)
    
    from evaluation.metrics import safe_parse_json
    prediction = safe_parse_json(raw)

    return ExtractResponse(
        strategy=req.strategy,
        prediction=prediction,
        raw_output=raw
    )

@app.get("/results")
def list_results():
    results_dir = Path("results")
    if not results_dir.exists():
        return []
    files = sorted(results_dir.glob("*.json"), reverse=True)
    return [f.name for f in files]

@app.get("/results/{filename}")
def get_result(filename: str):
    path = Path("results") / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    with open(path) as f:
        return json.load(f)