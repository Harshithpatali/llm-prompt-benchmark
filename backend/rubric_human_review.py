"""Human criterion annotation, adjudication and judge-calibration persistence."""
from __future__ import annotations
import json
from uuid import UUID
from backend.db import connection

def create_rubric_review_task(evaluation_id: UUID) -> dict:
    with connection() as conn:
        ev=conn.execute(
            """SELECT e.rubric_evaluation_id,e.prompt_text,e.response_text,r.rubric_name,r.version_label
               FROM public.rubric_evaluations e JOIN public.rubrics r USING(rubric_id)
               WHERE e.rubric_evaluation_id=%s""",(evaluation_id,)).fetchone()
        if not ev: raise LookupError("Rubric evaluation not found")
        row=conn.execute(
            """INSERT INTO public.annotation_tasks
               (task_key,source_dataset,source_task_id,rubric_evaluation_id,category,difficulty,
                query,candidate_response,review_guidance)
               VALUES (%s,'rubric_evaluation',%s,%s,'rubric_judging',NULL,%s,%s,%s)
               ON CONFLICT (rubric_evaluation_id) WHERE rubric_evaluation_id IS NOT NULL
               DO UPDATE SET updated_at=now()
               RETURNING annotation_task_id,task_key,status,assigned_to,created_at""",
            ("rubric-eval:"+str(evaluation_id),str(evaluation_id),evaluation_id,
             ev["prompt_text"],ev["response_text"],
             "Independently assess each criterion in the linked rubric evaluation; use evidence from the response.")
        ).fetchone()
    return dict(row)

def list_rubric_review_tasks(limit: int=100) -> list[dict]:
    with connection() as conn:
        rows=conn.execute(
            """SELECT t.annotation_task_id,t.rubric_evaluation_id,t.task_key,t.status,t.assigned_to,
                      t.query,t.candidate_response,t.created_at,r.rubric_name,r.version_label
               FROM public.annotation_tasks t
               LEFT JOIN public.rubric_evaluations e ON e.rubric_evaluation_id=t.rubric_evaluation_id
               LEFT JOIN public.rubrics r ON r.rubric_id=e.rubric_id
               WHERE t.rubric_evaluation_id IS NOT NULL ORDER BY t.created_at DESC LIMIT %s""",(limit,)).fetchall()
    return [dict(x) for x in rows]

def submit_rubric_human_annotation(*, evaluation_id: UUID, component_id: str,
                                   annotator_id: str, verdict: str, evidence: str,
                                   rationale: str, confidence: int) -> dict:
    if verdict not in {"pass","fail","not_applicable"}: raise ValueError("Invalid human verdict")
    if len(evidence.strip()) < 3: raise ValueError("Evidence must contain at least 3 characters")
    with connection() as conn:
        criterion=conn.execute(
            "SELECT 1 FROM public.rubric_criterion_scores WHERE rubric_evaluation_id=%s AND component_id=%s",
            (evaluation_id,component_id)).fetchone()
        if not criterion: raise LookupError("Criterion not found in this evaluation")
        row=conn.execute(
            """INSERT INTO public.rubric_human_annotations
               (rubric_evaluation_id,component_id,annotator_id,verdict,evidence,rationale,confidence)
               VALUES (%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (rubric_evaluation_id,component_id,annotator_id)
               DO UPDATE SET verdict=EXCLUDED.verdict,evidence=EXCLUDED.evidence,
                 rationale=EXCLUDED.rationale,confidence=EXCLUDED.confidence,created_at=now()
               RETURNING human_annotation_id,rubric_evaluation_id,component_id,annotator_id,verdict,created_at""",
            (evaluation_id,component_id,annotator_id,verdict,evidence.strip(),rationale.strip(),confidence)).fetchone()
        conn.execute("""INSERT INTO public.audit_events(actor_id,event_type,entity_type,entity_id,payload)
                        VALUES (%s,'rubric.human_annotation.submitted','rubric_evaluation',%s,%s::jsonb)""",
                     (annotator_id,str(evaluation_id),json.dumps({"component_id":component_id,"verdict":verdict})))
    return dict(row)

