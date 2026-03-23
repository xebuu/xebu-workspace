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

PROJECTS_TABLE = """
CREATE TABLE IF NOT EXISTS projects (
    id TEXT NOT NULL PRIMARY KEY,
    payload TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
)
"""

TASKS_TABLE = """
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
)
"""

ARCHIVED_TASKS_TABLE = """
CREATE TABLE IF NOT EXISTS archived_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payload TEXT NOT NULL,
    archived_at TEXT NOT NULL DEFAULT (datetime('now'))
)
"""


TOOLBAR_TABLE = """
CREATE TABLE IF NOT EXISTS toolbar_items (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    target TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'link',
    sort_index INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
)
"""


def create_base_schema(conn: Connection) -> None:
    """Create the base schema objects that must always exist."""
    conn.execute(SCHEMA_VERSION_TABLE)


def create_settings_table(conn: Connection) -> None:
    """Create the dedicated settings table that repositories can use."""
    conn.execute(SETTINGS_TABLE)


def create_projects_table(conn: Connection) -> None:
    """Create the projects table used by ProjectsRepository."""
    conn.execute(PROJECTS_TABLE)


def create_tasks_table(conn: Connection) -> None:
    """Create the task table used by TasksRepository."""
    conn.execute(TASKS_TABLE)


def create_archived_tasks_table(conn: Connection) -> None:
    """Create the archive table used by ArchivedTasksRepository."""
    conn.execute(ARCHIVED_TASKS_TABLE)


def create_toolbar_table(conn: Connection) -> None:
    """Create the toolbar table used by ToolbarRepository."""
    conn.execute(TOOLBAR_TABLE)
