from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

# If you're using PySide6 instead, change these imports accordingly.
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ArchivedProjectWindow(QWidget):
    """
    Minimal archived-projects window:
      - shows a readable list of archived processes
      - lets you unarchive the selected one
      - calls on_unarchived(proc_id) so the main window can save + re-render
    """

    def __init__(
        self,
        db: Dict[str, Any],
        on_unarchived: Optional[Callable[[str], None]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.db = db
        self.on_unarchived = on_unarchived

        self.setWindowTitle("Procesos archivados")
        self.resize(720, 420)

        # --- UI ---
        root = QVBoxLayout(self)

        self.lbl = QLabel("Selecciona un proceso archivado y presiona “Desarchivar”.")
        self.lbl.setWordWrap(True)
        root.addWidget(self.lbl)

        self.list = QListWidget()
        self.list.setSelectionMode(QListWidget.SingleSelection)
        root.addWidget(self.list, stretch=1)

        btn_row = QHBoxLayout()
        root.addLayout(btn_row)

        self.btn_refresh = QPushButton("Refrescar")
        self.btn_unarchive = QPushButton("Desarchivar seleccionado")
        self.btn_close = QPushButton("Cerrar")

        btn_row.addWidget(self.btn_refresh)
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_unarchive)
        btn_row.addWidget(self.btn_close)

        # --- Signals ---
        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_unarchive.clicked.connect(self._unarchive_selected)
        self.btn_close.clicked.connect(self.close)
        self.list.itemDoubleClicked.connect(lambda _: self._unarchive_selected())

        # Initial load
        self.setAutoFillBackground(True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setWindowFlag(Qt.Window, True)  # force top-level window
        self.setWindowModality(Qt.NonModal)  # optional
        self.setAttribute(Qt.WA_DeleteOnClose, True)  # optional nice behavior
        self.refresh()

    # -------------------------
    # Public
    # -------------------------
    def refresh(self) -> None:
        """Reload the list from self.db."""
        self.list.clear()

        archived = self._get_archived_processes()
        if not archived:
            item = QListWidgetItem("No hay procesos archivados.")
            item.setFlags(Qt.NoItemFlags)  # not selectable
            self.list.addItem(item)
            self.btn_unarchive.setEnabled(False)
            return

        self.btn_unarchive.setEnabled(True)

        # Sort by archived_at desc when available
        def sort_key(p: Dict[str, Any]):
            dt = self._parse_iso_dt(p.get("archived_at"))
            return dt or datetime.min

        archived_sorted = sorted(archived, key=sort_key, reverse=True)

        for p in archived_sorted:
            pid = str(p.get("id", ""))
            name = str(p.get("name", "(Sin nombre)"))
            archived_at = p.get("archived_at")

            display_date = self._format_archived_at(archived_at)
            text = f"{name}  —  {display_date}"

            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, pid)
            self.list.addItem(item)

    # -------------------------
    # Internals
    # -------------------------
    def _get_archived_processes(self) -> List[Dict[str, Any]]:
        procs = self.db.get("processes", [])
        if not isinstance(procs, list):
            return []
        return [
            p for p in procs if isinstance(p, dict) and p.get("is_archived") is True
        ]

    def _unarchive_selected(self) -> None:
        item = self.list.currentItem()
        if not item:
            return

        proc_id = item.data(Qt.UserRole)
        if not proc_id:
            return

        if (
            QMessageBox.question(
                self,
                "Desarchivar proceso",
                "¿Seguro que quieres desarchivar este proceso?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            != QMessageBox.Yes
        ):
            return

        # Delegate actual mutation + persistence to main window (recommended)
        if callable(self.on_unarchived):
            self.on_unarchived(str(proc_id))
        else:
            # Fallback: do local mutation only (no saving).
            self._local_unarchive(str(proc_id))

        self.refresh()

    def _local_unarchive(self, proc_id: str) -> None:
        """Fallback if you didn't pass on_unarchived. Does NOT call _save_db."""
        procs = self.db.get("processes", [])
        if not isinstance(procs, list):
            return
        for p in procs:
            if isinstance(p, dict) and p.get("id") == proc_id:
                p["is_archived"] = False
                p["archived_at"] = None
                break

    @staticmethod
    def _parse_iso_dt(value: Any) -> Optional[datetime]:
        if not value or not isinstance(value, str):
            return None
        try:
            # Handles "YYYY-MM-DDTHH:MM:SS"
            return datetime.fromisoformat(value)
        except Exception:
            return None

    @staticmethod
    def _format_archived_at(value: Any) -> str:
        dt = ArchivedProjectWindow._parse_iso_dt(value)
        if not dt:
            return "Sin fecha"
        return dt.strftime("%Y-%m-%d %H:%M")
