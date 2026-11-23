# LLM Quality Intelligence Platform

Prompt benchmarking, model evaluation, and quality reliability analysis in one reproducible platform.

This repository consolidates the structured prompt-benchmarking project with the evaluation, calibration, and human-review capabilities from [LLM Quality Intelligence Platform](https://github.com/Harshithpatali/llm-quality-intelligence-platform).

## Existing research assets

- `data/final_clean_amazon.jsonl`: structured product attribute extraction benchmark.
- Five prompt strategies: zero-shot, few-shot, chain-of-thought instruction, structured JSON, and role-based.
- Extraction metrics: exact match, attribute precision/recall/F1, micro/macro F1, JSON validity, coverage, missing attributes, lexical unsupported-value rate, latency, token usage, and request failures.
- Paired bootstrap confidence intervals and paired sign tests.
- Saved raw results and Markdown experiment reports.
- FastAPI extraction API, Streamlit dashboard, and GitHub Actions workflows.

The consolidated platform will also incorporate:
- `data/benchmark.jsonl`: 60 general response-quality starter cases from the companion repository.
- `data/seller_support_tasks.json`: 16 seller-support review scenarios from the companion repository.
- Versioned rubrics, judge validation, human annotations, adjudication, reviewer agreement, calibration, evaluation traces, review queues, and audit history.

These additional capabilities are the integration target; they are not all implemented or wired into this repository yet.

## Quality evaluation principles

Keep task-specific metrics separate. Product attribute F1, customer-support policy scores, and RAG faithfulness are not interchangeable. Store metric definitions, scales, dataset versions, prompt versions, and evaluator versions with every run.

The unsupported-value metric in the extraction benchmark is a lexical evidence heuristic, not semantic hallucination detection. LLM-as-judge scores remain supplementary until validated against independent human annotations. Authored or synthetic scenarios are not real customer data or externally validated gold standards.

## Local setup

Use Python 3.11 or compatible.

```bash
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Set provider credentials in a local `.env` file. Never commit API keys.

```env
PROVIDER=groq
GROQ_API_KEY=your_key
MODEL_NAME=openai/gpt-oss-20b
SAMPLE_SIZE=200
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

### Run the prompt benchmark

Live runs call an external model API and may incur provider charges or rate limits.

```bash
python -m experiments.run_experiment
python -m experiments.build_report
```

### Start the API and dashboard

```bash
uvicorn backend.main:app --reload --port 8000
streamlit run dashboard/app.py
```

Current API routes: `GET /health`, `GET /strategies`, `POST /extract`, `GET /results`, and `GET /results/{filename}`.

## Architecture and roadmap

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/IMPLEMENTATION_ROADMAP.md](docs/IMPLEMENTATION_ROADMAP.md). Neon PostgreSQL is the intended persistence target. The old Supabase-specific data-access code must be replaced with a native PostgreSQL repository layer; do not assume changing a connection URL is sufficient.

## Reproducibility

Record provider, exact model, dataset version, split seed and IDs, prompt version, evaluator/rubric version, generation settings, and timestamp. Do not tune on the final holdout. Review API failures and effective sample size before interpreting results.

## Security

Keep API keys and database URLs in environment variables or deployment secrets. Do not store personal customer data in the public benchmark repository.

## License

MIT
