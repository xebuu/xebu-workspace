from pathlib import Path
from typing import Optional

from PySide6.QtCore import QStandardPaths

# Directory for AppData

APP_NAME = "XebuWorkspace"
ORG_NAME = "Xebu"


def _resolve_app_data_dir() -> Path:
    """Return the AppData folder where user data should live."""
    loc = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
    base = Path(loc) if loc else (Path.home() / f".{APP_NAME.lower()}")
    return base / ORG_NAME / APP_NAME


def _fallback_app_data_dir() -> Path:
    """Return a safe fallback AppData path under the repository."""
    root = Path(__file__).resolve().parents[1] / ".appdata"
    return root / ORG_NAME / APP_NAME


_app_data_dir_cache: Optional[Path] = None


def _set_app_data_dir(path: Path) -> Path:
    global _app_data_dir_cache
    _app_data_dir_cache = path
    return path


def _ensure_directory_writable(directory: Path) -> None:
    """Attempt to write a temporary file inside the directory."""
    test_file = directory / ".write_test"
    try:
        test_file.write_text("", encoding="utf-8")
    finally:
        try:
            test_file.unlink(missing_ok=True)
        except OSError:
            pass


def get_app_data_dir() -> Path:
    """Return the AppData folder path (does not create it)."""
    global _app_data_dir_cache
    if _app_data_dir_cache is None:
        _app_data_dir_cache = _resolve_app_data_dir()
    return _app_data_dir_cache


def ensure_app_data_dir() -> Path:
    """Ensure the AppData folder exists and return it."""
    target = get_app_data_dir()
    try:
        target.mkdir(parents=True, exist_ok=True)
        _ensure_directory_writable(target)
        return target
    except OSError:
        fallback = _fallback_app_data_dir()
        fallback.mkdir(parents=True, exist_ok=True)
        _ensure_directory_writable(fallback)
        return _set_app_data_dir(fallback)


def get_db_path(name: str = "xebu_workspace.db") -> Path:
    """Return a path reserved for the future SQLite database file."""
    return ensure_app_data_dir() / name


def get_config_path(name: str = "config.json") -> Path:
    """Return a configuration file path inside AppData."""
    return ensure_app_data_dir() / name


def get_log_path(name: str = "app.log") -> Path:
    """Return a log file path inside AppData."""
    return ensure_app_data_dir() / name


def get_backup_dir() -> Path:
    """Return a dedicated backups directory inside AppData."""
    backup_dir = ensure_app_data_dir() / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


# === Cached helpers ===

APP_DATA_DIR = ensure_app_data_dir()


FILES_JSON = APP_DATA_DIR / "files.json"
ACTIVE_TASKS_JSON = APP_DATA_DIR / "tasks.json"
ARCHIVED_TASKS_CSV = APP_DATA_DIR / "tasks_archive.csv"

# === Main Window ===

TOOLBAR_JSON = APP_DATA_DIR / "toolbar.json"
BITACORA_CSV = APP_DATA_DIR / "bitacora.csv"

# XebuWorkspace Paths
APP_DIR = Path(__file__).resolve().parents[1]
ASSETS_DIR = APP_DIR / "assets"
assets_path = ASSETS_DIR / "style.qss"

__all__ = [
    "APP_NAME",
    "ORG_NAME",
    "get_app_data_dir",
    "ensure_app_data_dir",
    "get_db_path",
    "get_config_path",
    "get_log_path",
    "get_backup_dir",
    "APP_DATA_DIR",
    "FILES_JSON",
    "ACTIVE_TASKS_JSON",
    "ARCHIVED_TASKS_CSV",
    "TOOLBAR_JSON",
    "BITACORA_CSV",
    "APP_DIR",
    "ASSETS_DIR",
    "assets_path",
]
