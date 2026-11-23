# Implementation Roadmap

This roadmap separates existing repository capabilities from work still required to consolidate the companion quality-intelligence project.

## Stage 0 — Preserve and establish the foundation

- [x] Preserve the existing Amazon JSONL dataset and saved experiment artifacts.
- [x] Retain the prompt registry, experiment runner, extraction metrics, API, dashboard, and CI.
- [x] Document the combined product scope and architecture.
- [x] Copy and validate the 60-case general benchmark and 16 seller-support scenarios.
- [x] Add validated loaders, lexical reference-overlap diagnostics, and a dataset manifest.
- [ ] Add a reproducible Amazon dataset manifest with a verified source hash and upstream provenance.
- [x] Integrate judge calibration, judge validation, and annotation/reviewer metrics with tests.

## Stage 1 — Normalize the application structure

- [ ] Introduce a service layer shared by CLI experiments and FastAPI.
- [ ] Define typed contracts for datasets, evaluation requests, per-example results, and run metadata.
- [ ] Separate task-specific evaluators from shared run orchestration.
- [ ] Reconcile the existing provider calls with the companion provider adapter and add regression tests.
- [ ] Preserve current extraction benchmark behavior with deterministic fixtures.

## Stage 2 — Integrate quality evaluation

- [x] Add the 60-case general benchmark as a versioned starter dataset.
- [x] Add seller-support scenarios as a separate policy/groundedness challenge dataset.
- [x] Add a validated loader for both datasets.
- [x] Add lexical reference-overlap diagnostics with explicit semantic limitations.
- [x] Add a general benchmark runner with per-case results, category summaries, and failure reporting.
- [x] Add a Markdown report generator and manual GitHub Actions workflow.
- [ ] Add versioned rubrics and transparent task-specific score details.
- [ ] Add RAG evaluation only when retrieval contexts and evidence references are available.

## Stage 3 — Human review and judge validation

- [x] Add offline judge-vs-human validation and reliability-analysis modules.
- [x] Add reviewer agreement and annotation operational metric helpers.
- [ ] Build annotation task creation, reviewer submission, and adjudication workflows.
- [ ] Use pseudonymous reviewer IDs; do not expose personal details in public artifacts.
- [ ] Connect collected human labels to calibration inputs through a validated data contract.
- [x] Implement validation-only threshold selection and frozen holdout evaluation in the offline calibration module.
- [ ] Show class support, confusion matrices, confidence intervals, and limitations in the dashboard.

## Stage 4 — Persistence with Neon PostgreSQL

- [ ] Define native PostgreSQL migrations for the consolidated data model.
- [ ] Add a repository/data-access layer using a PostgreSQL driver.
- [ ] Add transaction, retry, connection-pool, and migration tests.
- [ ] Configure Neon connection secrets in deployment environments.
- [ ] Verify write/read round trips for runs, traces, annotations, and audit events.
- [ ] Keep JSON artifacts as reproducible exports, not as the only source of history.

## Stage 5 — Unified quality dashboard and API

- [ ] Add overview, prompt benchmark, model comparison, quality analysis, human review, judge calibration, and run-history views.
- [ ] Add API endpoints for run submission, run status, results, annotations, and review queue.
- [ ] Keep model execution and scoring in backend services, not Streamlit page code.
- [ ] Add pagination and filters for traces and annotations.
- [ ] Add safe error handling and avoid exposing provider or database secrets.

## Stage 6 — Validation and release

- [ ] Run all offline unit, integration, and API tests.
- [ ] Add deterministic evaluator tests with known expected outputs.
- [ ] Run provider-mocked tests in CI; keep live API benchmarks manual.
- [ ] Execute a small live smoke test, then a pre-registered benchmark run.
- [ ] Generate a reproducible report with dataset/model/prompt/evaluator versions and uncertainty.
- [ ] Verify Render, Streamlit, and Neon together before changing any old deployment.
- [ ] Update README with implemented features and measured results only.

## Release acceptance criteria

A feature is not complete merely because its module exists. It must have:

1. A documented input/output contract.
2. Unit tests and relevant integration tests.
3. Error handling and data validation.
4. A reproducible example or experiment artifact.
5. Documentation that distinguishes measured behavior from intended behavior.

## Non-goals

- Do not fabricate human labels or calibration records.
- Do not describe authored scenarios as production customer data.
- Do not claim semantic hallucination detection from lexical overlap.
- Do not compare unrelated task metrics on one universal leaderboard.
- Do not delete the companion repository or its reference history as part of consolidation.
