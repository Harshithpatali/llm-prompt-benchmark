"""Leakage-safe prompt benchmark. Run: python -m experiments.run_experiment"""
import json, os, random, time
from datetime import datetime, timezone
from pathlib import Path
import mlflow
from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm
from evaluation.metrics import evaluate_batch, paired_bootstrap_ci, paired_sign_test, safe_parse_json
from prompts.prompt_templates import PROMPT_MAP
from utils.data_loader import load_data, split_data, prepare_examples, gold_record
load_dotenv()
PROVIDERS={"groq":("GROQ_API_KEY","https://api.groq.com/openai/v1"),
           "openrouter":("OPENROUTER_API_KEY","https://openrouter.ai/api/v1")}
DEFAULT_MODELS={"groq":"openai/gpt-oss-20b","openrouter":"meta-llama/llama-3.1-8b-instruct"}

def make_client(provider):
    if provider not in PROVIDERS: raise ValueError("Unsupported provider: "+provider)
    key_name,base=PROVIDERS[provider]; key=os.getenv(key_name)
    if not key: raise RuntimeError(key_name+" is required")
    return OpenAI(api_key=key,base_url=base,timeout=float(os.getenv("TIMEOUT_SECONDS","45")))

def call_model(client,model,prompt):
    error=None
    for attempt in range(int(os.getenv("RETRY_LIMIT","3"))):
        try:
            start=time.perf_counter()
            response=client.chat.completions.create(model=model,messages=[{"role":"user","content":prompt}],
                temperature=float(os.getenv("TEMPERATURE","0")),max_tokens=int(os.getenv("MAX_TOKENS","512")))
            ms=(time.perf_counter()-start)*1000; choice=response.choices[0]; usage=response.usage
            return choice.message.content or "",ms,getattr(usage,"prompt_tokens",None),getattr(usage,"completion_tokens",None),None
        except Exception as exc:
            error=type(exc).__name__+": "+str(exc)
            if attempt+1<int(os.getenv("RETRY_LIMIT","3")): time.sleep(min(2**attempt+random.random(),10))
    return "",0,None,None,error

def run_strategy(name,fn,test,demos,client,model):
    predictions=[]; golds=[]; raws=[]; rows=[]; latencies=[]
    for _,r in tqdm(test.iterrows(),total=len(test),desc=name):
        title=str(r.get("item_name","")); bullets=str(r.get("bullet_points_text",""))
        prompt=fn(title,bullets,demos) if name=="few_shot" else fn(title,bullets)
        raw,ms,pt,ct,error=call_model(client,model,prompt); pred=safe_parse_json(raw); gold=gold_record(r)
        predictions.append(pred); golds.append(gold); raws.append(raw); latencies.append(ms)
        rows.append({"item_id":str(r.item_id),"raw":raw,"prediction":pred,"gold":gold,
                     "source":title+" "+bullets,"error":error,"latency_ms":ms,
                     "prompt_tokens":pt,"completion_tokens":ct})
    metrics=evaluate_batch(predictions,golds,raws,[x["source"] for x in rows])
    good=sorted(x for x in latencies if x>0)
    if good:
        metrics.update({"latency_mean_ms":sum(good)/len(good),
            "latency_p50_ms":good[int(.50*(len(good)-1))],"latency_p95_ms":good[int(.95*(len(good)-1))]})
    metrics["request_failure_rate"]=sum(bool(x["error"]) for x in rows)/len(rows)
    metrics["total_prompt_tokens"]=sum(x["prompt_tokens"] or 0 for x in rows)
    metrics["total_completion_tokens"]=sum(x["completion_tokens"] or 0 for x in rows)
    row_em=[float(all(str(p.get(k) or "").strip().casefold()==str(g.get(k) or "").strip().casefold()
                 for k in ("brand","color","product_type","style","material","model_number")))
            for p,g in zip(predictions,golds)]
    return {"strategy":name,"metrics":metrics,"rows":rows,"row_exact_match":row_em}

def main():
    provider=os.getenv("PROVIDER","groq").lower(); model=os.getenv("MODEL_NAME",DEFAULT_MODELS.get(provider,""))
    seed=int(os.getenv("RANDOM_SEED","42")); df=load_data(os.getenv("DATA_PATH","data/final_clean_amazon.jsonl"))
    train,demo_df,test=split_data(df,float(os.getenv("TEST_SIZE",".2")),int(os.getenv("DEMO_SIZE","4")),seed)
    size=int(os.getenv("SAMPLE_SIZE","200"))
    if size>0: test=test.sample(n=min(size,len(test)),random_state=seed).sort_index()
    demos=prepare_examples(demo_df,len(demo_df)); client=make_client(provider)
    strategies=[x.strip() for x in os.getenv("STRATEGIES",",".join(PROMPT_MAP)).split(",") if x.strip()]
    if set(strategies)-set(PROMPT_MAP): raise ValueError("Unknown strategy requested")
    mlflow.set_experiment("LLM_Prompt_Benchmark"); results=[]
    with mlflow.start_run(run_name=provider+"_"+model+"_"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")):
        mlflow.log_params({"provider":provider,"model":model,"seed":seed,"dataset_rows":len(df),
                           "train_rows":len(train),"demo_rows":len(demo_df),"test_rows":len(test)})
        mlflow.set_tags({"split_policy":"train-only-demonstrations; untouched-holdout",
                         "dataset_path":os.getenv("DATA_PATH","data/final_clean_amazon.jsonl")})
        for name in strategies:
            result=run_strategy(name,PROMPT_MAP[name],test,demos,client,model); results.append(result)
            for key,value in result["metrics"].items():
                if isinstance(value,(int,float)): mlflow.log_metric(name+"_"+key,float(value))
        baseline=next((x for x in results if x["strategy"]=="zero_shot"),None); comparisons={}
        if baseline:
            for item in results:
                if item is baseline: continue
                comparisons[item["strategy"]]={"paired_bootstrap":paired_bootstrap_ci(item["row_exact_match"],baseline["row_exact_match"]),
                    "paired_sign_test":paired_sign_test(item["row_exact_match"],baseline["row_exact_match"])}
        payload={"metadata":{"provider":provider,"model":model,"seed":seed,"dataset_rows":len(df),
            "train_rows":len(train),"demo_ids":demo_df.item_id.astype(str).tolist(),
            "test_ids":test.item_id.astype(str).tolist(),"timestamp_utc":datetime.now(timezone.utc).isoformat(),
            "unsupported_metric_note":"Lexical evidence heuristic, not semantic fact checking."},
            "results":results,"paired_comparisons_vs_zero_shot":comparisons}
        Path("results").mkdir(exist_ok=True)
        path=Path("results")/(provider+"_"+model.replace("/","_")+"_"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+".json")
        path.write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding="utf-8"); mlflow.log_artifact(str(path))
        print("Saved",path)
if __name__=="__main__": main()
