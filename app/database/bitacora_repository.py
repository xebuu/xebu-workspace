from __future__ import annotations

import csv
from datetime import datetime
from sqlite3 import DatabaseError
from typing import Callable, List, Optional, Tuple

from app.core.paths import BITACORA_CSV
from app.database.connection import connection_context
from app.database.schema import create_bitacora_entries_table


def _with_table(func: Callable[..., object]):
    def wrapper(*args, **kwargs):
        with connection_context() as conn:
            create_bitacora_entries_table(conn)
            return func(*args, conn=conn, **kwargs)

    return wrapper


class BitacoraRepository:
    TABLE = "bitacora_entries"

    def __init__(self):
        self._seeded = False

    def _row_to_entry(self, row) -> dict:
        return {
            "id": row["id"],
            "fecha": row["fecha"],
            "nota": row["nota"],
            "created_at": row["created_at"],
        }

    def _table_has_entries(self, conn) -> bool:
        row = conn.execute(
            f"SELECT 1 FROM {self.TABLE} ORDER BY id LIMIT 1"
        ).fetchone()
        return row is not None

    def _parse_legacy_created_at(
        self, fecha: str, hora: str | None = None
    ) -> Optional[str]:
        raw_date = (fecha or "").strip()
        raw_time = (hora or "").strip()
        if not raw_date:
            return None

        joined = f"{raw_date} {raw_time}".strip()
        for fmt in ("%d-%m-%Y %I:%M %p", "%d-%m-%Y %H:%M", "%d-%m-%Y"):
            try:
                if "%I" in fmt or "%H" in fmt:
                    dt = datetime.strptime(joined, fmt)
                else:
                    dt = datetime.strptime(raw_date, fmt)
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
        return None

    def _seed_from_legacy_csv(self, conn) -> None:
        if self._seeded or self._table_has_entries(conn) or not BITACORA_CSV.exists():
            self._seeded = True
            return

        with BITACORA_CSV.open("r", newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            rows_to_insert = []
            for row in reader:
                fecha = str(row.get("Fecha") or "").strip()
                nota = str(row.get("Entrada") or "").strip()
                hora = str(row.get("Hora") or "").strip()
                if not fecha or not nota:
                    continue
                created_at = self._parse_legacy_created_at(fecha, hora)
                rows_to_insert.append((fecha, nota, created_at))

        if rows_to_insert:
            conn.executemany(
                f"""INSERT INTO {self.TABLE} (fecha, nota, created_at)
                VALUES (?, ?, COALESCE(?, datetime('now')))""",
                rows_to_insert,
            )

        self._seeded = True

    @_with_table
    def list_entries(self, *, conn) -> List[dict]:
        self._seed_from_legacy_csv(conn)
        rows = conn.execute(
            f"""SELECT id, fecha, nota, created_at
            FROM {self.TABLE}
            ORDER BY datetime(created_at) DESC, id DESC"""
        ).fetchall()
        return [self._row_to_entry(row) for row in rows]

    @_with_table
    def append_entry(
        self, fecha: str, nota: str, created_at: Optional[str] = None, *, conn
    ) -> Tuple[bool, str]:
        self._seed_from_legacy_csv(conn)
        try:
            conn.execute(
                f"""INSERT INTO {self.TABLE} (fecha, nota, created_at)
                VALUES (?, ?, COALESCE(?, datetime('now')))""",
                ((fecha or "").strip(), (nota or "").strip(), created_at),
            )
            return True, ""
        except DatabaseError as exc:
            return False, str(exc)
