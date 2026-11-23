"""FastAPI service for prompt extraction, experiment history and human review."""
import json
import os
from pathlib import Path
from typing import Any
from uuid import UUID
import hmac

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from openai import OpenAI
from pydantic import BaseModel, Field

from backend import db, repository
from backend.review_tasks import build_review_tasks, validate_annotation_submission
from backend.rubric_generator import build_generation_prompt, parse_and_validate
from backend import rubric_repository
from backend.rubric_evaluator import evaluate_response
from backend import rubric_human_review
from backend.judge_calibration import calculate_calibration
from backend.rubric_qa import validate_csv
from evaluation.metrics import safe_parse_json
from prompts.prompt_templates import PROMPT_MAP

load_dotenv()
app = FastAPI(title="LLM Quality Intelligence API", version="3.1")
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


class RubricGenerateRequest(BaseModel):
    scenario: str = Field(min_length=30, max_length=30000)
    provider: str = Field(default="groq", pattern="^(groq|openrouter)$")
    model: str | None = Field(default=None, max_length=200)


class RubricSaveRequest(BaseModel):
    rubric_name: str = Field(min_length=2, max_length=200)
    version_label: str = Field(min_length=1, max_length=80)
    objective: str = Field(min_length=10, max_length=4000)
    csv: str = Field(min_length=100, max_length=5_000_000)
    generator_provider: str | None = None
    generator_model: str | None = None
    created_by: str = Field(min_length=1, max_length=120)

class RubricApprovalRequest(BaseModel):
    approver: str = Field(min_length=1, max_length=120)

class RubricEvaluationRequest(BaseModel):
    rubric_id: UUID
    prompt: str = Field(min_length=1, max_length=30000)
    response: str = Field(min_length=1, max_length=30000)
    provider: str = Field(default="groq", pattern="^(groq|openrouter)$")
    model: str | None = Field(default=None, max_length=200)

class RubricHumanAnnotationRequest(BaseModel):
    evaluation_id: UUID
    component_id: str = Field(min_length=2, max_length=20)
    annotator_id: str = Field(min_length=1, max_length=120)
    verdict: str = Field(pattern="^(pass|fail|not_applicable)$")
    evidence: str = Field(min_length=3, max_length=4000)
    rationale: str = Field(default="", max_length=3000)
    confidence: int = Field(ge=1, le=5)

class RubricAdjudicationRequest(BaseModel):
    evaluation_id: UUID
    component_id: str = Field(min_length=2, max_length=20)
    adjudicator_id: str = Field(min_length=1, max_length=120)
    verdict: str = Field(pattern="^(pass|fail|not_applicable)$")
    evidence: str = Field(min_length=3, max_length=4000)
    notes: str = Field(default="", max_length=4000)

class RubricCalibrationRequest(BaseModel):
    rubric_id: UUID | None = None
    min_samples: int = Field(default=5, ge=2, le=1000)
    reliability_threshold: float = Field(default=0.80, ge=0.0, le=1.0)
    save_run: bool = True

class AnnotationDimensions(BaseModel):
    relevance: str
    correctness: str
    completeness: str


class AnnotationSubmission(BaseModel):
    annotator_id: str = Field(min_length=1, max_length=120)
    dimensions: AnnotationDimensions
    overall_label: str
    evidence: str = Field(min_length=8, max_length=4000)
    confidence: int = Field(ge=1, le=5)
    handling_seconds: int = Field(default=0, ge=0)
    escalated: bool | None = None
    defect_category: str = Field(default="none", min_length=1, max_length=120)
    is_audit: bool = False


def require_review_api_key(x_review_api_key: str | None = Header(default=None)) -> None:
    """Protect reviewer operations with a shared secret configured at deployment."""
    expected = os.getenv("REVIEW_API_KEY", "").strip()
    if not expected:
        raise HTTPException(503, "Review API is disabled until REVIEW_API_KEY is configured")
    if not x_review_api_key or not hmac.compare_digest(x_review_api_key, expected):
        raise HTTPException(401, "Invalid or missing review API key")


def _database_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, db.DatabaseConfigurationError):
        return HTTPException(503, "Database is not configured")
    if isinstance(exc, LookupError):
        return HTTPException(404, str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(409, str(exc))
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


@app.post("/rubrics/generate")
def generate_rubric(req: RubricGenerateRequest):
    """Generate a rubric from the checked-in framework and return deterministic QA."""
    prompt = build_generation_prompt(req.scenario)
    model = req.model or os.getenv("MODEL_NAME", "openai/gpt-oss-20b")
    try:
        response = _client(req.provider).chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=12000,
        )
        raw = response.choices[0].message.content or ""
        csv_text, qa = parse_and_validate(raw)
        return {"provider": req.provider, "model": model, "csv": csv_text, "qa": qa}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, "Rubric generation failed: " + type(exc).__name__) from exc


