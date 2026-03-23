from __future__ import annotations

from contextlib import contextmanager
import sqlite3

from app.core.paths import get_db_path


def get_connection() -> sqlite3.Connection:
    """Return a sqlite3 connection favoring the configured DB path."""
    path = get_db_path()
    conn = sqlite3.connect(
        path,
        detect_types=sqlite3.PARSE_DECLTYPES,
        isolation_level=None,
    )
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def connection_context():
    """Simple context manager for connections."""
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()
