"""LLM-as-judge rubric evaluation with strict output validation."""
from __future__ import annotations
import json, re
from uuid import UUID
from backend.rubric_repository import get_rubric, persist_rubric_evaluation

def evaluate_response(*, rubric_id: UUID, provider: str, model: str, prompt: str,
                      response: str, client) -> dict:
    rubric=get_rubric(rubric_id)
    if rubric is None: raise LookupError("Rubric not found")
    if rubric["status"] != "approved":
        raise ValueError("Only approved rubric versions can be used for evaluation")
    criteria=[r for r in rubric["dimensions"] if str(r.get("Rubric Component Number","")).startswith(("C","O"))]
    if not criteria: raise ValueError("The selected rubric has no evaluable criteria")
    compact=[{"id":r["Rubric Component Number"],"category":r["Rubric Parent Category"],
              "name":r["Rubric Component Name"],"question":r["Rubric Evaluation Question"],
              "pass_fail_criteria":r["Pass/Fail Criteria"],
              "explicit_implicit":r["Implicit vs. Explicit in the Prompt"]} for r in criteria]
    system=("You are a strict rubric evaluator. Judge only the supplied assistant response against each criterion. "
            "Do not reward claims without evidence. Use verdict pass, fail, or not_applicable. "
            "For not_applicable, explain why the criterion does not apply. Evidence must be a short exact quote "
            "from the response where possible; use N/A if no supporting quote exists. Return JSON only.")
    user={"task":"Evaluate every criterion exactly once. Do not omit or invent IDs.",
          "user_prompt":prompt,"assistant_response":response,"criteria":compact,
          "required_json":{"scores":[{"component_id":"C1","verdict":"pass|fail|not_applicable",
             "evidence":"exact response quote or N/A","rationale":"brief explanation","confidence":0.0}]}}
    completion=client.chat.completions.create(
        model=model,temperature=0,
        messages=[{"role":"system","content":system},{"role":"user","content":json.dumps(user,ensure_ascii=False)}],
        response_format={"type":"json_object"},max_tokens=12000)
    raw=completion.choices[0].message.content or ""
    try: payload=json.loads(raw)
    except json.JSONDecodeError as exc: raise ValueError("Judge returned invalid JSON") from exc
    supplied=payload.get("scores")
    if not isinstance(supplied,list): raise ValueError("Judge output must contain a scores array")
    expected={r["Rubric Component Number"]:r for r in criteria}
    by_id={}
    for item in supplied:
        if not isinstance(item,dict): raise ValueError("Malformed criterion score")
        cid=item.get("component_id")
        if cid not in expected or cid in by_id: raise ValueError("Judge returned an unknown or duplicate component ID")
        verdict=item.get("verdict")
        if verdict not in {"pass","fail","not_applicable"}: raise ValueError("Invalid criterion verdict")
        evidence=str(item.get("evidence","N/A")).strip()[:2000] or "N/A"
        rationale=str(item.get("rationale","")).strip()[:3000]
        confidence=item.get("confidence",0.5)
        try: confidence=max(0.0,min(1.0,float(confidence)))
        except (TypeError,ValueError): confidence=0.5
        source=expected[cid]
        by_id[cid]={"component_id":cid,"parent_category":source["Rubric Parent Category"],
          "criterion_name":source["Rubric Component Name"],"evaluation_question":source["Rubric Evaluation Question"],
          "verdict":verdict,"evidence":evidence,"rationale":rationale,"confidence":confidence}
    missing=set(expected)-set(by_id)
    if missing: raise ValueError("Judge omitted criteria: "+", ".join(sorted(missing)))
    scores=[by_id[r["Rubric Component Number"]] for r in criteria]
    applicable=[s for s in scores if s["verdict"]!="not_applicable"]
    passed=sum(s["verdict"]=="pass" for s in applicable)
    failed=sum(s["verdict"]=="fail" for s in applicable)
    summary={"total_criteria":len(scores),"applicable_criteria":len(applicable),
             "passed":passed,"failed":failed,
             "not_applicable":len(scores)-len(applicable),
             "pass_rate":round(passed/len(applicable),4) if applicable else None,
             "evaluation_type":"LLM judge estimate; human review recommended"}
    return persist_rubric_evaluation(rubric_id=rubric_id,provider=provider,model=model,
        prompt=prompt,response=response,scores=scores,summary=summary)
