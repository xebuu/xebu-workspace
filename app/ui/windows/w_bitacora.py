from __future__ import annotations

import datetime

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.categories import (
    CATEGORY_DEFINITIONS,
    DEFAULT_BITACORA_CATEGORY,
    category_label,
)
from app.core.theme import theme_manager
from app.database.bitacora_repository import BitacoraRepository


def _build_preview(note: str, limit: int = 84) -> str:
    compact = " ".join((note or "").split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "..."


class BitacoraViewerWindow(QMainWindow):
    def __init__(self, repository: BitacoraRepository, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bitácora")
        self.resize(860, 520)

        self.repo = repository
        self.entries: list[dict] = []

        central = QWidget(self)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        title = QLabel("Bitácora")
        title.setObjectName("Title")
        root.addWidget(title)

        subtitle = QLabel("Entradas recientes, con vista cómoda para notas largas.")
        subtitle.setStyleSheet("color: #909090;")
        root.addWidget(subtitle)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        root.addWidget(splitter, 1)

        list_panel = QWidget()
        list_layout = QVBoxLayout(list_panel)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(8)

        self.list = QListWidget()
        self.list.setObjectName("BitacoraViewerList")
        self.list.currentItemChanged.connect(self._on_item_changed)
        list_layout.addWidget(self.list, 1)
        splitter.addWidget(list_panel)

        detail_panel = QWidget()
        detail_layout = QVBoxLayout(detail_panel)
        detail_layout.setContentsMargins(16, 16, 16, 16)
        detail_layout.setSpacing(10)

        self.detail_date = QLabel("Selecciona una entrada")
        self.detail_date.setStyleSheet("font-size: 16px; font-weight: 700;")
        detail_layout.addWidget(self.detail_date)

        self.detail_note = QTextEdit()
        self.detail_note.setReadOnly(True)
        self.detail_note.setPlaceholderText("La nota completa aparecerá aquí.")
        detail_layout.addWidget(self.detail_note, 1)
        splitter.addWidget(detail_panel)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 4)

        self.refresh_entries()

    def refresh_entries(self) -> None:
        self.entries = self.repo.list_entries()
        self.list.clear()

        if not self.entries:
            placeholder = QListWidgetItem("No hay entradas en la bitácora todavía.")
            placeholder.setFlags(Qt.NoItemFlags)
            self.list.addItem(placeholder)
            self.detail_date.setText("Sin entradas")
            self.detail_note.setPlainText("")
            return

        for entry in self.entries:
            preview = _build_preview(entry.get("nota", ""))
            category = category_label(
                entry.get("category"), DEFAULT_BITACORA_CATEGORY
            )
            item = QListWidgetItem(f"{entry.get('fecha', '')} • {category}\n{preview}")
            item.setData(Qt.UserRole, entry)
            self.list.addItem(item)

        self.list.setCurrentRow(0)

    def _on_item_changed(self, current: QListWidgetItem, _previous) -> None:
        entry = current.data(Qt.UserRole) if current is not None else None
        if not isinstance(entry, dict):
            self.detail_date.setText("Sin entradas")
            self.detail_note.setPlainText("")
            return

        category = category_label(entry.get("category"), DEFAULT_BITACORA_CATEGORY)
        self.detail_date.setText(f"{entry.get('fecha', 'Sin fecha')} • {category}")
        self.detail_note.setPlainText(entry.get("nota", ""))


class BitacoraWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bitácora Diaria")
        self.resize(640, 420)

        self.bitacora_repo = BitacoraRepository()
        self._viewer_win = None

        central = QWidget(self)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        title = QLabel("Bitácora Diaria")
        title.setObjectName("Title")
        root.addWidget(title)

        self.edt = QTextEdit()
        self.edt.setObjectName("BitacoraEntry")
        self.edt.setPlaceholderText("Escribe aquí tu entrada...")
        self.edt.installEventFilter(self)
        root.addWidget(self.edt, 1)

        category_row = QHBoxLayout()
        category_row.addWidget(QLabel("Categoría:"))
        self.cmb_category = QComboBox()
        for key in CATEGORY_DEFINITIONS:
            self.cmb_category.addItem(category_label(key), key)
        self.cmb_category.setCurrentText(category_label(DEFAULT_BITACORA_CATEGORY))
        category_row.addWidget(self.cmb_category)
        category_row.addStretch()
        root.addLayout(category_row)

        theme_manager.theme_changed.connect(lambda _: self._update_highlight())
        self._update_highlight()

        row = QHBoxLayout()
        self.btn_add = QPushButton("+ Agregar a Bitácora")
        self.btn_add.clicked.connect(self._add_entry)
        self.btn_view = QPushButton("Ver entradas")
        self.btn_view.clicked.connect(self._open_viewer)
        row.addWidget(self.btn_add)
        row.addStretch()
        row.addWidget(self.btn_view)
        root.addLayout(row)

    def _add_entry(self):
        text = (self.edt.toPlainText() or "").strip()
        if not text:
            return

        today = datetime.date.today().strftime("%d-%m-%Y")
        created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        category = self.cmb_category.currentData() or DEFAULT_BITACORA_CATEGORY
        ok, err = self.bitacora_repo.append_entry(today, text, category, created_at)
        if not ok:
            QMessageBox.critical(self, "Bitácora", f"Error al guardar en SQLite:\n{err}")
            return

        self.edt.clear()
        self.cmb_category.setCurrentText(category_label(DEFAULT_BITACORA_CATEGORY))
        if self._viewer_win is not None:
            self._viewer_win.refresh_entries()
        self.statusBar().showMessage("Entrada agregada a la bitácora", 1500)

    def _open_viewer(self):
        if self._viewer_win is None:
            self._viewer_win = BitacoraViewerWindow(self.bitacora_repo, self)
            self._viewer_win.destroyed.connect(
                lambda: setattr(self, "_viewer_win", None)
            )
        self._viewer_win.refresh_entries()
        self._viewer_win.show()
        self._viewer_win.raise_()
        self._viewer_win.activateWindow()

    def eventFilter(self, obj, event):
        if obj is self.edt and event.type() in (QEvent.FocusIn, QEvent.FocusOut):
            self._update_highlight()
        return super().eventFilter(obj, event)

    def _update_highlight(self):
        if self.edt.hasFocus():
            color = theme_manager.get_color("accent", "normal")
            self.edt.setStyleSheet(f"border-bottom: 3px solid {color};")
        else:
            self.edt.setStyleSheet("")
