# 🚀 LLM Prompt Evaluation & Benchmarking Framework

> A production-ready framework for evaluating and benchmarking multiple
> prompt engineering strategies for structured information extraction
> using Large Language Models (LLMs).

> **Note:** This README is a polished starter document based on your
> current project structure. It is intended to be expanded with
> screenshots, benchmark results, and API examples as your project
> evolves.

------------------------------------------------------------------------

## 📌 Table of Contents

1.  Overview
2.  Features
3.  Project Objective
4.  System Architecture
5.  Project Structure
6.  Dataset
7.  Prompt Strategies
8.  Evaluation Metrics
9.  Technology Stack
10. Installation
11. Environment Variables
12. Running the Project
13. API Endpoints
14. Dashboard
15. Deployment
16. Future Improvements
17. Author
18. License

------------------------------------------------------------------------

# 1. Overview

The **LLM Prompt Evaluation & Benchmarking Framework** is a modular
platform for comparing prompt engineering strategies on structured
attribute extraction tasks.

It combines:

-   FastAPI backend
-   Streamlit dashboard
-   MLflow experiment tracking
-   Automated benchmarking
-   Interactive visualizations

------------------------------------------------------------------------

# 2. Features

-   ✅ Zero-Shot Prompting
-   ✅ Few-Shot Prompting
-   ✅ Chain-of-Thought Prompting
-   ✅ Structured JSON Prompting
-   ✅ FastAPI REST API
-   ✅ Streamlit Dashboard
-   ✅ MLflow Experiment Tracking
-   ✅ Interactive Benchmark Comparison
-   ✅ JSON Result Storage
-   ✅ Production-Ready Architecture

------------------------------------------------------------------------

# 3. Project Objective

Evaluate multiple prompting strategies using the same dataset and
compare:

-   Extraction Accuracy
-   Precision
-   Recall
-   F1 Score
-   Exact Match
-   Latency
-   JSON Validity

------------------------------------------------------------------------

# 4. System Architecture

``` text
Dataset
   │
   ▼
Prompt Templates
   │
   ▼
LLM (Groq/OpenRouter)
   │
   ▼
Structured JSON
   │
   ▼
Evaluation Engine
   │
   ▼
MLflow + Results
   │
   ▼
Streamlit Dashboard
```

------------------------------------------------------------------------

# 5. Project Structure

``` text
llm-prompt-benchmark/
│
├── backend/
│   └── main.py
├── dashboard/
│   └── app.py
├── data/
│   └── final_clean_amazon.jsonl
├── evaluation/
│   ├── metrics.py
│   └── llm_judge.py
├── experiments/
│   └── run_experiment.py
├── prompts/
│   └── prompt_templates.py
├── results/
├── utils/
│   └── data_loader.py
├── mlruns/
├── requirements.txt
└── README.md
```

------------------------------------------------------------------------

# 6. Dataset

Cleaned Amazon Berkeley Objects (ABO) product dataset containing:

-   Product title
-   Bullet points
-   Ground truth attributes

------------------------------------------------------------------------

# 7. Prompt Strategies

-   Zero-Shot
-   Few-Shot
-   Chain-of-Thought
-   Structured JSON

------------------------------------------------------------------------

# 8. Evaluation Metrics

-   Exact Match
-   Precision
-   Recall
-   F1 Score
-   Attribute Accuracy
-   JSON Validity
-   Latency
-   Success Rate

------------------------------------------------------------------------

# 9. Technology Stack

-   Python
-   FastAPI
-   Streamlit
-   Plotly
-   Pandas
-   NumPy
-   Scikit-learn
-   MLflow
-   OpenRouter
-   Groq

------------------------------------------------------------------------

# 10. Installation

``` bash
git clone https://github.com/<username>/llm-prompt-benchmark.git
cd llm-prompt-benchmark
pip install -r requirements.txt
```

------------------------------------------------------------------------

# 11. Environment Variables

``` env
OPENROUTER_API_KEY=
GROQ_API_KEY=
MODEL_NAME=
TEMPERATURE=0
```

------------------------------------------------------------------------

# 12. Running the Project

Backend

``` bash
uvicorn backend.main:app --reload
```

Dashboard

``` bash
streamlit run dashboard/app.py
```

Run benchmark

``` bash
python experiments/run_experiment.py
```

------------------------------------------------------------------------

# 13. API Endpoints

  Method   Endpoint
  -------- ------------
  POST     /extract
  POST     /benchmark
  GET      /results
  GET      /health

------------------------------------------------------------------------

# 14. Dashboard

Includes:

-   Strategy Comparison
-   Attribute Performance
-   Raw Output Explorer
-   Live Attribute Extraction

------------------------------------------------------------------------

# 15. Deployment

Backend

``` bash
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

Dashboard

``` bash
streamlit run dashboard/app.py --server.port=$PORT --server.address=0.0.0.0
```

Deploy both services on Render.

------------------------------------------------------------------------

# 16. Future Improvements

-   LLM-as-a-Judge
-   Semantic Similarity
-   RAG Evaluation
-   Multi-model Comparison
-   Docker
-   Kubernetes
-   CI/CD

------------------------------------------------------------------------

# 17. Author

**Harshith Devraj**

GitHub: https://github.com/Harshithpatali

LinkedIn: https://linkedin.com/in/harshith-devaraja-087ba0228

------------------------------------------------------------------------

# 18. License

MIT License