@app.post("/rubrics/validate")
def validate_rubric(payload: dict[str, str]):
    """Validate a rubric CSV without calling an LLM."""
    csv_text = payload.get("csv", "")
    if not csv_text or len(csv_text) > 5_000_000:
        raise HTTPException(400, "CSV is required and must be at most 5 MB")
    return validate_csv(csv_text)


@app.post("/rubrics", status_code=201, dependencies=[Depends(require_review_api_key)])
def save_rubric(req: RubricSaveRequest):
    try:
        qa = validate_csv(req.csv)
        if qa["status"] == "FAIL":
            raise HTTPException(422, {"message": "Rubric failed QA", "qa": qa})
        return rubric_repository.save_rubric(
            name=req.rubric_name, version=req.version_label, objective=req.objective,
            csv_text=req.csv, provider=req.generator_provider, model=req.generator_model,
            created_by=req.created_by,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise _database_http_error(exc) from exc

@app.get("/rubrics")
def list_saved_rubrics(limit: int = Query(default=50, ge=1, le=200),
                       offset: int = Query(default=0, ge=0, le=100000)):
    try:
        return {"rubrics": rubric_repository.list_rubrics(limit, offset)}
    except Exception as exc:
        raise _database_http_error(exc) from exc

@app.get("/rubrics/{rubric_id}")
def get_saved_rubric(rubric_id: UUID):
    try:
        rubric = rubric_repository.get_rubric(rubric_id)
    except Exception as exc:
        raise _database_http_error(exc) from exc
    if rubric is None:
        raise HTTPException(404, "Rubric not found")
    return rubric

@app.post("/rubrics/{rubric_id}/approve", dependencies=[Depends(require_review_api_key)])
def approve_saved_rubric(rubric_id: UUID, req: RubricApprovalRequest):
    try:
        return rubric_repository.approve_rubric(rubric_id, req.approver)
    except Exception as exc:
        raise _database_http_error(exc) from exc

@app.post("/rubrics/evaluate", status_code=201, dependencies=[Depends(require_review_api_key)])
def evaluate_with_rubric(req: RubricEvaluationRequest):
    model = req.model or os.getenv("MODEL_NAME", "openai/gpt-oss-20b")
    try:
        return evaluate_response(rubric_id=req.rubric_id, provider=req.provider, model=model,
            prompt=req.prompt, response=req.response, client=_client(req.provider))
    except HTTPException:
        raise
    except Exception as exc:
        raise _database_http_error(exc) from exc

@app.get("/rubrics/evaluations/{evaluation_id}", dependencies=[Depends(require_review_api_key)])
def get_rubric_evaluation(evaluation_id: UUID):
    try:
        result = rubric_repository.get_rubric_evaluation(evaluation_id)
    except Exception as exc:
        raise _database_http_error(exc) from exc
    if result is None:
        raise HTTPException(404, "Rubric evaluation not found")
    return result

@app.get("/rubrics/{rubric_id}/evaluations", dependencies=[Depends(require_review_api_key)])
def list_rubric_evaluations(rubric_id: UUID, limit: int = Query(default=20, ge=1, le=100)):
    try:
        if rubric_repository.get_rubric(rubric_id) is None:
            raise HTTPException(404, "Rubric not found")
        return {"evaluations": rubric_repository.list_rubric_evaluations(rubric_id, limit)}
    except HTTPException:
        raise
    except Exception as exc:
        raise _database_http_error(exc) from exc

@app.post("/rubrics/evaluations/{evaluation_id}/review-task", status_code=201, dependencies=[Depends(require_review_api_key)])
def create_rubric_review_task(evaluation_id: UUID):
    try:
        return rubric_human_review.create_rubric_review_task(evaluation_id)
    except Exception as exc:
        raise _database_http_error(exc) from exc

@app.get("/rubrics/review-tasks", dependencies=[Depends(require_review_api_key)])
def list_rubric_review_tasks(limit: int = Query(default=100, ge=1, le=500)):
    try:
        return {"tasks": rubric_human_review.list_rubric_review_tasks(limit)}
    except Exception as exc:
        raise _database_http_error(exc) from exc

@app.post("/rubrics/human-annotations", status_code=201, dependencies=[Depends(require_review_api_key)])
def submit_rubric_human_annotation(req: RubricHumanAnnotationRequest):
    try:
        return rubric_human_review.submit_rubric_human_annotation(
            evaluation_id=req.evaluation_id,component_id=req.component_id,annotator_id=req.annotator_id,
            verdict=req.verdict,evidence=req.evidence,rationale=req.rationale,confidence=req.confidence)
    except Exception as exc:
        raise _database_http_error(exc) from exc

@app.post("/rubrics/adjudications", status_code=201, dependencies=[Depends(require_review_api_key)])
def adjudicate_rubric_criterion(req: RubricAdjudicationRequest):
    try:
        return rubric_human_review.adjudicate_rubric_criterion(
            evaluation_id=req.evaluation_id,component_id=req.component_id,adjudicator_id=req.adjudicator_id,
            verdict=req.verdict,evidence=req.evidence,notes=req.notes)
    except Exception as exc:
        raise _database_http_error(exc) from exc

@app.post("/rubrics/calibration", dependencies=[Depends(require_review_api_key)])
def run_rubric_calibration(req: RubricCalibrationRequest):
    try:
        records=rubric_human_review.get_calibration_records(req.rubric_id)
        report=calculate_calibration(records,min_samples=req.min_samples,
                                     reliability_threshold=req.reliability_threshold)
        if req.save_run and report["overall"]["sample_count"]:
            saved=rubric_human_review.save_calibration_run(
                model="rubric-llm-judge",metrics=report,
                thresholds=report["thresholds"],
                metadata={"rubric_id":str(req.rubric_id) if req.rubric_id else None,
                          "records":report["overall"]["sample_count"]})
            report["calibration_run_id"]=str(saved["calibration_run_id"])
        return report
    except Exception as exc:
        raise _database_http_error(exc) from exc

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
            model=model, messages=[{"role": "user", "content": prompt}],
            temperature=0, max_tokens=512,
        )
        raw = response.choices[0].message.content or ""
    except Exception as exc:
        raise HTTPException(502, "LLM provider request failed: " + type(exc).__name__) from exc
    prediction = safe_parse_json(raw)
    if not prediction:
        raise HTTPException(502, "Provider returned invalid JSON")
    return ExtractResponse(strategy=req.strategy, provider=req.provider, model=model,
                            prediction=prediction, raw_output=raw)


