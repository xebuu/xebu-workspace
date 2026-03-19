from __future__ import annotations

from typing import Dict, Optional

from app.database.connection import connection_context


class SettingsRepository:
    """Minimal key/value store that builds on the sqlite settings table."""

    TABLE = "settings"

    def get(self, key: str) -> Optional[str]:
        with connection_context() as conn:
            row = conn.execute(
                f"SELECT value FROM {self.TABLE} WHERE key = ?", (key,)
            ).fetchone()
            return row[0] if row else None

    def list_all(self) -> Dict[str, str]:
        with connection_context() as conn:
            cursor = conn.execute(f"SELECT key, value FROM {self.TABLE}")
            return {key: value for key, value in cursor}

    def upsert(self, key: str, value: str) -> None:
        with connection_context() as conn:
            conn.execute(
                f"INSERT OR REPLACE INTO {self.TABLE} (key, value) VALUES (?, ?)",
                (key, value),
            )

    def delete(self, key: str) -> bool:
        with connection_context() as conn:
            cur = conn.execute(f"DELETE FROM {self.TABLE} WHERE key = ?", (key,))
            return cur.rowcount > 0
