# New project window
from __future__ import annotations

import uuid
from typing import Optional

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)

from app.models.project_models import ProcessDef


class NewProjectWindow(QDialog):
    def __init__(self, existing: Optional[ProcessDef] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nuevo proyecto")
        self.setModal(True)
        self.resize(720, 320)

        self.proc = existing or ProcessDef(
            id=str(uuid.uuid4()),
            name="",
            description="",
            scripts=[],
            links=[],
            copiers=[],
            is_pinned=False,
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 8, 16, 8)
        root.setSpacing(8)

        title = QLabel("Nuevo proyecto")
        title.setObjectName("RunTitle")
        title.setContentsMargins(0, 0, 0, 4)
        root.addWidget(title)

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(QLabel("Nombre:"))
        self.edt_name = QLineEdit(self.proc.name)
        self.edt_name.setPlaceholderText("Nombre del proyecto")
        row.addWidget(self.edt_name)
        root.addLayout(row)

        self.edt_desc = QTextEdit()
        self.edt_desc.setPlaceholderText("Descripción del proyecto")
        self.edt_desc.setFixedHeight(200)
        description = self.proc.description or ""
        if isinstance(description, str):
            try:
                self.edt_desc.setHtml(description)
            except (TypeError, ValueError):
                self.edt_desc.setPlainText(description)
        else:
            self.edt_desc.setPlainText(str(description))
        root.addWidget(self.edt_desc)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Save).setText("Guardar")
        btns.button(QDialogButtonBox.Cancel).setText("Cancelar")
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _on_accept(self):
        name = self.edt_name.text().strip()
        if not name:
            return
        self.proc.name = name
        self.proc.description = self.edt_desc.toHtml().strip()
        self.accept()

    def result_process(self) -> ProcessDef:
        return self.proc
