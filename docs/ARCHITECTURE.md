# Architecture

## Product boundary

The consolidated repository combines two complementary workflows:

1. **Prompt benchmark research:** compare prompt strategies on identical held-out examples, initially focused on structured e-commerce attribute extraction.
2. **LLM quality operations:** evaluate general responses, validate automated judges, prepare human review, analyze disagreement, and persist quality history.

The prompt benchmark remains a task-specific research suite. It is not replaced by one generic score.

## Datasets

- `data/final_clean_amazon.jsonl`: structured extraction dataset with six target attributes.
- `data/benchmark.jsonl`: 60 general-response challenge cases.
- `data/seller_support_tasks.json`: 16 policy and customer-support scenarios.

Dataset loaders validate schemas and unique IDs. Provenance and limitations are recorded in `data/DATASET_MANIFEST.md`.

## Logical architecture

```text
Versioned datasets
  |-- structured extraction dataset
  |-- general response benchmark
  |-- seller-support scenarios
  `-- future task-specific / RAG datasets
          |
          v
Dataset adapters and split controls
          |
          v
Provider adapters --> prompt / model execution
          |
          v
Task-specific evaluators
  |-- structured extraction metrics
  |-- reference-overlap diagnostics (lexical only)
  |-- rubric-based quality dimensions (planned)
  |-- groundedness / evidence checks (planned)
  `-- judge validation and calibration
          |
          +------> Pending review tasks and submission validation
          |        (offline helpers; persistent workflow planned)
          |
          v
Experiment and trace records
          |
          v
PostgreSQL persistence (Neon target; planned)
          |
          v
FastAPI service + Streamlit quality dashboard
```

## Existing components

- `prompts/prompt_templates.py`: prompt strategy registry.
- `utils/data_loader.py`: e-commerce dataset validation and leakage-aware splitting.
- `evaluation/metrics.py`: extraction metrics and paired statistical comparisons.
- `evaluation/llm_judge.py`: optional supplementary judge for extraction examples.
- `experiments/run_experiment.py`: reproducible extraction experiment.
- `experiments/run_quality_benchmark.py`: general-response benchmark execution and run artifact creation.
- `experiments/build_quality_report.py`: Markdown report generation for general-response runs.
- `backend/main.py`: current extraction API baseline.
- `dashboard/app.py`: current Streamlit dashboard baseline.
- `backend/calibration.py`: reviewer/judge reliability and validation/holdout threshold calibration.
- `backend/judge_validation.py`: judge-vs-human validation and bootstrap accuracy intervals.
- `backend/ops_metrics.py`: annotation summaries, reviewer agreement, and risk-aware audit sampling.
- `backend/review_tasks.py`: seller-support review-task preparation and submission validation; no persistence.
- `backend/evaluator.py`: lexical reference-overlap diagnostics only.
- `backend/quality_datasets.py`: validated loaders for the two additional datasets.
- `backend/db.py`: lazy psycopg connection boundary with TLS required; persistence methods and application integration remain future work.
- `migrations/001_initial_schema.sql`: initial PostgreSQL schema, tested on a temporary Neon branch only.
- Existing `data/`, `results/`, and `reports/` artifacts must be preserved.

## Components still to integrate

- Persistent annotation task assignment, submissions, adjudication, and audit history.
- Versioned rubrics and general task-specific rubric scoring.
- Evaluation traces, review queues, and operational persistence.
- A provider abstraction reconciled with the current prompt-benchmark API client.

The companion quality-intelligence source contains Supabase-specific data access and API orchestration. Treat its schemas and contracts as references; do not copy its Supabase persistence code unchanged.

## Run-level data contract

Every run should identify:

- run ID and UTC timestamp;
- dataset name, immutable version or content hash;
- split method, random seed, and train/demo/validation/holdout identifiers where applicable;
- provider and exact model identifier;
- prompt template/version and generation settings;
- evaluator/rubric version;
- per-example input, output, score details, latency, token usage, and failure status, subject to retention policy.

Keep validation and final holdout separate. Related examples must remain in one split where leakage is possible. Human labels used to calibrate judges must be independent of the final holdout.

## Persistence target

Neon PostgreSQL is the intended persistence layer. An initial PostgreSQL schema is checked in and was validated on a temporary Neon branch; the temporary branch was discarded, and the migration has not been applied to the default branch. A lazy psycopg connection boundary is checked in but no run/annotation persistence methods are wired yet. The previous quality app used Supabase-specific PostgREST calls and SQL migrations. Replace those with a PostgreSQL driver, a repository/data-access layer, and explicit migrations. Do not assume the previous Supabase SQL file is already a suitable final Neon schema.

Candidate logical entities:

- datasets and dataset versions;
- benchmark cases;
- model/provider registry;
- prompt templates and versions;
- evaluation runs and per-example results;
- metric summaries and traces;
- rubrics and rubric versions;
- annotation tasks, submissions, and adjudications;
- judge validation/calibration runs;
- review queue items and audit events.

Use foreign keys, uniqueness constraints, indexes, and transaction boundaries. Keep credentials out of source control.

## API and UI responsibilities

FastAPI owns validated request handling, model execution orchestration, run retrieval, annotations, and quality-operation endpoints. Streamlit is a client of the API and presents run comparison, failure exploration, reviewer work, calibration, and history.

Avoid duplicating evaluation logic inside Streamlit. Offline experiments and API workflows should call the same service-layer evaluators.

## Deployment

- FastAPI backend: Render (existing target).
- Streamlit frontend: Streamlit Community Cloud (existing target).
- Database: Neon PostgreSQL (new target).
- CI: GitHub Actions for offline tests and static checks.
- Live benchmark workflows: manual trigger, provider secrets, bounded sample size, and raw artifacts.

Migration is staged. Do not remove the existing deployment or historical JSON artifacts until the new integration passes tests and a live smoke test.