def adjudicate_rubric_criterion(*, evaluation_id: UUID, component_id: str,
                                adjudicator_id: str, verdict: str, evidence: str, notes: str) -> dict:
    if verdict not in {"pass","fail","not_applicable"}: raise ValueError("Invalid adjudication verdict")
    if len(evidence.strip()) < 3: raise ValueError("Adjudication evidence must contain at least 3 characters")
    with connection() as conn:
        exists=conn.execute("SELECT 1 FROM public.rubric_criterion_scores WHERE rubric_evaluation_id=%s AND component_id=%s",
                            (evaluation_id,component_id)).fetchone()
        if not exists: raise LookupError("Criterion not found in this evaluation")
        row=conn.execute(
            """INSERT INTO public.rubric_adjudications
               (rubric_evaluation_id,component_id,adjudicator_id,final_verdict,evidence,notes)
               VALUES (%s,%s,%s,%s,%s,%s)
               ON CONFLICT (rubric_evaluation_id,component_id)
               DO UPDATE SET adjudicator_id=EXCLUDED.adjudicator_id,final_verdict=EXCLUDED.final_verdict,
                 evidence=EXCLUDED.evidence,notes=EXCLUDED.notes,created_at=now()
               RETURNING rubric_adjudication_id,rubric_evaluation_id,component_id,adjudicator_id,final_verdict,created_at""",
            (evaluation_id,component_id,adjudicator_id,verdict,evidence.strip(),notes.strip())).fetchone()
        conn.execute("""INSERT INTO public.audit_events(actor_id,event_type,entity_type,entity_id,payload)
                        VALUES (%s,'rubric.criterion.adjudicated','rubric_evaluation',%s,%s::jsonb)""",
                     (adjudicator_id,str(evaluation_id),json.dumps({"component_id":component_id,"verdict":verdict})))
    return dict(row)

def get_calibration_records(rubric_id: UUID | None=None) -> list[dict]:
    with connection() as conn:
        rows=conn.execute(
            """SELECT e.rubric_evaluation_id,e.judge_model,e.provider,e.created_at,
                      s.component_id,s.parent_category,s.criterion_name,s.verdict AS judge_verdict,
                      COALESCE(a.final_verdict, hm.majority_verdict) AS human_verdict,
                      COALESCE(a.adjudicator_id, hm.annotator_count::text) AS human_source,
                      s.confidence
               FROM public.rubric_evaluations e
               JOIN public.rubric_criterion_scores s USING(rubric_evaluation_id)
               LEFT JOIN public.rubric_adjudications a
                 ON a.rubric_evaluation_id=s.rubric_evaluation_id AND a.component_id=s.component_id
               LEFT JOIN LATERAL (
                 SELECT (array_agg(verdict ORDER BY cnt DESC,verdict))[1] AS majority_verdict,
                        count(*) AS annotator_count
                 FROM (SELECT verdict,count(*) AS cnt FROM public.rubric_human_annotations h
                       WHERE h.rubric_evaluation_id=s.rubric_evaluation_id AND h.component_id=s.component_id
                       GROUP BY verdict) votes
               ) hm ON TRUE
               WHERE COALESCE(a.final_verdict,hm.majority_verdict) IS NOT NULL
                 AND (%s::uuid IS NULL OR e.rubric_id=%s::uuid)
               ORDER BY e.created_at,s.component_id""",(rubric_id,rubric_id)).fetchall()
    return [dict(x) for x in rows]

def save_calibration_run(*, model: str, metrics: dict, thresholds: dict, metadata: dict) -> dict:
    with connection() as conn:
        row=conn.execute(
            """INSERT INTO public.judge_calibration_runs
               (evaluator_version,thresholds,validation_metrics,holdout_metrics,metadata)
               VALUES (%s,%s::jsonb,%s::jsonb,'{}'::jsonb,%s::jsonb)
               RETURNING calibration_run_id,created_at""",
            (model,json.dumps(thresholds),json.dumps(metrics),json.dumps(metadata))).fetchone()
    return dict(row)
