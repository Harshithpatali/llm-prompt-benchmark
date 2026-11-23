import json
import re
import unicodedata
from math import comb
from typing import Any, Dict, Sequence

FIELDS = ("brand", "color", "product_type", "style", "material", "model_number")
ALIASES = {"product_type": ("product_type", "category", "item_type")}

def normalize(value: Any) -> str:
    if value is None: return ""
    return re.sub(r"\\s+", " ", unicodedata.normalize("NFKC", str(value)).casefold().strip())

def safe_parse_json(raw: str) -> Dict[str, Any]:
    if not raw: return {}
    text = re.sub(r"^\x60{3}(?:json)?\\s*|\\s*\x60{3}$", "", raw.strip(), flags=re.I).strip()
    try: value = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start: return {}
        try: value = json.loads(text[start:end + 1])
        except json.JSONDecodeError: return {}
    return value if isinstance(value, dict) else {}

def _get(record, field):
    for key in ALIASES.get(field, (field,)):
        if key in record: return record[key]
    return None

def _supported(value, source):
    candidate = normalize(value)
    if not candidate: return True
    text = normalize(source)
    if candidate in text: return True
    tokens = {x for x in re.findall(r"[a-z0-9]+", candidate) if len(x) > 2}
    return bool(tokens) and tokens.issubset(set(re.findall(r"[a-z0-9]+", text)))

def evaluate_batch(predictions: Sequence[Dict], golds: Sequence[Dict],
                   raw_outputs=None, sources=None) -> Dict[str, Any]:
    if len(predictions) != len(golds): raise ValueError("predictions and golds must have equal length")
    n = len(predictions)
    if not n: return {"n_samples": 0}
    per = {}; tp = fp = fn = missing = gold_count = predicted_count = hallucinated = supported = 0
    row_exact = []
    for field in FIELDS:
        a = b = c = 0
        for p, g in zip(predictions, golds):
            pv, gv = normalize(_get(p or {}, field)), normalize(_get(g or {}, field))
            predicted_count += bool(pv); gold_count += bool(gv)
            if pv and gv and pv == gv: a += 1
            elif pv and gv: b += 1; c += 1
            elif pv and not gv: b += 1
            elif gv and not pv: c += 1; missing += 1
        precision = a / (a+b) if a+b else 0.0
        recall = a / (a+c) if a+c else 0.0
        per[field] = {"precision":precision,"recall":recall,
                      "f1":2*precision*recall/(precision+recall) if precision+recall else 0.0,
                      "exact_match":a/n}
        tp += a; fp += b; fn += c
    for p,g in zip(predictions,golds):
        row_exact.append(all(normalize(_get(p or {},f)) == normalize(_get(g or {},f)) for f in FIELDS))
    for i,p in enumerate(predictions):
        source = sources[i] if sources and i < len(sources) else ""
        for f in FIELDS:
            v = _get(p or {},f)
            if v not in (None,"",[]):
                supported += 1
                if not _supported(v,source): hallucinated += 1
    precision = tp/(tp+fp) if tp+fp else 0.0
    recall = tp/(tp+fn) if tp+fn else 0.0
    valid = sum(bool(safe_parse_json(x)) for x in raw_outputs)/len(raw_outputs) if raw_outputs is not None and raw_outputs else (0.0 if raw_outputs is not None else None)
    return {"n_samples":n,"overall":sum(row_exact)/n,
            "micro_precision":precision,"micro_recall":recall,
            "micro_f1":2*precision*recall/(precision+recall) if precision+recall else 0.0,
            "macro_f1":sum(v["f1"] for v in per.values())/len(FIELDS),
            "missing_attribute_rate":missing/gold_count if gold_count else 0.0,
            "attribute_coverage":predicted_count/(n*len(FIELDS)),
            "unsupported_attribute_rate":hallucinated/supported if supported else 0.0,
            "json_validity_rate":valid,"per_attribute":per}

def paired_bootstrap_ci(a: Sequence[float], b: Sequence[float], iterations=2000, seed=42, confidence=.95):
    import numpy as np
    if len(a)!=len(b) or not len(a): raise ValueError("paired arrays must be non-empty and equal length")
    x,y=np.asarray(a,float),np.asarray(b,float); rng=np.random.default_rng(seed)
    samples=np.empty(iterations)
    for i in range(iterations):
        idx=rng.integers(0,len(x),len(x)); samples[i]=np.mean(x[idx]-y[idx])
    alpha=(1-confidence)/2
    return {"mean_difference":float(np.mean(x-y)),"ci_lower":float(np.quantile(samples,alpha)),
            "ci_upper":float(np.quantile(samples,1-alpha)),"confidence":confidence}

def paired_sign_test(a: Sequence[float], b: Sequence[float]):
    if len(a)!=len(b): raise ValueError("paired arrays must have equal length")
    d=[x-y for x,y in zip(a,b)]; wins=sum(x>0 for x in d); losses=sum(x<0 for x in d); n=wins+losses
    tail=sum(comb(n,i) for i in range(min(wins,losses)+1))/(2**n) if n else .5
    return {"wins":wins,"losses":losses,"ties":len(d)-n,"p_value":min(1.0,2*tail)}
