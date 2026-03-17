from pathlib import Path

from PySide6.QtCore import QStandardPaths

# Directory for AppData

APP_NAME = "XebuWorkspace"
ORG_NAME = "Xebu"


def appdata_dir() -> Path:
    loc = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
    base = Path(loc) if loc else (Path.home() / f".{APP_NAME.lower()}")
    p = base / ORG_NAME / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    return p


# === Tasks ===

FILES_JSON = appdata_dir() / "files.json"
ACTIVE_TASKS_JSON = appdata_dir() / "tasks.json"
ARCHIVED_TASKS_CSV = appdata_dir() / "tasks_archive.csv"

# === Main Window ===

TOOLBAR_JSON = appdata_dir() / "toolbar.json"
BITACORA_CSV = appdata_dir() / "bitacora.csv"

# XebuWorkspace V2 Paths
APP_DIR = Path(__file__).resolve().parents[1]
ASSETS_DIR = APP_DIR / "assets"
assets_path = ASSETS_DIR / "style.qss"

__all__ = [
    "APP_NAME",
    "ORG_NAME",
    "appdata_dir",
    "FILES_JSON",
    "ACTIVE_TASKS_JSON",
    "ARCHIVED_TASKS_CSV",
    "TOOLBAR_JSON",
    "BITACORA_CSV",
    "APP_DIR",
    "ASSETS_DIR",
    "assets_path",
]
