"""Minimal PostgreSQL connection boundary for the consolidated platform.

This module deliberately does not connect at import time. Set DATABASE_URL only
in the runtime environment; never commit a Neon connection string.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator, Any


class DatabaseConfigurationError(RuntimeError):
    """Raised when database configuration is missing or invalid."""


def _database_url() -> str:
    value = os.getenv("DATABASE_URL", "").strip()
    if not value:
        raise DatabaseConfigurationError("DATABASE_URL is not configured")
    if not value.startswith(("postgresql://", "postgres://")):
        raise DatabaseConfigurationError("DATABASE_URL must be a PostgreSQL connection URL")
    return value


@contextmanager
def connection() -> Iterator[Any]:
    """Yield a psycopg connection with TLS required and a short connect timeout."""
    dsn = _database_url()
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise DatabaseConfigurationError(
            "Install the PostgreSQL driver with: pip install 'psycopg[binary]'"
        ) from exc

    conn = psycopg.connect(
        dsn,
        connect_timeout=5,
        sslmode="require",
        row_factory=dict_row,
    )
    try:
        yield conn
    finally:
        conn.close()


def healthcheck() -> dict[str, Any]:
    """Run a minimal database read; never expose the connection URL."""
    with connection() as conn:
        row = conn.execute("SELECT current_database() AS database, 1 AS ok").fetchone()
    return {"status": "ok", "database": row["database"]}