@app.post("/quality/runs", status_code=201)
def create_quality_run(req: QualityRunCreate):
    try:
        return repository.create_run(
            run_type=req.run_type, provider=req.provider, model_name=req.model_name,
            configuration=req.configuration, metadata=req.metadata,
        )
    except Exception as exc:
        raise _database_http_error(exc) from exc


@app.post("/quality/runs/{run_id}/results", status_code=201)
def add_quality_results(run_id: UUID, results: list[QualityResultCreate]):
    if len(results) > 500:
        raise HTTPException(413, "A single request is limited to 500 results")
    try:
        inserted = repository.add_results(run_id, [item.model_dump() for item in results])
        return {"run_id": str(run_id), "submitted": len(results), "processed": inserted}
    except Exception as exc:
        raise _database_http_error(exc) from exc


@app.get("/quality/runs")
def list_quality_runs(limit: int = Query(default=20, ge=1, le=100),
                      offset: int = Query(default=0, ge=0, le=100000)):
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


@app.post("/quality/review-tasks/seed", status_code=201, dependencies=[Depends(require_review_api_key)])
def seed_review_tasks():
    """Idempotently import the repository's 16 authored seller-support examples."""
    try:
        tasks = build_review_tasks()
        inserted = repository.create_review_tasks(tasks)
        return {"source": "seller_support_tasks", "tasks_in_source": len(tasks),
                "inserted_or_existing": inserted}
    except Exception as exc:
        raise _database_http_error(exc) from exc


@app.get("/quality/review-tasks", dependencies=[Depends(require_review_api_key)])
def list_review_tasks(
    status: str | None = Query(default="pending", pattern="^(pending|claimed|submitted|adjudicated|cancelled)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0, le=100000),
):
    try:
        return {"tasks": repository.list_review_tasks(status=status, limit=limit, offset=offset)}
    except Exception as exc:
        raise _database_http_error(exc) from exc


@app.post("/quality/review-tasks/{task_id}/annotations", status_code=201, dependencies=[Depends(require_review_api_key)])
def submit_review_annotation(task_id: UUID, submission: AnnotationSubmission):
    task = {"review_task_id": str(task_id)}
    try:
        normalized = validate_annotation_submission(
            task, submission.model_dump(exclude_none=True)
        )
        return repository.submit_annotation(task_id, normalized)
    except Exception as exc:
        raise _database_http_error(exc) from exc


@app.get("/quality/annotations", dependencies=[Depends(require_review_api_key)])
def list_quality_annotations(limit: int = Query(default=100, ge=1, le=500),
                             offset: int = Query(default=0, ge=0, le=100000)):
    try:
        return {"annotations": repository.list_annotations(limit=limit, offset=offset)}
    except Exception as exc:
        raise _database_http_error(exc) from exc


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
