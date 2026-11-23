"""FastAPI service for prompt extraction and LLM quality run history."""
import json
import os
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from openai import OpenAI

from prompts.prompt_templates import PROMPT_MAP
from evaluation.metrics import safe_parse_json
from backend import db, repository

load_dotenv()
app = FastAPI(title="LLM Quality Intelligence API", version="3.0")
RESULTS_DIR = Path(os.getenv("RESULTS_DIR", "results")).resolve()


class ExtractRequest(BaseModel):
    item_name: str = Field(min_length=1, max_length=500)
    bullet_points: str = Field(default="", max_length=12000)
    strategy: str = "structured"
    provider: str = "groq"
    model: str | None = None


class ExtractResponse(BaseModel):
    strategy: str
    provider: str
    model: str
    prediction: dict[str, Any]
    raw_output: str


class QualityRunCreate(BaseModel):
    run_type: str = Field(pattern="^(prompt_benchmark|general_quality|seller_support)$")
    provider: str = Field(min_length=1, max_length=80)
    model_name: str = Field(min_length=1, max_length=200)
    configuration: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class QualityResultCreate(BaseModel):
    case_id: str = Field(min_length=1, max_length=200)
    strategy: str = Field(default="default", max_length=100)
    category: str = Field(min_length=1, max_length=120)
    difficulty: str | None = None
    prompt: str = Field(min_length=1)
    context: str | None = None
    reference_answer: str | None = None
    response: str | None = None
    status: str = Field(pattern="^(success|error)$")
    metrics: dict[str, Any] = Field(default_factory=dict)
    error_type: str | None = None
    error_message: str | None = None


def _database_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, db.DatabaseConfigurationError):
        return HTTPException(503, "Database is not configured")
    return HTTPException(503, "Database is unavailable or the required migration is not applied")


def _client(provider: str):
    configs = {
        "groq": ("GROQ_API_KEY", "https://api.groq.com/openai/v1"),
        "openrouter": ("OPENROUTER_API_KEY", "https://openrouter.ai/api/v1"),
    }
    if provider not in configs:
        raise HTTPException(400, "Unsupported provider")
    key, base = configs[provider]
    if not os.getenv(key):
        raise HTTPException(503, key + " is not configured")
    return OpenAI(api_key=os.getenv(key), base_url=base)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/database/health")
def database_health():
    try:
        return db.healthcheck()
    except Exception as exc:
        raise _database_http_error(exc) from exc


@app.get("/strategies")
def strategies():
    return {"strategies": list(PROMPT_MAP)}


@app.post("/extract", response_model=ExtractResponse)
def extract(req: ExtractRequest):
    if req.strategy not in PROMPT_MAP:
        raise HTTPException(400, "Invalid strategy")
    if req.strategy == "few_shot":
        raise HTTPException(400, "Few-shot requires training demonstrations; use the benchmark runner")
    model = req.model or os.getenv("MODEL_NAME", "llama-3.1-8b-instant")
    prompt = PROMPT_MAP[req.strategy](req.item_name, req.bullet_points)
    try:
        response = _client(req.provider).chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=512,
        )
        raw = response.choices[0].message.content or ""
    except Exception as exc:
        raise HTTPException(502, "LLM provider request failed: " + type(exc).__name__) from exc
    prediction = safe_parse_json(raw)
    if not prediction:
        raise HTTPException(502, "Provider returned invalid JSON")
    return ExtractResponse(
        strategy=req.strategy, provider=req.provider, model=model,
        prediction=prediction, raw_output=raw,
    )


@app.post("/quality/runs", status_code=201)
def create_quality_run(req: QualityRunCreate):
    try:
        return repository.create_run(
            run_type=req.run_type,
            provider=req.provider,
            model_name=req.model_name,
            configuration=req.configuration,
            metadata=req.metadata,
        )
    except Exception as exc:
        raise _database_http_error(exc) from exc


@app.post("/quality/runs/{run_id}/results", status_code=201)
def add_quality_results(run_id: UUID, results: list[QualityResultCreate]):
    if len(results) > 500:
        raise HTTPException(413, "A single request is limited to 500 results")
    try:
        inserted = repository.add_results(
            run_id, [item.model_dump() for item in results]
        )
        return {"run_id": str(run_id), "submitted": len(results), "processed": inserted}
    except Exception as exc:
        raise _database_http_error(exc) from exc


@app.get("/quality/runs")
def list_quality_runs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=100000),
):
    try:
        return {"runs": repository.list_runs(limit=limit, offset=offset)}
    except Exception as exc:
        raise _database_http_error(exc) from exc


@app.get("/quality/runs/{run_id}")
def get_quality_run(run_id: UUID):
    try:
        result = repository.get_run(run_id)
    except Exception as exc:
        raise _database_http_error(exc) from exc
    if result is None:
        raise HTTPException(404, "Evaluation run not found")
    return result


@app.get("/results")
def list_results():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(p.name for p in RESULTS_DIR.glob("*.json") if p.is_file())


@app.get("/results/{filename}")
def get_result(filename: str):
    if Path(filename).name != filename or not filename.endswith(".json"):
        raise HTTPException(400, "Invalid result filename")
    path = (RESULTS_DIR / filename).resolve()
    if path.parent != RESULTS_DIR or not path.is_file():
        raise HTTPException(404, "Result not found")
    return json.loads(path.read_text(encoding="utf-8"))
