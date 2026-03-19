from __future__ import annotations

from PySide6.QtCore import QObject, Signal

THEME_REGISTRY: dict[str, dict[str, dict[str, str]]] = {
    "Pink": {
        "accent": {
            "normal": "#ff4fa3",
            "hover": "#ff77bd",
            "checked": "#d93d86",
            "text": "#ffffff",
        },
        "calendar": {
            "nav_bar_bg": "#ff4fa3",
            "nav_bar_text": "#ffffff",
        },
    },
    "Yellow": {
        "accent": {
            "normal": "#facf4e",
            "hover": "#ffe08a",
            "checked": "#e0b83c",
            "text": "#111111",
        },
        "calendar": {
            "nav_bar_bg": "#facf4e",
            "nav_bar_text": "#111111",
        },
    },
    "Green": {
        "accent": {
            "normal": "#4D8F71",
            "hover": "#6fb091",
            "checked": "#3d725a",
            "text": "#ffffff",
        },
        "calendar": {
            "nav_bar_bg": "#4D8F71",
            "nav_bar_text": "#ffffff",
        },
    },
    "Blue": {
        "accent": {
            "normal": "#46abf3",
            "hover": "#77c2ff",
            "checked": "#2d8fd6",
            "text": "#ffffff",
        },
        "calendar": {
            "nav_bar_bg": "#46abf3",
            "nav_bar_text": "#ffffff",
        },
    },
    "Mint": {
        "accent": {
            "normal": "#91C4B9",
            "hover": "#b2ddd4",
            "checked": "#6ea89b",
            "text": "#111111",
        },
        "calendar": {
            "nav_bar_bg": "#91C4B9",
            "nav_bar_text": "#111111",
        },
    },
}


class ThemeManager(QObject):
    theme_changed = Signal(str)

    def __init__(self, default_theme: str = "Pink"):
        super().__init__()
        self._current_theme = (
            default_theme
            if default_theme in THEME_REGISTRY
            else next(iter(THEME_REGISTRY))
        )

    @property
    def current_theme(self) -> str:
        return self._current_theme

    def set_theme(self, name: str) -> None:
        if name not in THEME_REGISTRY or name == self._current_theme:
            return
        self._current_theme = name
        self.theme_changed.emit(name)

    def get_color(self, component: str, token: str, fallback: str = "#2c2c2c") -> str:
        theme = THEME_REGISTRY.get(self._current_theme, {})
        component_data = theme.get(component, {})
        color = component_data.get(token)
        if color:
            return color
        accent = theme.get("accent", {})
        return accent.get("normal", fallback)


# Module-level singleton to keep theme state application-wide
theme_manager = ThemeManager()
