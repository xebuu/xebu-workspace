from __future__ import annotations

import re
import uuid
from datetime import date, timedelta
from typing import Iterable, Optional


DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PRIORITY_ORDER = {"alta": 0, "media": 1, "baja": 2}
PRIORITY_TOKENS = set(PRIORITY_ORDER)
DAILY_TOKENS = {"diaria", "diario", "daily"}
TODAY_TOKENS = {"hoy", "today"}
TOMORROW_TOKENS = {"manana", "ma\u00f1ana", "tomorrow"}


def today_iso(today: Optional[date] = None) -> str:
    return str(today or date.today())


def normalize_priority(value: object) -> str:
    priority = str(value or "media").strip().lower()
    return priority if priority in PRIORITY_ORDER else "media"


def parse_deadline(value: object) -> Optional[date]:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def normalize_task(task: dict, today: Optional[date] = None) -> dict:
    if not task.get("id"):
        task["id"] = str(uuid.uuid4())
    task["tarea"] = str(task.get("tarea") or "").strip()
    task["completado"] = bool(task.get("completado", False))
    task["diaria"] = bool(task.get("diaria", False))
    task["ultima_actualizacion"] = str(
        task.get("ultima_actualizacion") or today_iso(today)
    )
    task["deadline"] = str(task.get("deadline") or "").strip()
    task["prioridad"] = normalize_priority(task.get("prioridad"))
    return task


def normalize_tasks(tasks: Iterable[dict], today: Optional[date] = None) -> list[dict]:
    return [normalize_task(task, today=today) for task in tasks]


def create_task(
    text: str,
    *,
    deadline: str = "",
    prioridad: str = "media",
    diaria: bool = False,
    today: Optional[date] = None,
) -> dict:
    return normalize_task(
        {
            "id": str(uuid.uuid4()),
            "tarea": text.strip(),
            "completado": False,
            "diaria": diaria,
            "ultima_actualizacion": today_iso(today),
            "deadline": deadline.strip(),
            "prioridad": prioridad,
        },
        today=today,
    )


def parse_quick_task(
    raw_text: str,
    *,
    default_deadline: Optional[str] = None,
    today: Optional[date] = None,
) -> Optional[dict]:
    raw_text = (raw_text or "").strip()
    if not raw_text:
        return None

    base_date = today or date.today()
    deadline = default_deadline
    priority = "media"
    daily = False
    title_parts: list[str] = []

    for token in raw_text.split():
        clean = token.strip(".,;:!()[]{}").lower()
        if clean in PRIORITY_TOKENS:
            priority = clean
            continue
        if clean in DAILY_TOKENS:
            daily = True
            continue
        if clean in TODAY_TOKENS:
            deadline = str(base_date)
            continue
        if clean in TOMORROW_TOKENS:
            deadline = str(base_date + timedelta(days=1))
            continue
        if DATE_RE.match(clean) and parse_deadline(clean):
            deadline = clean
            continue
        title_parts.append(token)

    title = " ".join(title_parts).strip()
    if not title:
        return None
    return create_task(
        title,
        deadline=deadline or "",
        prioridad=priority,
        diaria=daily,
        today=base_date,
    )


def is_pending(task: dict) -> bool:
    return not task.get("completado", False)


def is_overdue(task: dict, today: Optional[date] = None) -> bool:
    deadline = parse_deadline(task.get("deadline"))
    return (
        is_pending(task)
        and deadline is not None
        and deadline < (today or date.today())
    )


def is_due_today(task: dict, today: Optional[date] = None) -> bool:
    deadline = parse_deadline(task.get("deadline"))
    return is_pending(task) and deadline == (today or date.today())


def is_upcoming(task: dict, today: Optional[date] = None, days: int = 7) -> bool:
    base = today or date.today()
    deadline = parse_deadline(task.get("deadline"))
    return (
        is_pending(task)
        and deadline is not None
        and base < deadline <= base + timedelta(days=days)
    )


def is_high_priority_pending(task: dict) -> bool:
    return is_pending(task) and normalize_priority(task.get("prioridad")) == "alta"


def is_inbox(task: dict) -> bool:
    return is_pending(task) and not str(task.get("deadline") or "").strip()


def task_sort_key(task: dict):
    deadline = parse_deadline(task.get("deadline"))
    return (
        PRIORITY_ORDER.get(normalize_priority(task.get("prioridad")), 1),
        deadline or date.max,
        str(task.get("tarea") or "").lower(),
    )


def sorted_tasks(tasks: Iterable[dict]) -> list[dict]:
    return sorted(tasks, key=task_sort_key)


def task_id(task: dict | str) -> str:
    return task if isinstance(task, str) else str(task.get("id") or "")


def update_task_by_id(tasks: list[dict], selected: dict | str, **changes) -> bool:
    selected_id = task_id(selected)
    for task in tasks:
        if task.get("id") == selected_id:
            task.update(changes)
            normalize_task(task)
            return True
    return False


def delete_task_by_id(tasks: list[dict], selected: dict | str) -> bool:
    selected_id = task_id(selected)
    original_len = len(tasks)
    tasks[:] = [task for task in tasks if task.get("id") != selected_id]
    return len(tasks) != original_len


def dashboard_sections(
    tasks: Iterable[dict],
    today: Optional[date] = None,
) -> dict[str, list[dict]]:
    base = today or date.today()
    normalized = normalize_tasks(list(tasks), today=base)
    return {
        "overdue": sorted_tasks(task for task in normalized if is_overdue(task, base)),
        "today": sorted_tasks(task for task in normalized if is_due_today(task, base)),
        "high_priority": sorted_tasks(
            task for task in normalized if is_high_priority_pending(task)
        ),
        "upcoming": sorted_tasks(task for task in normalized if is_upcoming(task, base)),
        "inbox": sorted_tasks(task for task in normalized if is_inbox(task)),
    }


def attention_tasks(tasks: Iterable[dict], today: Optional[date] = None) -> list[dict]:
    sections = dashboard_sections(tasks, today=today)
    seen: set[str] = set()
    result: list[dict] = []
    for key in ("overdue", "today", "high_priority"):
        for task in sections[key]:
            task_key = task.get("id")
            if task_key and task_key not in seen:
                seen.add(task_key)
                result.append(task)
    return result


def tasks_for_deadline(tasks: Iterable[dict], deadline: str) -> list[dict]:
    return sorted_tasks(
        task
        for task in normalize_tasks(list(tasks))
        if str(task.get("deadline") or "").strip() == deadline
    )
