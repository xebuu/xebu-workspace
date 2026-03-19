from __future__ import annotations

from sqlite3 import Connection

from app.database.schema import create_base_schema

CURRENT_SCHEMA_VERSION = 1


def get_applied_version(conn: Connection) -> int:
    """Return the highest schema version that was successfully applied."""
    cur = conn.execute(
        "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
    )
    row = cur.fetchone()
    return int(row[0]) if row else 0


def record_schema_version(conn: Connection, version: int) -> None:
    """Persist the schema version marker."""
    conn.execute(
        "INSERT OR REPLACE INTO schema_version (version) VALUES (?)", (version,)
    )


def ensure_schema(conn: Connection) -> int:
    """Ensure the schema is fully created and return the active version."""
    create_base_schema(conn)
    current = get_applied_version(conn)
    if current < CURRENT_SCHEMA_VERSION:
        # future migrations would incrementally run here
        record_schema_version(conn, CURRENT_SCHEMA_VERSION)
    return CURRENT_SCHEMA_VERSION
