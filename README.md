# LLM Quality Intelligence Platform

**Prompt benchmarking, model evaluation, and quality reliability analysis in one reproducible platform.**

This repository consolidates the structured prompt-benchmarking project with the evaluation, calibration, and human-review capabilities from [LLM Quality Intelligence Platform](https://github.com/Harshithpatali/llm-quality-intelligence-platform).

The prompt benchmark remains a first-class research suite. The broader platform adds task-specific quality evaluation, human-review preparation, judge validation, calibration, experiment history, and operational monitoring.

## Existing datasets

- `data/final_clean_amazon.jsonl`: structured e-commerce product-attribute extraction data.
- `data/benchmark.jsonl`: 60 general response-quality cases across 12 categories.
- `data/seller_support_tasks.json`: 16 seller-support scenarios across six categories.

See [Dataset Manifest](data/DATASET_MANIFEST.md) for provenance notes and limitations. The general and seller-support datasets are authored starter scenarios, not externally validated gold standards or real customer records.

## Current capabilities

### Prompt benchmarking

- Five prompt strategies: zero-shot, few-shot, chain-of-thought instruction, structured JSON, and role-based.
- Leakage-aware data splitting: demonstrations are sampled only from training rows; all strategies share the same untouched holdout.
- Structured extraction metrics: exact match, attribute precision/recall/F1, micro/macro F1, JSON validity, missing attributes, coverage, lexical unsupported-value rate, latency, token usage, and request failures.
- Paired bootstrap confidence intervals and paired sign tests.
- Raw JSON results and Markdown research reports.

### General response benchmark

- Runs the 60-case general response benchmark against Groq or OpenRouter-compatible providers.
- Records response text, latency, token usage, request failures, case IDs, and dataset SHA-256.
- Produces category-level lexical diagnostics and a Markdown report.
- Has a manually triggered GitHub Actions workflow for reproducible runs.

### Human-review and reliability foundations

- Converts seller-support scenarios into pending, unlabelled review tasks.
- Validates human submissions using pseudonymous annotator IDs, evidence, confidence, and review dimensions.
- Judge threshold calibration using validation labels and frozen evaluation on an untouched holdout.
- Judge-versus-human agreement, confusion matrices, Cohen's kappa, class-level metrics, and bootstrap accuracy intervals.
- Annotation summaries, inter-reviewer agreement, and deterministic risk-aware audit sampling.

The review workflow is database-backed: 16 authored starter scenarios can be seeded idempotently, reviewers can submit validated annotations, task status changes transactionally, and each submission creates an audit event. The Streamlit reviewer workspace is available at `dashboard/pages/2_Quality_Review.py`. The starter scenarios are unlabelled examples, not real customer data or gold labels.

### Application foundation

- FastAPI extraction API.
- Streamlit experiment dashboard.
- GitHub Actions offline test and manual live-benchmark workflows.

## Important measurement limitations

- The general reference-overlap evaluator is a **lexical diagnostic**, not semantic correctness, factuality, relevance, groundedness, or safety evaluation.
- The e-commerce unsupported-value metric is also a lexical evidence heuristic, not semantic hallucination detection.
- LLM-as-judge scores remain supplementary until validated against independently collected human annotations.
- Human labels are an operational reference, not infallible ground truth.
- Bootstrap intervals quantify sampling uncertainty for the evaluated sample; they do not remove dataset bias, label errors, or model/provider drift.
- Keep task-specific metrics separate. Product extraction F1, support-policy rubric scores, and RAG faithfulness are not interchangeable.
- Cost reporting requires a maintained provider/model price table and must be omitted when prices are unknown.

## Database foundation

- Initial PostgreSQL schema is checked in at `migrations/001_initial_schema.sql`.
- `backend/db.py` provides a lazy, TLS-required psycopg connection boundary.
- The initial schema has been applied to the Neon production database. The deployed API's `GET /database/health` endpoint has returned a successful connection to `neondb`.
- See [database setup and migration instructions](database/README.md).

## Planned integration

The following remain implementation work:

- Persistent annotation UI, task assignment, submissions, adjudication, and audit history.
- Versioned rubrics and task-specific scoring for relevance, correctness, completeness, instruction following, groundedness, and policy compliance.
- Evaluation run/trace persistence using PostgreSQL (Neon is the intended target).
- Unified FastAPI endpoints and Streamlit quality-intelligence pages.
- RAG evaluation when retrieval contexts and evidence references are available.

See [Architecture](docs/ARCHITECTURE.md) and [Implementation Roadmap](docs/IMPLEMENTATION_ROADMAP.md). The companion repository remains a reference; this repository is the consolidated target.

## Local setup

Use Python 3.11 or a compatible version.

```bash
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Create a local `.env` file (never commit secrets):

```env
PROVIDER=groq
GROQ_API_KEY=your_key
MODEL_NAME=openai/gpt-oss-20b
SAMPLE_SIZE=200
QUALITY_SAMPLE_SIZE=60
TEST_SIZE=0.20
DEMO_SIZE=4
RANDOM_SEED=42
TEMPERATURE=0
MAX_TOKENS=512
```

For OpenRouter, configure `OPENROUTER_API_KEY` and set `PROVIDER=openrouter`.

### Run offline tests

```bash
pytest -q
```

### Run the e-commerce prompt benchmark

Live runs call an external model API and may incur provider charges or rate limits.

```bash
python -m experiments.run_experiment
python -m experiments.build_report
```

### Run the general response benchmark

```bash
python -m experiments.run_quality_benchmark
python -m experiments.build_quality_report
```

### Start the API and dashboard

```bash
uvicorn backend.main:app --reload --port 8000
streamlit run dashboard/app.py
```

Current API routes include `GET /health`, `GET /database/health`, `GET /strategies`, `POST /extract`, experiment history under `/quality/runs`, and reviewer operations under `/quality/review-tasks` and `/quality/annotations`. Reviewer routes require the `X-Review-API-Key` header.

## Reproducibility

Record provider, exact model, dataset version/hash, split seed and IDs, prompt version, evaluator/rubric version, generation settings, and timestamp. Do not tune on the final holdout. Review API failures and effective sample size before interpreting results.

## Security

Keep API keys and database URLs in environment variables or deployment secrets. Do not store personal customer data in the public benchmark repository.

## License

MIT

## Rubric generation and QA standards

The repository now includes the supplied universal rubric-generation framework and its companion QA specification:

- [Universal Rubric Generation Guide](docs/RUBRIC_GENERATION_GUIDE.md) — nine parent categories, atomic binary Pass/Fail criteria, explicit-versus-implicit traceability, and the fixed 14 Overall Performance questions (O1–O14). The guide specifies a nine-column CSV output and requires all fields to be quoted.
- [Rubric QA Specification](docs/RUBRIC_QA_SPEC.md) — validation rules for category names, immutable O1–O14 wording, sequential component IDs, CSV quoting/escaping, explicit/implicit alignment, and coverage checks.

These documents preserve the supplied source specifications. They are evaluation methodology references; the rubric-generation and QA interfaces are not yet represented as completed product features merely by adding these documents.


## Rubric Studio

Rubric Studio turns a scenario prompt into an atomic binary evaluation rubric using the checked-in Universal Rubric Generation Guide. It appends the 14 fixed Overall Performance questions and runs deterministic QA before export.

- Streamlit page: `dashboard/pages/3_Rubric_Studio.py`
- API: `POST /rubrics/generate` (provider-backed generation) and `POST /rubrics/validate` (offline CSV validation)
- QA engine: `backend/rubric_qa.py`
- Generator prompt builder: `backend/rubric_generator.py`
- QA specification: [Rubric QA Specification](docs/RUBRIC_QA_SPEC.md)

Generation requires the selected provider key (`GROQ_API_KEY` or `OPENROUTER_API_KEY`) on the API service. Validation is deterministic and does not require an LLM. A generated rubric is not considered approved merely because it passes structural QA: domain owners should inspect the atomic criteria, quotations, and implicit assumptions before using it for model release decisions.
