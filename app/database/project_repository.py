from __future__ import annotations

import json
from typing import Callable, List, Optional

from app.database.connection import connection_context
from app.database.schema import create_projects_table
from app.models.project_models import ProcessDef


def _with_table(func: Callable[..., None] | Callable[..., List[ProcessDef]]):
    def wrapper(*args, **kwargs):
        with connection_context() as conn:
            create_projects_table(conn)
            return func(*args, conn=conn, **kwargs)

    return wrapper


class ProjectsRepository:
    TABLE = "projects"

    def _serialize(self, process: ProcessDef) -> str:
        return json.dumps(process.to_dict(), allow_nan=False, ensure_ascii=False)

    def _deserialize(self, payload: str) -> ProcessDef:
        data = json.loads(payload)
        return ProcessDef.from_dict(data)

    @_with_table
    def list_all(self, *, conn) -> List[ProcessDef]:
        rows = conn.execute(f"SELECT payload FROM {self.TABLE}").fetchall()
        return [self._deserialize(row[0]) for row in rows]

    @_with_table
    def get_by_id(self, process_id: str, *, conn) -> Optional[ProcessDef]:
        row = conn.execute(
            f"SELECT payload FROM {self.TABLE} WHERE id = ?", (process_id,)
        ).fetchone()
        return self._deserialize(row[0]) if row else None

    @_with_table
    def save(self, process: ProcessDef, *, conn) -> None:
        conn.execute(
            f"INSERT OR REPLACE INTO {self.TABLE} (id, payload) VALUES (?, ?)",
            (process.id, self._serialize(process)),
        )

    @_with_table
    def delete(self, process_id: str, *, conn) -> bool:
        cur = conn.execute(
            f"DELETE FROM {self.TABLE} WHERE id = ?", (process_id,)
        )
        return cur.rowcount > 0
