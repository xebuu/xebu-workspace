from __future__ import annotations

import re

from PySide6.QtCore import QObject, Signal


HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
CUSTOM_PREFIX = "Custom:"

BASE_TOKENS: dict[str, dict[str, str]] = {
    "app": {
        "background": "#141616",
        "background_alt": "#191b1b",
    },
    "surface": {
        "base": "#1d2020",
        "raised": "#242828",
        "sunken": "#171a1a",
        "hover": "#2b3030",
        "selected": "#213238",
    },
    "border": {
        "subtle": "#303636",
        "normal": "#3e4747",
        "strong": "#596767",
        "focus": "#ffffff",
    },
    "text": {
        "primary": "#f2f0e8",
        "secondary": "#c9d0cd",
        "muted": "#8e9a96",
        "inverse": "#101313",
    },
    "state": {
        "success": "#6fcf97",
        "warning": "#f5c76b",
        "danger": "#f06f6f",
        "info": "#72b7f2",
    },
    "priority": {
        "high": "#f5c76b",
        "medium": "#72b7f2",
        "low": "#8e9a96",
    },
}

ACCENT_PRESETS: dict[str, str] = {
    "Pink": "#ff4fa3",
    "Yellow": "#facf4e",
    "Green": "#4D8F71",
    "Blue": "#46abf3",
    "Mint": "#91C4B9",
}


def _normalize_hex(value: str) -> str:
    color = (value or "").strip()
    if not color.startswith("#"):
        color = f"#{color}"
    if not HEX_RE.match(color):
        return ACCENT_PRESETS["Pink"]
    return color.lower()


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = _normalize_hex(value).lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _mix(color: str, target: str, amount: float) -> str:
    r1, g1, b1 = _hex_to_rgb(color)
    r2, g2, b2 = _hex_to_rgb(target)
    mixed = (
        round(r1 + (r2 - r1) * amount),
        round(g1 + (g2 - g1) * amount),
        round(b1 + (b2 - b1) * amount),
    )
    return _rgb_to_hex(mixed)


def _contrast_text(color: str) -> str:
    r, g, b = _hex_to_rgb(color)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "#101313" if luminance > 0.62 else "#ffffff"


def _build_theme(accent: str) -> dict[str, dict[str, str]]:
    accent = _normalize_hex(accent)
    theme = {section: dict(tokens) for section, tokens in BASE_TOKENS.items()}
    theme["accent"] = {
        "normal": accent,
        "hover": _mix(accent, "#ffffff", 0.18),
        "muted": _mix(accent, BASE_TOKENS["surface"]["base"], 0.68),
        "checked": _mix(accent, "#000000", 0.18),
        "text": _contrast_text(accent),
    }
    theme["calendar"] = {
        "nav_bar_bg": accent,
        "nav_bar_text": _contrast_text(accent),
        "today_border": accent,
        "selected_bg": _mix(accent, BASE_TOKENS["surface"]["base"], 0.64),
        "chip_bg": _mix(accent, BASE_TOKENS["surface"]["base"], 0.78),
    }
    return theme


THEME_REGISTRY: dict[str, dict[str, dict[str, str]]] = {
    name: _build_theme(accent) for name, accent in ACCENT_PRESETS.items()
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
        self._custom_accent = ACCENT_PRESETS["Pink"]

    @property
    def current_theme(self) -> str:
        return self._current_theme

    @property
    def current_accent(self) -> str:
        return self.get_color("accent", "normal")

    def _active_theme(self) -> dict[str, dict[str, str]]:
        if self._current_theme == "Custom":
            return _build_theme(self._custom_accent)
        return THEME_REGISTRY.get(self._current_theme, THEME_REGISTRY["Pink"])

    def set_theme(self, name: str) -> None:
        if name not in THEME_REGISTRY or name == self._current_theme:
            return
        self._current_theme = name
        self.theme_changed.emit(name)

    def set_custom_accent(self, color: str) -> None:
        normalized = _normalize_hex(color)
        if self._current_theme == "Custom" and normalized == self._custom_accent:
            return
        self._custom_accent = normalized
        self._current_theme = "Custom"
        self.theme_changed.emit("Custom")

    def load_theme(self, value: str | None) -> None:
        if not value:
            return
        if value.startswith(CUSTOM_PREFIX):
            self.set_custom_accent(value.removeprefix(CUSTOM_PREFIX))
        elif value in THEME_REGISTRY:
            self.set_theme(value)

    def serialize_current_theme(self) -> str:
        if self._current_theme == "Custom":
            return f"{CUSTOM_PREFIX}{self._custom_accent}"
        return self._current_theme

    def get_color(self, component: str, token: str, fallback: str = "#2c2c2c") -> str:
        theme = self._active_theme()
        component_data = theme.get(component, {})
        color = component_data.get(token)
        if color:
            return color
        accent = theme.get("accent", {})
        return accent.get("normal", fallback)

    def stylesheet_tokens(self) -> dict[str, str]:
        theme = self._active_theme()
        flat: dict[str, str] = {}
        for component, tokens in theme.items():
            for token, value in tokens.items():
                flat[f"{component}_{token}"] = value
        return flat


theme_manager = ThemeManager()
