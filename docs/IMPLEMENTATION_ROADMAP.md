# Implementation Roadmap

This roadmap separates existing repository capabilities from work still required to consolidate the companion quality-intelligence project.

## Stage 0 — Preserve and establish the foundation

- [x] Preserve the existing Amazon JSONL dataset and saved experiment artifacts.
- [x] Retain the prompt registry, experiment runner, extraction metrics, API, dashboard, and CI.
- [x] Document the combined product scope and architecture.
- [ ] Add a dataset manifest with provenance, license, version/hash, row count, schema, and limitations.
- [ ] Record the current offline test baseline.

## Stage 1 — Normalize the application structure

- [ ] Introduce a service layer shared by CLI experiments and FastAPI.
- [ ] Define typed contracts for datasets, evaluation requests, per-example results, and run metadata.
- [ ] Separate task-specific evaluators from shared run orchestration.
- [ ] Reconcile the existing provider calls with the companion provider adapter and add regression tests.
- [ ] Preserve current extraction benchmark behavior with deterministic fixtures.

## Stage 2 — Integrate quality evaluation

- [ ] Add the 60-case general benchmark as a versioned dataset.
- [ ] Add seller-support scenarios as a separate policy/groundedness evaluation suite.
- [ ] Add a general benchmark runner without treating lexical overlap as semantic correctness.
- [ ] Add versioned rubrics and transparent score details.
- [ ] Add RAG evaluation only when retrieval contexts and evidence references are available.

## Stage 3 — Human review and judge validation

- [ ] Build annotation task creation, reviewer submission, and adjudication workflows.
- [ ] Use pseudonymous reviewer IDs; do not expose personal details in public artifacts.
- [ ] Integrate human-human agreement and judge-vs-adjudicated analysis.
- [ ] Calibrate judge thresholds on a validation split only.
- [ ] Freeze thresholds and evaluate once on an untouched holdout.
- [ ] Show class support, confusion matrices, confidence intervals, and limitations.

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
