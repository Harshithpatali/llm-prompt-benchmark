# LLM Prompt Evaluation & Benchmarking Framework

A reproducible evaluation harness for structured product-attribute extraction from e-commerce text. It compares prompting strategies on identical held-out examples and reports quality, reliability and latency.

## Implemented
- Zero-shot, few-shot, chain-of-thought instruction, structured JSON and role-based prompting.
- Groq and OpenRouter-compatible API clients.
- Leakage-safe deterministic split: demonstrations are sampled only from training rows; test and demo IDs are recorded.
- Exact match, per-attribute precision/recall/F1, micro/macro F1, JSON validity, missing attributes, coverage and lexical unsupported-value rate.
- Paired bootstrap confidence intervals and exact paired sign test versus zero-shot.
- Latency percentiles, token usage, retry/failure reporting and MLflow artifacts.
- Offline unit tests and GitHub Actions CI.
- FastAPI extraction API with safe result-file resolution.

## Experimental protocol
Split the data before selecting few-shot examples. Every prompt strategy is evaluated on the same untouched holdout. Each result records dataset size, split IDs, seed, raw outputs, predictions, labels and per-row outcomes. Use a sufficiently large holdout and report uncertainty; a small run is exploratory, not conclusive.

The unsupported-value metric is a lexical heuristic, not a semantic hallucination detector. The optional judge is supplementary and must be calibrated against human annotations before being treated as reliable. Bootstrap intervals do not correct dataset bias or provider/model drift.

## Setup
Create a virtual environment and install requirements. Set GROQ_API_KEY or OPENROUTER_API_KEY in .env. Configure PROVIDER, MODEL_NAME, SAMPLE_SIZE (200 by default; 0 means full holdout), TEST_SIZE, DEMO_SIZE, RANDOM_SEED, STRATEGIES, TEMPERATURE and MAX_TOKENS.

Run offline tests with: pytest -q

Run a live benchmark with: python -m experiments.run_experiment

Live benchmarking requires provider credentials and makes external API calls.

## API
Start with: uvicorn backend.main:app --reload --port 8000

Routes: GET /health, GET /strategies, POST /extract, GET /results, GET /results/{filename}.

## Limitations
Exact match is strict; semantic similarity requires separately validated scoring. The lexical unsupported-value heuristic can flag paraphrases and miss plausible errors. Judge scores require human calibration. Monetary cost is not estimated without a maintained provider price table. Audit dataset labels, duplicates, provenance and category balance before making general claims.

## License
MIT
