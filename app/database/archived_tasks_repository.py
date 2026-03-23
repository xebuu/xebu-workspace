from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Callable, List, Optional

from app.core.paths import ARCHIVED_TASKS_CSV
from app.database.connection import connection_context
from app.database.schema import create_archived_tasks_table


def _with_archived_table(func: Callable[..., Optional[bool]]):
    def wrapper(*args, **kwargs):
        with connection_context() as conn:
            create_archived_tasks_table(conn)
            return func(*args, conn=conn, **kwargs)

    return wrapper


class ArchivedTasksRepository:
    TABLE = "archived_tasks"

    def __init__(self):
        self._seeded = False

    def _serialize(self, task: dict) -> str:
        return json.dumps(task, ensure_ascii=False, separators=(",", ":"))

    def _deserialize(self, payload: str) -> dict:
        return json.loads(payload)

    def _import_csv(self, conn):
        if self._seeded:
            return
        if not ARCHIVED_TASKS_CSV.exists():
            self._seeded = True
            return
        with ARCHIVED_TASKS_CSV.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                conn.execute(
                    f"INSERT INTO {self.TABLE} (payload) VALUES (?)",
                    (self._serialize(row),),
                )
        self._seeded = True

    @_with_archived_table
    def append_task(self, task: dict, *, conn) -> tuple[bool, str]:
        self._import_csv(conn)
        conn.execute(
            f"INSERT INTO {self.TABLE} (payload) VALUES (?)", (self._serialize(task),)
        )
        return True, ""

    @_with_archived_table
    def list_all(self, *, conn) -> List[dict]:
        self._import_csv(conn)
        rows = conn.execute(f"SELECT payload FROM {self.TABLE}").fetchall()
        return [self._deserialize(row[0]) for row in rows]
