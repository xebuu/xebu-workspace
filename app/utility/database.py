from __future__ import annotations

import json, csv, datetime
from typing import Any, Dict, List, Tuple

from app.utility.paths import ACTIVE_TASKS_JSON, ARCHIVED_TASKS_CSV


class TasksRepo:
    """Active tasks stored in ACTIVE_TASKS_JSON as a list[dict]."""

    def load(self) -> List[Dict[str, Any]]:
        p = ACTIVE_TASKS_JSON
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("[]", encoding="utf-8")
            return []
        try:
            data = json.loads(p.read_text(encoding="utf-8")) or []
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def save(self, tasks: List[Dict[str, Any]]) -> None:
        p = ACTIVE_TASKS_JSON
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(tasks, indent=2, ensure_ascii=False), encoding="utf-8")

    def reset_daily_if_needed(self, tasks: List[Dict[str, Any]], today: datetime.date | None = None) -> bool:
        """Resets daily tasks if last update != today. Returns True if changes were made."""
        hoy = today or datetime.date.today()
        changed = False
        for t in tasks:
            if t.get("diaria") and t.get("ultima_actualizacion") != str(hoy):
                t["completado"] = False
                t["ultima_actualizacion"] = str(hoy)
                changed = True
        if changed:
            self.save(tasks)
        return changed


class ArchivedTasksRepo:
    """Archived tasks stored in ARCHIVED_TASKS_CSV."""

    HEADER = ["Tarea", "Completado", "Diaria", "Última actualización", "Deadline", "Prioridad"]

    def append_task(self, task: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Appends a task to the archive CSV.
        Returns (ok, error_message). error_message empty if ok.
        """
        p = ARCHIVED_TASKS_CSV
        newfile = not p.exists()

        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            with p.open("a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                if newfile:
                    w.writerow(self.HEADER)
                w.writerow([
                    task.get("tarea", ""),
                    task.get("completado", False),
                    task.get("diaria", False),
                    task.get("ultima_actualizacion", ""),
                    task.get("deadline", ""),
                    task.get("prioridad", ""),
                ])
            return True, ""
        except Exception as e:
            return False, str(e)
