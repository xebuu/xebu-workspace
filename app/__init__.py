from __future__ import annotations

from app.database.bootstrap import initialize_database


def initialize_application() -> int:
    """Explicitly initialize application resources such as the SQLite store."""
    return initialize_database()


__all__ = ["initialize_application"]
