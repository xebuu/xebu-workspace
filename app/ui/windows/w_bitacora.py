# tabs/w_bitacora.py
from __future__ import annotations

import datetime

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.helpers import open_resource_target
from app.utility.database import BitacoraRepo
from app.core.theme import theme_manager


class BitacoraWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📝 Bitácora Diaria")
        self.resize(640, 420)

        self.bitacora_repo = BitacoraRepo()
        self.bitacora_repo.ensure_headers()

        central = QWidget(self)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        title = QLabel("📝 Bitácora Diaria")
        title.setObjectName("Title")
        root.addWidget(title)

        self.edt = QTextEdit()
        self.edt.setObjectName("BitacoraEntry")
        self.edt.setPlaceholderText("Escribe aquí tu entrada…")
        self.edt.installEventFilter(self)
        root.addWidget(self.edt, 1)

        theme_manager.theme_changed.connect(lambda _: self._update_highlight())
        self._update_highlight()

        row = QHBoxLayout()
        self.btn_add = QPushButton("＋ Agregar a Bitácora")
        self.btn_add.clicked.connect(self._add_entry)
        self.btn_open = QPushButton("➡️ Abrir Bitácora (CSV)")
        self.btn_open.clicked.connect(self._open_csv)
        row.addWidget(self.btn_add)
        row.addStretch()
        row.addWidget(self.btn_open)
        root.addLayout(row)

    def _add_entry(self):
        text = (self.edt.toPlainText() or "").strip()
        if not text:
            return
        today = datetime.date.today().strftime("%d-%m-%Y")
        now = datetime.datetime.now().strftime("%I:%M %p")
        headers = [today, text, now]
        ok, err = self.bitacora_repo.append_entry(headers)
        if not ok:
            QMessageBox.critical(self, "Bitácora", f"Error al escribir CSV:\n{err}")
            return

        self.edt.clear()
        self.statusBar().showMessage("Entrada agregada al CSV ✅", 1500)

    def _open_csv(self):
        p = self.bitacora_repo.path()
        try:
            open_resource_target(str(p.resolve()))
        except OSError as e:
            QMessageBox.warning(self, "Bitácora", str(e))

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
