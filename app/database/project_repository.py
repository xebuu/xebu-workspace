from __future__ import annotations

import json
from typing import Callable, List, Optional

from app.database.connection import connection_context
from app.database.schema import create_projects_table
from app.models.project_models import ProcessDef
from app.utility.database import ProjectsRepo as LegacyProjectsRepo


def _with_table(func: Callable[..., None] | Callable[..., List[ProcessDef]]):
    def wrapper(*args, **kwargs):
        with connection_context() as conn:
            create_projects_table(conn)
            return func(*args, conn=conn, **kwargs)

    return wrapper


class ProjectsRepository:
    TABLE = "projects"

    def __init__(self):
        self._seeded = False

    def _serialize(self, process: ProcessDef) -> str:
        return json.dumps(process.to_dict(), allow_nan=False, ensure_ascii=False)

    def _deserialize(self, payload: str) -> ProcessDef:
        data = json.loads(payload)
        return ProcessDef.from_dict(data)

    def _maybe_import_json(self, conn) -> None:
        if self._seeded:
            return
        count = conn.execute(
            f"SELECT COUNT(1) FROM {self.TABLE}"
        ).fetchone()[0]
        if count == 0:
            legacy = LegacyProjectsRepo()
            store = legacy.load()
            for raw in store.get("processes", []):
                proc = ProcessDef.from_dict(raw)
                conn.execute(
                    f"INSERT OR REPLACE INTO {self.TABLE} (id, payload) VALUES (?, ?)",
                    (proc.id, self._serialize(proc)),
                )
        self._seeded = True

    @_with_table
    def list_all(self, *, conn) -> List[ProcessDef]:
        self._maybe_import_json(conn)
        rows = conn.execute(
            f"SELECT payload FROM {self.TABLE}"
        ).fetchall()
        return [self._deserialize(row[0]) for row in rows]

    @_with_table
    def get_by_id(self, process_id: str, *, conn) -> Optional[ProcessDef]:
        self._maybe_import_json(conn)
        row = conn.execute(
            f"SELECT payload FROM {self.TABLE} WHERE id = ?", (process_id,)
        ).fetchone()
        return self._deserialize(row[0]) if row else None

    @_with_table
    def save(self, process: ProcessDef, *, conn) -> None:
        self._maybe_import_json(conn)
        conn.execute(
            f"INSERT OR REPLACE INTO {self.TABLE} (id, payload) VALUES (?, ?)",
            (process.id, self._serialize(process)),
        )

    @_with_table
    def delete(self, process_id: str, *, conn) -> bool:
        self._maybe_import_json(conn)
        cur = conn.execute(
            f"DELETE FROM {self.TABLE} WHERE id = ?", (process_id,)
        )
        return cur.rowcount > 0
