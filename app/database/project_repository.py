from __future__ import annotations

import json
import uuid
from typing import Any, Callable, Dict, List, Optional

from app.core.paths import FILES_JSON
from app.database.connection import connection_context
from app.database.schema import create_projects_table
from app.models.project_models import ProcessDef


def _with_table(func: Callable[..., None] | Callable[..., List[ProcessDef]]):
    def wrapper(*args, **kwargs):
        with connection_context() as conn:
            create_projects_table(conn)
            return func(*args, conn=conn, **kwargs)

    return wrapper


def _save_legacy_project_store(data: Dict[str, Any]) -> None:
    FILES_JSON.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _load_legacy_project_store() -> Dict[str, Any]:
    FILES_JSON.parent.mkdir(parents=True, exist_ok=True)
    if not FILES_JSON.exists():
        FILES_JSON.write_text(
            json.dumps({"processes": [], "tasks": []}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    try:
        data = json.loads(FILES_JSON.read_text(encoding="utf-8")) or {}
    except json.JSONDecodeError:
        data = {}

    data.setdefault("processes", [])
    data.setdefault("tasks", [])

    changed = False
    processes = data["processes"]
    if not isinstance(processes, list):
        processes = []
        data["processes"] = processes
        changed = True

    for proc in processes:
        if not isinstance(proc, dict):
            continue
        if "id" not in proc:
            proc["id"] = str(uuid.uuid4())
            changed = True
        proc.setdefault("name", "Sin nombre")
        proc.setdefault("description", "")
        proc.setdefault("scripts", [])
        proc.setdefault("links", [])
        proc.setdefault("copiers", [])
        proc.setdefault("is_pinned", False)
        proc.setdefault("is_archived", False)
        proc.setdefault("archived_at", None)

    if changed:
        _save_legacy_project_store(data)

    return data


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
            store = _load_legacy_project_store()
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
