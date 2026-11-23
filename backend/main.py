"""FastAPI extraction service sharing the prompt registry."""
import json, os
from pathlib import Path
from typing import Any, Dict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from openai import OpenAI
from prompts.prompt_templates import PROMPT_MAP
from evaluation.metrics import safe_parse_json
load_dotenv()
app=FastAPI(title="LLM Prompt Benchmark API",version="2.0")
RESULTS_DIR=Path(os.getenv("RESULTS_DIR","results")).resolve()
class ExtractRequest(BaseModel):
    item_name:str=Field(min_length=1,max_length=500)
    bullet_points:str=Field(default="",max_length=12000)
    strategy:str="structured"
    provider:str="groq"
    model:str|None=None
class ExtractResponse(BaseModel):
    strategy:str
    provider:str
    model:str
    prediction:Dict[str,Any]
    raw_output:str
def _client(provider):
    configs={"groq":("GROQ_API_KEY","https://api.groq.com/openai/v1"),
             "openrouter":("OPENROUTER_API_KEY","https://openrouter.ai/api/v1")}
    if provider not in configs:raise HTTPException(400,"Unsupported provider")
    key,base=configs[provider]
    if not os.getenv(key):raise HTTPException(503,key+" is not configured")
    return OpenAI(api_key=os.getenv(key),base_url=base)
@app.get("/health")
def health():return {"status":"ok"}
@app.get("/strategies")
def strategies():return {"strategies":list(PROMPT_MAP)}
@app.post("/extract",response_model=ExtractResponse)
def extract(req:ExtractRequest):
    if req.strategy not in PROMPT_MAP:raise HTTPException(400,"Invalid strategy")
    if req.strategy=="few_shot":raise HTTPException(400,"Few-shot requires training demonstrations; use the benchmark runner")
    model=req.model or os.getenv("MODEL_NAME","llama-3.1-8b-instant")
    prompt=PROMPT_MAP[req.strategy](req.item_name,req.bullet_points)
    try:
        response=_client(req.provider).chat.completions.create(model=model,messages=[{"role":"user","content":prompt}],temperature=0,max_tokens=512)
        raw=response.choices[0].message.content or ""
    except Exception as exc:raise HTTPException(502,"LLM provider request failed: "+type(exc).__name__) from exc
    prediction=safe_parse_json(raw)
    if not prediction:raise HTTPException(502,"Provider returned invalid JSON")
    return ExtractResponse(strategy=req.strategy,provider=req.provider,model=model,prediction=prediction,raw_output=raw)
@app.get("/results")
def list_results():
    RESULTS_DIR.mkdir(parents=True,exist_ok=True)
    return sorted(p.name for p in RESULTS_DIR.glob("*.json") if p.is_file())
@app.get("/results/{filename}")
def get_result(filename:str):
    if Path(filename).name!=filename or not filename.endswith(".json"):raise HTTPException(400,"Invalid result filename")
    path=(RESULTS_DIR/filename).resolve()
    if path.parent!=RESULTS_DIR or not path.is_file():raise HTTPException(404,"Result not found")
    return json.loads(path.read_text(encoding="utf-8"))
