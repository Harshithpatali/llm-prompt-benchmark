"""Database access methods for evaluation runs and per-case results."""
from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from backend.db import connection


def create_run(
    *,
    run_type: str,
    provider: str,
    model_name: str,
    configuration: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    dataset_version_id: UUID | None = None,
) -> dict[str, Any]:
    with connection() as conn:
        row = conn.execute(
            """
            INSERT INTO public.evaluation_runs
                (run_type, dataset_version_id, provider, model_name, configuration, metadata)
            VALUES (%s, %s, %s, %s, %s::jsonb, %s::jsonb)
            RETURNING run_id, run_type, provider, model_name, status, started_at
            """,
            (
                run_type, dataset_version_id, provider, model_name,
                json.dumps(configuration or {}), json.dumps(metadata or {}),
            ),
        ).fetchone()
    return dict(row)


def add_results(run_id: UUID, results: list[dict[str, Any]]) -> int:
    if not results:
        return 0
    rows = []
    for item in results:
        rows.append((
            run_id,
            item["case_id"],
            item.get("strategy", "default"),
            item["category"],
            item.get("difficulty"),
            item["prompt"],
            item.get("context"),
            item.get("reference_answer"),
            item.get("response"),
            item["status"],
            json.dumps(item.get("metrics") or {}),
            item.get("error_type"),
            item.get("error_message"),
        ))
    with connection() as conn:
        conn.executemany(
            """
            INSERT INTO public.evaluation_results
                (run_id, case_id, strategy, category, difficulty, prompt, context,
                 reference_answer, response, status, metrics, error_type, error_message)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
            ON CONFLICT (run_id, case_id, strategy) DO NOTHING
            """,
            rows,
        )
    return len(rows)


def list_runs(*, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT run_id, run_type, provider, model_name, status, started_at, completed_at,
                   (SELECT count(*) FROM public.evaluation_results r WHERE r.run_id = e.run_id) AS result_count
            FROM public.evaluation_runs e
            ORDER BY started_at DESC
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        ).fetchall()
    return [dict(row) for row in rows]


def get_run(run_id: UUID) -> dict[str, Any] | None:
    with connection() as conn:
        run = conn.execute(
            """
            SELECT run_id, run_type, provider, model_name, status, configuration,
                   metadata, started_at, completed_at
            FROM public.evaluation_runs WHERE run_id = %s
            """,
            (run_id,),
        ).fetchone()
        if run is None:
            return None
        results = conn.execute(
            """
            SELECT case_id, strategy, category, difficulty, status, metrics,
                   latency_ms, prompt_tokens, completion_tokens, created_at
            FROM public.evaluation_results r
            LEFT JOIN public.evaluation_traces t USING (result_id)
            WHERE r.run_id = %s
            ORDER BY r.created_at, r.case_id
            """,
            (run_id,),
        ).fetchall()
    payload = dict(run)
    payload["results"] = [dict(row) for row in results]
    return payload
