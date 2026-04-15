from __future__ import annotations

CATEGORY_DEFINITIONS = {
    "work": {"label": "Trabajo", "color": "#4f8cff"},
    "gym": {"label": "Gym", "color": "#2dbb74"},
    "art": {"label": "Arte", "color": "#f08a24"},
    "personal": {"label": "Personal", "color": "#d45ca6"},
}

DEFAULT_TASK_CATEGORY = "work"
DEFAULT_BITACORA_CATEGORY = "personal"


def normalize_category(value: str | None, default: str = DEFAULT_TASK_CATEGORY) -> str:
    category = (value or "").strip().lower()
    if category in CATEGORY_DEFINITIONS:
        return category
    return default


def category_label(value: str | None, default: str = DEFAULT_TASK_CATEGORY) -> str:
    category = normalize_category(value, default)
    return CATEGORY_DEFINITIONS[category]["label"]


def category_color(value: str | None, default: str = DEFAULT_TASK_CATEGORY) -> str:
    category = normalize_category(value, default)
    return CATEGORY_DEFINITIONS[category]["color"]
