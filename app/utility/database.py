from __future__ import annotations

import csv
import json
import uuid
from typing import Any, Dict, List, Tuple

from app.core.paths import BITACORA_CSV, TOOLBAR_JSON


class BitacoraRepo:

    HEADERS = ["Fecha", "Entrada", "Hora"]

    def ensure_headers(self) -> None:
        p = BITACORA_CSV
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            with p.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(self.HEADERS)

    def append_entry(self, headers: List) -> Tuple[bool, str]:
        p = BITACORA_CSV
        try:
            self.ensure_headers()
            with p.open("a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
            return True, ""
        except OSError as e:
            return False, str(e)

    def path(self):
        self.ensure_headers()
        return BITACORA_CSV


class MainWindowToolbarRepo:
    """Toolbar items stored in TOOLBAR_JSON as {"items": [ ... ]}"""

    def ensure_db(self) -> None:
        TOOLBAR_JSON.parent.mkdir(parents=True, exist_ok=True)
        if not TOOLBAR_JSON.exists():
            TOOLBAR_JSON.write_text(
                json.dumps({"items": []}, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

    def load(self) -> Dict[str, Any]:
        self.ensure_db()

        try:
            data = json.loads(TOOLBAR_JSON.read_text(encoding="utf-8")) or {}
        except json.JSONDecodeError:
            data = {}

        items = data.get("items")
        if not isinstance(items, list):
            items = []
        data["items"] = items

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
            it.setdefault("kind", "link")

        cleaned = [it for it in items if isinstance(it, dict)]
        if len(cleaned) != len(items):
            data["items"] = cleaned
            changed = True

        if changed:
            self.save(data)

        return data

    def save(self, data: Dict[str, Any]) -> None:
        TOOLBAR_JSON.parent.mkdir(parents=True, exist_ok=True)
        TOOLBAR_JSON.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def list_items(self) -> List[Dict[str, Any]]:
        return self.load().get("items", [])

    def add_item(self, title: str, target: str, kind: str = "link") -> Dict[str, Any]:
        db = self.load()
        item = {
            "id": str(uuid.uuid4()),
            "title": title.strip() or "Acceso",
            "target": target.strip(),
            "kind": kind,
        }
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
