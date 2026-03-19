from __future__ import annotations

from sqlite3 import Connection

SCHEMA_VERSION_TABLE = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
)
"""

SETTINGS_TABLE = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT NOT NULL PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
)
"""


def create_base_schema(conn: Connection) -> None:
    """Create the base schema objects that must always exist."""
    conn.execute(SCHEMA_VERSION_TABLE)


def create_settings_table(conn: Connection) -> None:
    """Create the dedicated settings table that repositories can use."""
    conn.execute(SETTINGS_TABLE)
