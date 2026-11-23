"""Agreement and per-criterion reliability metrics for LLM judges."""
from __future__ import annotations
from collections import Counter, defaultdict
from typing import Any

LABELS=("pass","fail","not_applicable")

def _cohen_kappa(pairs: list[tuple[str,str]]) -> float | None:
    n=len(pairs)
    if not n: return None
    observed=sum(a==b for a,b in pairs)/n
    left=Counter(a for a,_ in pairs); right=Counter(b for _,b in pairs)
    expected=sum((left[k]/n)*(right[k]/n) for k in LABELS)
    return 1.0 if expected==1.0 and observed==1.0 else (0.0 if expected==1.0 else (observed-expected)/(1-expected))

def calculate_calibration(records: list[dict[str,Any]], *, min_samples: int=5,
                          reliability_threshold: float=0.80) -> dict:
    """Compare judge labels with adjudicated labels or human-majority labels."""
    groups=defaultdict(list)
    for row in records:
        judge=row.get("judge_verdict"); human=row.get("human_verdict")
        if judge not in LABELS or human not in LABELS: continue
        groups[row["component_id"]].append((judge,human,row))
    criterion_results=[]
    all_pairs=[]
    for component,items in sorted(groups.items()):
        pairs=[(x[0],x[1]) for x in items]; all_pairs.extend(pairs)
        n=len(pairs); correct=sum(a==b for a,b in pairs)
        tp=sum(a=="pass" and b=="pass" for a,b in pairs)
        fp=sum(a=="pass" and b=="fail" for a,b in pairs)
        fn=sum(a=="fail" and b=="pass" for a,b in pairs)
        precision=tp/(tp+fp) if tp+fp else None
        recall=tp/(tp+fn) if tp+fn else None
        f1=(2*precision*recall/(precision+recall)) if precision is not None and recall is not None and precision+recall else None
        agreement=correct/n
        kappa=_cohen_kappa(pairs)
        if n<min_samples: flag="insufficient_data"
        elif agreement<reliability_threshold or (kappa is not None and kappa<0.4): flag="review"
        else: flag="reliable"
        criterion_results.append({"component_id":component,"category":items[0][2].get("parent_category"),
          "criterion_name":items[0][2].get("criterion_name"),"sample_count":n,
          "exact_agreement":round(agreement,4),"cohen_kappa":round(kappa,4) if kappa is not None else None,
          "pass_precision":round(precision,4) if precision is not None else None,
          "pass_recall":round(recall,4) if recall is not None else None,
          "pass_f1":round(f1,4) if f1 is not None else None,"reliability_status":flag})
    n=len(all_pairs)
    overall={"sample_count":n,"exact_agreement":round(sum(a==b for a,b in all_pairs)/n,4) if n else None,
             "cohen_kappa":round(_cohen_kappa(all_pairs),4) if n and _cohen_kappa(all_pairs) is not None else None}
    flagged=[x for x in criterion_results if x["reliability_status"]!="reliable"]
    return {"overall":overall,"criteria":criterion_results,"flagged_criteria":flagged,
            "method":"Three-class exact agreement and Cohen's kappa; pass-class precision/recall/F1. "
                     "Adjudicated verdicts take precedence; otherwise human-majority labels are used.",
            "thresholds":{"minimum_samples":min_samples,"minimum_exact_agreement":reliability_threshold,
                          "minimum_kappa_for_review":0.4}}
