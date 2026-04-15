from __future__ import annotations

import json
import uuid
from datetime import date as date_cls
from typing import Callable, List

from app.core.categories import DEFAULT_TASK_CATEGORY, normalize_category
from app.database.connection import connection_context
from app.database.schema import create_tasks_table


def _with_tasks_table(func: Callable[..., None]):
    def wrapper(*args, **kwargs):
        with connection_context() as conn:
            create_tasks_table(conn)
            return func(*args, conn=conn, **kwargs)

    return wrapper


class TasksRepository:
    TABLE = "tasks"

    def _serialize(self, task: dict) -> str:
        task = dict(task)
        if "id" not in task:
            task["id"] = str(uuid.uuid4())
        task["category"] = normalize_category(
            task.get("category"), DEFAULT_TASK_CATEGORY
        )
        return json.dumps(task, ensure_ascii=False, separators=(",", ":"))

    def _deserialize(self, payload: str) -> dict:
        task = json.loads(payload)
        if "id" not in task:
            task["id"] = str(uuid.uuid4())
        task["category"] = normalize_category(
            task.get("category"), DEFAULT_TASK_CATEGORY
        )
        return task

    @_with_tasks_table
    def list_all(self, *, conn) -> List[dict]:
        rows = conn.execute(f"SELECT payload FROM {self.TABLE}").fetchall()
        return [self._deserialize(row[0]) for row in rows]

    @_with_tasks_table
    def save_all(self, tasks: List[dict], *, conn) -> None:
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
