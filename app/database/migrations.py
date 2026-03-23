from __future__ import annotations

from sqlite3 import Connection

from app.database.schema import (
    create_base_schema,
    create_projects_table,
    create_settings_table,
)

CURRENT_SCHEMA_VERSION = 3


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
    if current < 1:
        record_schema_version(conn, 1)
        current = 1
    if current < 2:
        create_settings_table(conn)
        record_schema_version(conn, 2)
        current = 2
    if current < 3:
        create_projects_table(conn)
        record_schema_version(conn, 3)
        current = 3
    return CURRENT_SCHEMA_VERSION
