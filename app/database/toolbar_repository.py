from __future__ import annotations

import uuid
from typing import Any, Callable, Dict, List, Optional

from app.database.connection import connection_context
from app.database.schema import create_toolbar_table


def _with_table(func: Callable[..., Any]):
    def wrapper(*args, **kwargs):
        with connection_context() as conn:
            create_toolbar_table(conn)
            return func(*args, conn=conn, **kwargs)

    return wrapper


class ToolbarRepository:
    TABLE = "toolbar_items"

    def _row_to_item(self, row) -> Dict[str, str]:
        return {
            "id": row["id"],
            "title": row["title"],
            "target": row["target"],
            "kind": row["kind"],
        }

    def _normalize(self, raw: Dict[str, str]) -> Dict[str, str]:
        item_id = str(raw.get("id") or uuid.uuid4())
        title = str(raw.get("title") or "Acceso").strip()
        if not title:
            title = "Acceso"
        target = str(raw.get("target") or "").strip()
        kind = str(raw.get("kind") or "link").strip() or "link"
        return {"id": item_id, "title": title, "target": target, "kind": kind}

    def _next_sort_index(self, conn) -> int:
        row = conn.execute(
            f"SELECT MAX(sort_index) FROM {self.TABLE}"
        ).fetchone()
        max_index = row[0]
        return int(max_index) + 1 if max_index is not None else 0

    @_with_table
    def list_items(self, *, conn) -> List[Dict[str, str]]:
        rows = conn.execute(
            f"SELECT id, title, target, kind FROM {self.TABLE} ORDER BY sort_index ASC"
        ).fetchall()
        return [self._row_to_item(row) for row in rows]

    @_with_table
    def insert_item(self, item: Dict[str, str], *, conn) -> Dict[str, str]:
        normalized = self._normalize(item)
        sort_index = self._next_sort_index(conn)
        conn.execute(
            f"""INSERT INTO {self.TABLE}
            (id, title, target, kind, sort_index)
            VALUES (?, ?, ?, ?, ?)""",
            (
                normalized["id"],
                normalized["title"],
                normalized["target"],
                normalized["kind"],
                sort_index,
            ),
        )
        return normalized

    @_with_table
    def update_item(
        self,
        item_id: str,
        *,
        conn,
        title: Optional[str] = None,
        target: Optional[str] = None,
        kind: Optional[str] = None,
    ) -> bool:
        row = conn.execute(
            f"SELECT title, target, kind FROM {self.TABLE} WHERE id = ?", (item_id,)
        ).fetchone()
        if not row:
            return False
        new_title = title.strip() if title is not None else row["title"]
        if not new_title:
            new_title = row["title"]
        new_target = target.strip() if target is not None else row["target"]
        new_kind = kind.strip() if kind is not None else row["kind"]
        conn.execute(
            f"""UPDATE {self.TABLE}
            SET title = ?, target = ?, kind = ?, updated_at = datetime('now')
            WHERE id = ?""",
            (new_title, new_target, new_kind, item_id),
        )
        return True

    @_with_table
    def delete_item(self, item_id: str, *, conn) -> bool:
        cur = conn.execute(
            f"DELETE FROM {self.TABLE} WHERE id = ?", (item_id,)
        )
        return cur.rowcount > 0
