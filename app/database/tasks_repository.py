from __future__ import annotations

import json
import uuid
from datetime import date as date_cls
from typing import Callable, List

from app.database.connection import connection_context
from app.database.schema import create_tasks_table
from app.utility.database import TasksRepo as LegacyTasksRepo


def _with_tasks_table(func: Callable[..., None]):
    def wrapper(*args, **kwargs):
        with connection_context() as conn:
            create_tasks_table(conn)
            return func(*args, conn=conn, **kwargs)

    return wrapper


class TasksRepository:
    TABLE = "tasks"

    def __init__(self):
        self._seeded = False

    def _serialize(self, task: dict) -> str:
        if "id" not in task:
            task = dict(task)
            task["id"] = str(uuid.uuid4())
        return json.dumps(task, ensure_ascii=False, separators=(",", ":"))

    def _deserialize(self, payload: str) -> dict:
        return json.loads(payload)

    def _maybe_import_json(self, conn):
        if self._seeded:
            return
        count = conn.execute(f"SELECT COUNT(1) FROM {self.TABLE}").fetchone()[0]
        if count == 0:
            legacy = LegacyTasksRepo()
            tasks = legacy.load()
            for task in tasks:
                conn.execute(
                    f"INSERT OR REPLACE INTO {self.TABLE} (id, payload) VALUES (?, ?)",
                    (task.get("id") or str(uuid.uuid4()), self._serialize(task)),
                )
        self._seeded = True

    @_with_tasks_table
    def list_all(self, *, conn) -> List[dict]:
        self._maybe_import_json(conn)
        rows = conn.execute(f"SELECT payload FROM {self.TABLE}").fetchall()
        return [self._deserialize(row[0]) for row in rows]

    @_with_tasks_table
    def save_all(self, tasks: List[dict], *, conn) -> None:
        self._maybe_import_json(conn)
        conn.execute(f"DELETE FROM {self.TABLE}")
        entries = [
            (task.get("id") or str(uuid.uuid4()), self._serialize(task)) for task in tasks
        ]
        conn.executemany(
            f"INSERT INTO {self.TABLE} (id, payload) VALUES (?, ?)", entries
        )

    def reset_daily_if_needed(self, tasks: List[dict], today=None) -> bool:
        hoy = today or date_cls.today()
        changed = False
        for t in tasks:
            if t.get("diaria") and t.get("ultima_actualizacion") != str(hoy):
                t["completado"] = False
                t["ultima_actualizacion"] = str(hoy)
                changed = True
        if changed:
            self.save_all(tasks)
        return changed
