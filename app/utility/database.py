from __future__ import annotations

import csv
from typing import List, Tuple

from app.core.paths import BITACORA_CSV


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
