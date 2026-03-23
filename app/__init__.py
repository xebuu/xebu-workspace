from __future__ import annotations

from app.core.theme import THEME_REGISTRY, theme_manager
from app.database.bootstrap import initialize_database
from app.database.settings_repository import SettingsRepository


def _apply_saved_theme() -> None:
    repo = SettingsRepository()
    theme_name = repo.get("theme")
    if theme_name and theme_name in THEME_REGISTRY:
        theme_manager.set_theme(theme_name)


def initialize_application() -> int:
    """Explicitly initialize application resources such as the SQLite store."""
    version = initialize_database()
    _apply_saved_theme()
    return version


__all__ = ["initialize_application"]
