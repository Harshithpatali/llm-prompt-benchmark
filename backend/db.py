"""PostgreSQL connection boundary for Neon.

Connections are lazy: importing the application never opens a database session.
All statements use parameter binding; DATABASE_URL must be supplied at runtime.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator, Any


class DatabaseConfigurationError(RuntimeError):
    """Raised when database configuration is missing or invalid."""


class DatabaseUnavailableError(RuntimeError):
    """Raised when the database driver or server is unavailable."""


def _database_url() -> str:
    value = os.getenv("DATABASE_URL", "").strip()
    if not value:
        raise DatabaseConfigurationError("DATABASE_URL is not configured")
    if not value.startswith(("postgresql://", "postgres://")):
        raise DatabaseConfigurationError("DATABASE_URL must be a PostgreSQL connection URL")
    return value


@contextmanager
def connection() -> Iterator[Any]:
    """Yield a TLS-required psycopg connection with commit/rollback semantics."""
    dsn = _database_url()
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise DatabaseUnavailableError(
            "PostgreSQL driver is unavailable; install psycopg[binary]"
        ) from exc

    try:
        with psycopg.connect(
            dsn,
            connect_timeout=8,
            sslmode="require",
            row_factory=dict_row,
        ) as conn:
            yield conn
    except (DatabaseConfigurationError, DatabaseUnavailableError):
        raise
    except Exception as exc:
        raise DatabaseUnavailableError("PostgreSQL connection or query failed") from exc


def healthcheck() -> dict[str, Any]:
    """Run a read-only connection test; never expose the connection URL."""
    with connection() as conn:
        row = conn.execute(
            "SELECT current_database() AS database, current_user AS role, 1 AS ok"
        ).fetchone()
    return {"status": "ok", "database": row["database"], "role": row["role"]}
