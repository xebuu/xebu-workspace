from __future__ import annotations

import json, csv, datetime, uuid
from typing import Any, Dict, List, Tuple

from app.utility.paths import (ACTIVE_TASKS_JSON, ARCHIVED_TASKS_CSV, 
                               BITACORA_CSV, FILES_JSON, TOOLBAR_JSON)


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

class BitacoraRepo:

    HEADERS = ["Fecha", "Entrada", "Hora"]
    def ensure_headers(self) -> None:
        p = BITACORA_CSV
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            with p.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(self.HEADERS)  # headers

    def append_entry(self, headers: List) -> Tuple[bool, str]:
        p = BITACORA_CSV
        try:
            self.ensure_headers
            with p.open("a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
            return True, ""
        except Exception as e:
            return False, str(e)
        
    def path(self):
        self.ensure_headers
        return BITACORA_CSV 

class ProjectsRepo:
    """Processes/projects database stored in FILES_JSON."""

    def ensure(self) -> None:
        FILES_JSON.parent.mkdir(parents=True, exist_ok=True)
        if not FILES_JSON.exists():
            FILES_JSON.write_text(
                json.dumps({"processes": [], "tasks": []}, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

    def load(self) -> Dict[str, Any]:
        self.ensure()
        try:
            data = json.loads(FILES_JSON.read_text(encoding="utf-8")) or {}
        except Exception:
            data = {}

        # === Load Processes ===
        data.setdefault("processes", [])
        changed = False
        for p in data["processes"]:
            if isinstance(p, dict) and "id" not in p:
                p["id"] = str(uuid.uuid4())
                changed = True
            if isinstance(p, dict):
                p.setdefault("name", "Sin nombre")
                p.setdefault("description", "")
                p.setdefault("scripts", [])
                p.setdefault("links", [])
                p.setdefault("copiers", [])

        # === Load Tasks ===
        data.setdefault("tasks", [])
        for t in data["tasks"]:
            if not isinstance(t, dict):
                continue
            t.setdefault("tarea", "Sin título")
            t.setdefault("completado", False)
            t.setdefault("diaria", False)
            t.setdefault("ultima_actualizacion", "")
            t.setdefault("deadline", "")
            t.setdefault("prioridad", "media")
            t.setdefault("proc_id", None)

        if changed:
            self.save(data)

        return data

    def save(self, obj: Dict[str, Any]) -> None:
        self.ensure()
        FILES_JSON.write_text(
            json.dumps(obj, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
class MainWindowToolbarRepo:
    """Toolbar items stored in TOOLBAR_JSON as {"items": [ ... ]}"""

    def ensure_db(self) -> None:
        TOOLBAR_JSON.parent.mkdir(parents=True, exist_ok=True)
        if not TOOLBAR_JSON.exists():
            TOOLBAR_JSON.write_text(
                json.dumps({"items": []}, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )

    def load(self) -> Dict[str, Any]:
        self.ensure_db()

        try:
            data = json.loads(TOOLBAR_JSON.read_text(encoding="utf-8")) or {}
        except Exception:
            data = {}

        items = data.get("items")
        if not isinstance(items, list):
            items = []
        data["items"] = items

        # backfill + normalize
        changed = False
        for it in items:
            if not isinstance(it, dict):
                changed = True
                continue
            if "id" not in it:
                it["id"] = str(uuid.uuid4())
                changed = True
            it.setdefault("title", "Acceso")
            it.setdefault("target", "")
            it.setdefault("kind", "link")  # optional: link / script / folder / etc.

        # drop non-dicts (optional but safer)
        cleaned = [it for it in items if isinstance(it, dict)]
        if len(cleaned) != len(items):
            data["items"] = cleaned
            changed = True

        if changed:
            self.save(data)

        return data

    def save(self, data: Dict[str, Any]) -> None:
        TOOLBAR_JSON.parent.mkdir(parents=True, exist_ok=True)
        TOOLBAR_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    # ---- convenience API (so UI stays thin) ----

    def list_items(self) -> List[Dict[str, Any]]:
        return self.load().get("items", [])

    def add_item(self, title: str, target: str, kind: str = "link") -> Dict[str, Any]:
        db = self.load()
        item = {"id": str(uuid.uuid4()), "title": title.strip() or "Acceso", "target": target.strip(), "kind": kind}
        db["items"].append(item)
        self.save(db)
        return item

    def delete_item(self, item_id: str) -> bool:
        db = self.load()
        before = len(db["items"])
        db["items"] = [it for it in db["items"] if it.get("id") != item_id]
        changed = len(db["items"]) != before
        if changed:
            self.save(db)
        return changed

    def update_item(self, item_id: str, **patch: Any) -> bool:
        db = self.load()
        changed = False
        for it in db["items"]:
            if it.get("id") == item_id:
                for k, v in patch.items():
                    if v is None:
                        continue
                    it[k] = v
                changed = True
                break
        if changed:
            self.save(db)
        return changed
