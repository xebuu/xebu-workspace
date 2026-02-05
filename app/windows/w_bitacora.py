# tabs/w_bitacora.py
from __future__ import annotations
import os, csv, datetime
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QMessageBox
)
from PySide6.QtGui import QDesktopServices
from app.utility.paths import BITACORA_CSV

def _ensure_csv_with_header(csv_path: Path):
    if not csv_path.exists():
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Fecha", "Entrada", "Hora"])  # encabezados


class BitacoraWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📝 Bitácora Diaria")
        self.resize(640, 420)

        self.csv_path = BITACORA_CSV
        _ensure_csv_with_header(self.csv_path)

        central = QWidget(self)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        title = QLabel("📝 Bitácora Diaria")
        title.setObjectName("Title")
        root.addWidget(title)

        self.edt = QTextEdit()
        self.edt.setPlaceholderText("Escribe aquí tu entrada…")
        root.addWidget(self.edt, 1)

        row = QHBoxLayout()
        self.btn_add = QPushButton("＋ Agregar a Bitácora")
        self.btn_add.clicked.connect(self._add_entry)
        self.btn_open = QPushButton("➡️ Abrir Bitácora (CSV)")
        self.btn_open.clicked.connect(self._open_csv)
        row.addWidget(self.btn_add)
        row.addStretch()
        row.addWidget(self.btn_open)
        root.addLayout(row)

        # atajo: Ctrl+Enter para guardar
        act_save = QAction(self)
        act_save.setShortcut(QKeySequence(Qt.CTRL | Qt.Key_Return))
        act_save.triggered.connect(self._add_entry)
        self.addAction(act_save)


    def _add_entry(self):
        text = (self.edt.toPlainText() or "").strip()
        if not text:
            return
        today = datetime.date.today().strftime("%d-%m-%Y")
        now = datetime.datetime.now().strftime("%I:%M %p")
        try:
            with self.csv_path.open("a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([today, text, now])
            self.edt.clear()
            self.statusBar().showMessage(f"Entrada agregada al CSV✅", 1500)
        except Exception as e:
            QMessageBox.critical(self, "Bitácora", f"Error al escribir CSV:\n{e}")

    def _open_csv(self):
        p = self.csv_path
        try:
            os.startfile(str(p.resolve()))
        except Exception as e:
            QMessageBox.warning(self, "Bitácora", str(e))
