from __future__ import annotations

from datetime import datetime
from typing import Callable, List, Optional

from app.models.project_models import ProcessDef
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
    Shows archived projects and lets the user unarchive one.
    """

    def __init__(
        self,
        projects: List[ProcessDef],
        on_unarchived: Optional[Callable[[str], None]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.projects = projects
        self.on_unarchived = on_unarchived

        self.setWindowTitle("Procesos archivados")
        self.resize(720, 420)

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

        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_unarchive.clicked.connect(self._unarchive_selected)
        self.btn_close.clicked.connect(self.close)
        self.list.itemDoubleClicked.connect(lambda _: self._unarchive_selected())

        self.setAutoFillBackground(True)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setWindowFlag(Qt.Window, True)
        self.setWindowModality(Qt.NonModal)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.refresh()

    def refresh(self) -> None:
        self.list.clear()
        archived = self._get_archived_processes()
        if not archived:
            item = QListWidgetItem("No hay procesos archivados.")
            item.setFlags(Qt.NoItemFlags)
            self.list.addItem(item)
            self.btn_unarchive.setEnabled(False)
            return

        self.btn_unarchive.setEnabled(True)

        def sort_key(proc: ProcessDef):
            return self._parse_iso_dt(getattr(proc, "archived_at", None)) or datetime.min

        for proc in sorted(archived, key=sort_key, reverse=True):
            pid = getattr(proc, "id", "")
            name = getattr(proc, "name", "(Sin nombre)")
            archived_at = getattr(proc, "archived_at", None)
            display_date = self._format_archived_at(archived_at)
            text = f"{name}  —  {display_date}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, str(pid))
            self.list.addItem(item)

    def _get_archived_processes(self) -> List[ProcessDef]:
        return [proc for proc in self.projects if getattr(proc, "is_archived", False)]

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

        if callable(self.on_unarchived):
            self.on_unarchived(str(proc_id))
        else:
            self._local_unarchive(str(proc_id))
        self.refresh()

    def _local_unarchive(self, proc_id: str) -> None:
        for proc in self.projects:
            if getattr(proc, "id", "") == proc_id:
                proc.is_archived = False
                proc.archived_at = None
                break

    @staticmethod
    def _parse_iso_dt(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    @staticmethod
    def _format_archived_at(value: Optional[str]) -> str:
        dt = ArchivedProjectWindow._parse_iso_dt(value)
        if not dt:
            return "Sin fecha"
        return dt.strftime("%Y-%m-%d %H:%M")
