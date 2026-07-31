import os
import json
import time
from datetime import datetime
from typing import List, Dict
from tqdm import tqdm
from dotenv import load_dotenv
from openai import OpenAI
import mlflow

from utils.data_loader import load_data, prepare_examples
from prompts.prompt_templates import (
    zero_shot_prompt, few_shot_prompt, cot_prompt, structured_prompt
)
from evaluation.metrics import safe_parse_json, evaluate_batch

load_dotenv()

# ====================== CONFIG ======================
# In run_experiment.py

PROVIDER = "groq"
GROQ_MODEL = "llama-3.1-8b-instant"     # ← change this
N_SAMPLES = 12                         # ← reduce this
TEMPERATURE = 0.0
# ====================================================

def get_client(provider: str) -> OpenAI:
    if provider == "groq":
        return OpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1"
        )
    elif provider == "openrouter":
        return OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1"
        )
    raise ValueError("PROVIDER must be 'groq' or 'openrouter'")

def get_model_name(provider: str) -> str:
    return GROQ_MODEL if provider == "groq" else OPENROUTER_MODEL

client = get_client(PROVIDER)
MODEL = get_model_name(PROVIDER)

def call_llm(prompt: str, max_retries: int = 3) -> str:
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=TEMPERATURE,
                max_tokens=1024,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Attempt {attempt+1} failed: {e}")
            time.sleep(2 ** attempt)
    return ""

def run_strategy(name: str, prompt_fn, test_df, examples=None):
    print(f"\n→ Running strategy: {name} | Model: {MODEL}")
    predictions, golds, raw_outputs = [], [], []

    for _, row in tqdm(test_df.iterrows(), total=len(test_df)):
        if name == "few_shot":
            prompt = prompt_fn(row["item_name"], row["bullet_points_text"], examples)
        else:
            prompt = prompt_fn(row["item_name"], row["bullet_points_text"])

        raw = call_llm(prompt)
        pred = safe_parse_json(raw)

        gold = {
            "brand": row.get("brand"),
            "color": row.get("color"),
            "product_type": row.get("product_type"),
            "style": row.get("style"),
            "material": row.get("material"),
            "model_number": row.get("model_number"),
            "key_features": row.get("bullet_points", [])[:4] if isinstance(row.get("bullet_points"), list) else []
        }

        predictions.append(pred)
        golds.append(gold)
        raw_outputs.append({"item_id": row["item_id"], "raw": raw, "pred": pred})
        time.sleep(0.35)

    metrics = evaluate_batch(predictions, golds)
    return {
        "strategy": name,
        "provider": PROVIDER,
        "model": MODEL,
        "metrics": metrics,
        "raw_outputs": raw_outputs
    }

def main():
    mlflow.set_experiment("LLM_Prompt_Benchmark")
    
    with mlflow.start_run(run_name=f"{PROVIDER}_{MODEL}_{datetime.now().strftime('%H%M%S')}"):
        mlflow.log_param("provider", PROVIDER)
        mlflow.log_param("model", MODEL)
        mlflow.log_param("n_samples", N_SAMPLES)
        mlflow.log_param("temperature", TEMPERATURE)

        print(f"Using provider: {PROVIDER.upper()} | Model: {MODEL}")
        df = load_data("data/final_clean_amazon.jsonl")
        print(f"Loaded {len(df)} products")

        examples = prepare_examples(df, n=4)
        test_df = df.sample(n=min(N_SAMPLES, len(df)), random_state=42)

        strategies = [
            ("zero_shot", zero_shot_prompt),
            ("few_shot", few_shot_prompt),
            ("cot", cot_prompt),
            ("structured", structured_prompt),
        ]

        all_results = []
        for name, fn in strategies:
            res = run_strategy(name, fn, test_df, examples if name == "few_shot" else None)
            all_results.append(res)

            # Log metrics to MLflow
            for metric_name, value in res["metrics"].items():
                mlflow.log_metric(f"{name}_{metric_name}", value)

            print(f"{name:12} → Overall: {res['metrics'].get('overall', 0):.3f}")

        # Save full results
        os.makedirs("results", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"results/{PROVIDER}_{MODEL.replace('/', '_')}_{timestamp}.json"
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)

        mlflow.log_artifact(output_path)
        print(f"\nResults saved → {output_path}")
        print("MLflow run completed.")

if __name__ == "__main__":
    main()