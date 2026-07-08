from __future__ import annotations

import json
from datetime import date as date_cls
from typing import Callable, List

from app.core.task_helpers import normalize_task
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
        return json.dumps(normalize_task(task), ensure_ascii=False, separators=(",", ":"))

    def _deserialize(self, payload: str) -> dict:
        return json.loads(payload)

    def _save_all(self, tasks: List[dict], *, conn) -> None:
        normalized_tasks = [normalize_task(task) for task in tasks]
        conn.execute(f"DELETE FROM {self.TABLE}")
        entries = [
            (task["id"], self._serialize(task)) for task in normalized_tasks
        ]
        conn.executemany(
            f"INSERT INTO {self.TABLE} (id, payload) VALUES (?, ?)", entries
        )

    @_with_tasks_table
    def list_all(self, *, conn) -> List[dict]:
        rows = conn.execute(f"SELECT payload FROM {self.TABLE}").fetchall()
        tasks = []
        changed = False
        for row in rows:
            task = self._deserialize(row[0])
            if not task.get("id"):
                changed = True
            tasks.append(normalize_task(task))
        if changed:
            self._save_all(tasks, conn=conn)
        return tasks

    @_with_tasks_table
    def save_all(self, tasks: List[dict], *, conn) -> None:
        self._save_all(tasks, conn=conn)

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
