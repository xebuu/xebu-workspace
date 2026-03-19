from __future__ import annotations

from app.database.connection import connection_context
from app.database.migrations import ensure_schema


def initialize_database() -> int:
    """Ensure the SQLite store exists and schema is in place."""
    with connection_context() as conn:
        version = ensure_schema(conn)
        conn.commit()
        return version
