"""PostgreSQL repository for evaluation history and human-review operations."""
from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from backend.db import connection


def create_run(*, run_type: str, provider: str, model_name: str,
               configuration: dict[str, Any] | None = None,
               metadata: dict[str, Any] | None = None,
               dataset_version_id: UUID | None = None) -> dict[str, Any]:
    with connection() as conn:
        row = conn.execute(
            """
            INSERT INTO public.evaluation_runs
                (run_type, dataset_version_id, provider, model_name, configuration, metadata)
            VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb)
            RETURNING run_id, run_type, provider, model_name, status, started_at
            """,
            (run_type, dataset_version_id, provider, model_name,
             json.dumps(configuration or {}), json.dumps(metadata or {})),
        ).fetchone()
    return dict(row)


def add_results(run_id: UUID, results: list[dict[str, Any]]) -> int:
    if not results:
        return 0
    rows = [(
        run_id, item["case_id"], item.get("strategy", "default"),
        item["category"], item.get("difficulty"), item["prompt"],
        item.get("context"), item.get("reference_answer"), item.get("response"),
        item["status"], json.dumps(item.get("metrics") or {}),
        item.get("error_type"), item.get("error_message"),
    ) for item in results]
    with connection() as conn:
        conn.executemany(
            """
            INSERT INTO public.evaluation_results
                (run_id, case_id, strategy, category, difficulty, prompt, context,
                 reference_answer, response, status, metrics, error_type, error_message)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
            ON CONFLICT (run_id, case_id, strategy) DO NOTHING
            """, rows,
        )
    return len(rows)


def list_runs(*, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT e.run_id, e.run_type, e.provider, e.model_name, e.status,
                   e.started_at, e.completed_at,
                   (SELECT count(*) FROM public.evaluation_results r WHERE r.run_id = e.run_id) AS result_count
            FROM public.evaluation_runs e
            ORDER BY e.started_at DESC LIMIT %s OFFSET %s
            """, (limit, offset),
        ).fetchall()
    return [dict(row) for row in rows]


def get_run(run_id: UUID) -> dict[str, Any] | None:
    with connection() as conn:
        run = conn.execute(
            """SELECT run_id, run_type, provider, model_name, status, configuration,
                      metadata, started_at, completed_at
               FROM public.evaluation_runs WHERE run_id = %s""", (run_id,),
        ).fetchone()
        if run is None:
            return None
        results = conn.execute(
            """
            SELECT r.case_id, r.strategy, r.category, r.difficulty, r.status, r.metrics,
                   t.latency_ms, t.prompt_tokens, t.completion_tokens, r.created_at
            FROM public.evaluation_results r
            LEFT JOIN public.evaluation_traces t ON t.result_id = r.result_id
            WHERE r.run_id = %s
            ORDER BY r.created_at, r.case_id
            """, (run_id,),
        ).fetchall()
    payload = dict(run)
    payload["results"] = [dict(row) for row in results]
    return payload


def create_review_tasks(tasks: list[dict[str, Any]]) -> int:
    if not tasks:
        return 0
    rows = [(
        task["review_task_id"], task["source_dataset"], task["review_task_id"],
        task["category"], task["difficulty"], task["query"], task["context"],
        task["candidate_response"], task["review_guidance"],
    ) for task in tasks]
    with connection() as conn:
        conn.executemany(
            """
            INSERT INTO public.annotation_tasks
                (task_key, source_dataset, source_task_id, category, difficulty,
                 query, context, candidate_response, review_guidance)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (task_key) DO NOTHING
            """, rows,
        )
    return len(rows)


def list_review_tasks(*, status: str | None = "pending", limit: int = 50,
                      offset: int = 0) -> list[dict[str, Any]]:
    with connection() as conn:
        if status is None:
            rows = conn.execute(
                """SELECT annotation_task_id, task_key, source_dataset, category,
                          difficulty, query, context, candidate_response, review_guidance,
                          status, assigned_to, created_at
                   FROM public.annotation_tasks ORDER BY created_at, task_key
                   LIMIT %s OFFSET %s""", (limit, offset),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT annotation_task_id, task_key, source_dataset, category,
                          difficulty, query, context, candidate_response, review_guidance,
                          status, assigned_to, created_at
                   FROM public.annotation_tasks WHERE status = %s
                   ORDER BY created_at, task_key LIMIT %s OFFSET %s""",
                (status, limit, offset),
            ).fetchall()
    return [dict(row) for row in rows]


def submit_annotation(task_id: UUID, annotation: dict[str, Any]) -> dict[str, Any]:
    """Insert one review and move its task to submitted in one transaction."""
    with connection() as conn:
        task = conn.execute(
            "SELECT task_key, status FROM public.annotation_tasks WHERE annotation_task_id = %s FOR UPDATE",
            (task_id,),
        ).fetchone()
        if task is None:
            raise LookupError("Review task not found")
        if task["status"] not in {"pending", "claimed"}:
            raise ValueError("Review task is not accepting submissions")
        row = conn.execute(
            """
            INSERT INTO public.annotations
                (annotation_task_id, annotator_id, relevance, correctness, completeness,
                 overall_label, evidence, confidence, handling_seconds, escalated,
                 defect_category, is_audit)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING annotation_id, annotation_task_id, annotator_id, overall_label, created_at
            """,
            (task_id, annotation["annotator_id"], annotation["relevance"],
             annotation["correctness"], annotation["completeness"], annotation["overall_label"],
             annotation["evidence"], annotation["confidence"], annotation["handling_seconds"],
             annotation["escalated"], annotation["defect_category"], annotation["is_audit"]),
        ).fetchone()
        conn.execute(
            "UPDATE public.annotation_tasks SET status = 'submitted', updated_at = now() WHERE annotation_task_id = %s",
            (task_id,),
        )
        conn.execute(
            """
            INSERT INTO public.audit_events (actor_id, event_type, entity_type, entity_id, payload)
            VALUES (%s, 'annotation.submitted', 'annotation_task', %s, %s::jsonb)
            """,
            (annotation["annotator_id"], str(task_id),
             json.dumps({"annotation_id": str(row["annotation_id"]), "decision": annotation["overall_label"]})),
        )
    return dict(row)


def list_annotations(*, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT a.annotation_id, a.annotation_task_id, t.task_key, t.category,
                   a.annotator_id, a.relevance, a.correctness, a.completeness,
                   a.overall_label, a.evidence, a.confidence, a.handling_seconds,
                   a.escalated, a.defect_category, a.is_audit, a.created_at
            FROM public.annotations a
            JOIN public.annotation_tasks t USING (annotation_task_id)
            ORDER BY a.created_at DESC LIMIT %s OFFSET %s
            """, (limit, offset),
        ).fetchall()
    return [dict(row) for row in rows]
