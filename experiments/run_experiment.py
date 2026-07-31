import os
import json
import time
from datetime import datetime
from tqdm import tqdm
from dotenv import load_dotenv
from openai import OpenAI
import mlflow

from utils.data_loader import load_data, prepare_examples
from prompts.prompt_templates import (
    zero_shot_prompt,
    few_shot_prompt,
    cot_prompt,
    structured_prompt,
)
from evaluation.metrics import safe_parse_json, evaluate_batch
from evaluation.llm_judge import llm_as_judge

load_dotenv()

# =====================================================
# CONFIG
# =====================================================

PROVIDER = "groq"          # "groq" or "openrouter"

GROQ_MODEL = "llama-3.1-8b-instant"
OPENROUTER_MODEL = "meta-llama/llama-3.1-8b-instruct"

N_SAMPLES = 12
TEMPERATURE = 0.0


# =====================================================
# CLIENT
# =====================================================

def get_client(provider: str) -> OpenAI:
    if provider == "groq":
        return OpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1",
        )

    elif provider == "openrouter":
        return OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
        )

    raise ValueError("Provider must be groq or openrouter")


def get_model_name(provider: str):
    if provider == "groq":
        return GROQ_MODEL
    return OPENROUTER_MODEL


client = get_client(PROVIDER)
MODEL = get_model_name(PROVIDER)


# =====================================================
# LLM CALL
# =====================================================

def call_llm(prompt: str, max_retries: int = 3):

    for attempt in range(max_retries):

        try:

            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=TEMPERATURE,
                max_tokens=1024,
            )

            return response.choices[0].message.content

        except Exception as e:

            print(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(2 ** attempt)

    return ""


# =====================================================
# RUN ONE PROMPT STRATEGY
# =====================================================

def run_strategy(name, prompt_fn, test_df, examples=None):

    print(f"\nRunning {name} using {MODEL}")

    predictions = []
    golds = []
    raw_outputs = []

    for _, row in tqdm(test_df.iterrows(), total=len(test_df)):

        if name == "few_shot":
            prompt = prompt_fn(
                row["item_name"],
                row["bullet_points_text"],
                examples,
            )
        else:
            prompt = prompt_fn(
                row["item_name"],
                row["bullet_points_text"],
            )

        raw = call_llm(prompt)

        pred = safe_parse_json(raw)

        gold = {
            "brand": row.get("brand"),
            "color": row.get("color"),
            "product_type": row.get("product_type"),
            "style": row.get("style"),
            "material": row.get("material"),
            "model_number": row.get("model_number"),
            "key_features": (
                row.get("bullet_points", [])[:4]
                if isinstance(row.get("bullet_points"), list)
                else []
            ),
        }

        # =====================================================
        # LLM AS JUDGE
        # =====================================================

        judge = llm_as_judge(
            prediction=pred,
            gold=gold,
            item_name=row["item_name"],
            bullet_points=row["bullet_points_text"],
        )

        predictions.append(pred)
        golds.append(gold)

        raw_outputs.append(
            {
                "item_id": row["item_id"],
                "raw": raw,
                "pred": pred,
                "gold": gold,
                "judge": judge,
            }
        )

        time.sleep(0.35)

    metrics = evaluate_batch(predictions, golds)

    # =====================================================
    # Average Judge Score
    # =====================================================

    judge_scores = [
        item["judge"]["score"]
        for item in raw_outputs
        if item.get("judge") and "score" in item["judge"]
    ]

    if judge_scores:
        metrics["judge_avg_score"] = round(
            sum(judge_scores) / len(judge_scores),
            3,
        )

    return {
        "strategy": name,
        "provider": PROVIDER,
        "model": MODEL,
        "metrics": metrics,
        "raw_outputs": raw_outputs,
    }


# =====================================================
# MAIN
# =====================================================

def main():

    mlflow.set_experiment("LLM_Prompt_Benchmark")

    with mlflow.start_run(
        run_name=f"{PROVIDER}_{MODEL}_{datetime.now().strftime('%H%M%S')}"
    ):

        mlflow.log_param("provider", PROVIDER)
        mlflow.log_param("model", MODEL)
        mlflow.log_param("temperature", TEMPERATURE)
        mlflow.log_param("samples", N_SAMPLES)

        print(f"Provider : {PROVIDER}")
        print(f"Model    : {MODEL}")

        df = load_data("data/final_clean_amazon.jsonl")

        print(f"Loaded {len(df)} products")

        examples = prepare_examples(df, n=4)

        test_df = df.sample(
            n=min(N_SAMPLES, len(df)),
            random_state=42,
        )

        strategies = [
            ("zero_shot", zero_shot_prompt),
            ("few_shot", few_shot_prompt),
            ("cot", cot_prompt),
            ("structured", structured_prompt),
        ]

        all_results = []

        for name, prompt_fn in strategies:

            result = run_strategy(
                name,
                prompt_fn,
                test_df,
                examples if name == "few_shot" else None,
            )

            all_results.append(result)

            for metric_name, value in result["metrics"].items():
                mlflow.log_metric(
                    f"{name}_{metric_name}",
                    value,
                )

            print(
                f"{name:12s}  Overall={result['metrics'].get('overall',0):.3f}"
            )

        os.makedirs("results", exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        filename = (
            f"{PROVIDER}_{MODEL.replace('/','_')}_{timestamp}.json"
        )

        output_path = os.path.join("results", filename)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                all_results,
                f,
                indent=2,
                ensure_ascii=False,
            )

        mlflow.log_artifact(output_path)

        print("\nResults saved to:")
        print(output_path)

        print("\nMLflow logging completed.")


if __name__ == "__main__":
    main()