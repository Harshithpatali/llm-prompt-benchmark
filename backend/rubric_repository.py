"""Persistence helpers for versioned rubrics and criterion-level evaluations."""
from __future__ import annotations
import hashlib, json
from uuid import UUID
from backend.db import connection
from backend.rubric_qa import validate_csv

def save_rubric(*, name: str, version: str, objective: str, csv_text: str,
                provider: str | None, model: str | None, created_by: str) -> dict:
    qa = validate_csv(csv_text)
    if qa["status"] == "FAIL":
        raise ValueError("Rubric failed QA and cannot be saved")
    digest = hashlib.sha256(csv_text.encode("utf-8")).hexdigest()
    dimensions = qa["rows"]
    decision_rules = {"qa_status": qa["status"], "qa_counts": qa["counts"],
                      "qa_issues": qa["issues"], "framework": "Universal Rubric Framework"}
    with connection() as conn:
        row = conn.execute(
            """INSERT INTO public.rubrics
               (rubric_name, version_label, objective, dimensions, decision_rules,
                generator_provider, generator_model, source_csv, sha256, created_by)
               VALUES (%s,%s,%s,%s::jsonb,%s::jsonb,%s,%s,%s,%s,%s)
               RETURNING rubric_id, rubric_name, version_label, status, sha256, created_at""",
            (name, version, objective, json.dumps(dimensions), json.dumps(decision_rules),
             provider, model, csv_text, digest, created_by)
        ).fetchone()
    return dict(row)

def list_rubrics(limit: int = 50, offset: int = 0) -> list[dict]:
    with connection() as conn:
        rows=conn.execute(
            """SELECT rubric_id,rubric_name,version_label,objective,status,
                      generator_provider,generator_model,approved_by,approved_at,created_by,sha256,created_at
               FROM public.rubrics ORDER BY created_at DESC LIMIT %s OFFSET %s""",(limit,offset)).fetchall()
    return [dict(r) for r in rows]

def get_rubric(rubric_id: UUID) -> dict | None:
    with connection() as conn:
        row=conn.execute(
            """SELECT rubric_id,rubric_name,version_label,objective,dimensions,decision_rules,
                      status,generator_provider,generator_model,approved_by,approved_at,created_by,
                      sha256,source_csv,created_at FROM public.rubrics WHERE rubric_id=%s""",
            (rubric_id,)).fetchone()
    return dict(row) if row else None

def approve_rubric(rubric_id: UUID, approver: str) -> dict:
    with connection() as conn:
        row=conn.execute(
            """UPDATE public.rubrics SET status='approved', approved_by=%s, approved_at=now()
               WHERE rubric_id=%s AND status='draft'
               RETURNING rubric_id,rubric_name,version_label,status,approved_by,approved_at""",
            (approver,rubric_id)).fetchone()
        if row is None:
            exists=conn.execute("SELECT status FROM public.rubrics WHERE rubric_id=%s",(rubric_id,)).fetchone()
            if exists is None: raise LookupError("Rubric not found")
            raise ValueError("Only draft rubrics can be approved; current status: "+exists["status"])
        conn.execute("""INSERT INTO public.audit_events(actor_id,event_type,entity_type,entity_id,payload)
                        VALUES (%s,'rubric.approved','rubric',%s,%s::jsonb)""",
                     (approver,str(rubric_id),json.dumps({"version":row["version_label"]})))
    return dict(row)

def persist_rubric_evaluation(*, rubric_id: UUID, provider: str, model: str,
                               prompt: str, response: str, scores: list[dict],
                               summary: dict) -> dict:
    with connection() as conn:
        parent=conn.execute(
            """INSERT INTO public.rubric_evaluations
               (rubric_id,provider,judge_model,prompt_text,response_text,summary)
               VALUES (%s,%s,%s,%s,%s,%s::jsonb)
               RETURNING rubric_evaluation_id,created_at""",
            (rubric_id,provider,model,prompt,response,json.dumps(summary))).fetchone()
        rows=[(parent["rubric_evaluation_id"],s["component_id"],s["parent_category"],
               s["criterion_name"],s["evaluation_question"],s["verdict"],s["evidence"],
               s["rationale"],s.get("confidence")) for s in scores]
        conn.executemany(
            """INSERT INTO public.rubric_criterion_scores
               (rubric_evaluation_id,component_id,parent_category,criterion_name,
                evaluation_question,verdict,evidence,rationale,confidence)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",rows)
    return {"rubric_evaluation_id":str(parent["rubric_evaluation_id"]),
            "created_at":parent["created_at"],"summary":summary,"scores":scores}

def list_rubric_evaluations(rubric_id: UUID, limit: int = 20) -> list[dict]:
    with connection() as conn:
        rows=conn.execute(
            """SELECT rubric_evaluation_id,provider,judge_model,summary,created_at
               FROM public.rubric_evaluations WHERE rubric_id=%s ORDER BY created_at DESC LIMIT %s""",
            (rubric_id,limit)).fetchall()
    return [dict(r) for r in rows]

def get_rubric_evaluation(evaluation_id: UUID) -> dict | None:
    with connection() as conn:
        head=conn.execute(
            """SELECT rubric_evaluation_id,rubric_id,provider,judge_model,prompt_text,response_text,summary,created_at
               FROM public.rubric_evaluations WHERE rubric_evaluation_id=%s""",(evaluation_id,)).fetchone()
        if not head: return None
        scores=conn.execute(
            """SELECT component_id,parent_category,criterion_name,evaluation_question,
                      verdict,evidence,rationale,confidence
               FROM public.rubric_criterion_scores WHERE rubric_evaluation_id=%s ORDER BY component_id""",
            (evaluation_id,)).fetchall()
    result=dict(head); result["scores"]=[dict(s) for s in scores]; return result
