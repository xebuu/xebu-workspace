from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from app.database.connection import connection_context
from app.database.schema import create_settings_table


def _with_table(func: Callable[..., Any]):
    """Decorator to ensure the settings table exists before db work."""

    def wrapper(*args, **kwargs):
        with connection_context() as conn:
            create_settings_table(conn)
            if not args:
                return func(conn, **kwargs)
            self_arg, *rest = args
            return func(self_arg, conn, *rest, **kwargs)

    return wrapper


class SettingsRepository:
    """Minimal key/value store that builds on the sqlite settings table."""

    TABLE = "settings"

    @_with_table
    def get(self, conn, key: str) -> Optional[str]:
        row = conn.execute(
            f"SELECT value FROM {self.TABLE} WHERE key = ?", (key,)
        ).fetchone()
        return row[0] if row else None

    @_with_table
    def list_all(self, conn) -> Dict[str, str]:
        cursor = conn.execute(f"SELECT key, value FROM {self.TABLE}")
        return {key: value for key, value in cursor}

    @_with_table
    def upsert(self, conn, key: str, value: str) -> None:
        conn.execute(
            f"INSERT OR REPLACE INTO {self.TABLE} (key, value) VALUES (?, ?)",
            (key, value),
        )

    @_with_table
    def delete(self, conn, key: str) -> bool:
        cur = conn.execute(f"DELETE FROM {self.TABLE} WHERE key = ?", (key,))
        return cur.rowcount > 0
