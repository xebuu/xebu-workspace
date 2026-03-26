# seg_processing_manager.py
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextDocument
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from app.models.project_models import ProcessDef
from app.database.project_repository import ProjectsRepository
from app.ui.widgets.search_bars import ProjectSearchBar
from app.ui.windows.w_archived_projects import ArchivedProjectWindow
from app.ui.windows.w_new_project import NewProjectWindow
from app.ui.windows.w_ProjectViewer import ProjectViewWindow


# -------------------- Main: Manager window --------------------
class ProjectManagerTab(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestión de Proyectos")
        self.resize(1000, 640)
        self.repo = ProjectsRepository()
        self.processes: list[ProcessDef] = self.repo.list_all()

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Proyectos")
        title.setObjectName("Title")
        header.addWidget(title)
        header.addItem(QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.searchbar = ProjectSearchBar()
        self.searchbar.setFixedWidth(600)
        self.searchbar.textChanged.connect(self._on_search_changed)
        header.addWidget(self.searchbar)

        self.btn_archived = QPushButton("Archivados")
        self.btn_archived.clicked.connect(self._open_archived_projects)
        header.addWidget(self.btn_archived)

        self.btn_add = QPushButton("+ Nuevo Proyecto")
        self.btn_add.clicked.connect(self._open_builder_new)
        header.addWidget(self.btn_add)

        root.addLayout(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.wrap = QWidget()
        self.grid = QGridLayout(self.wrap)
        self.grid.setContentsMargins(6, 6, 6, 6)
        self.grid.setHorizontalSpacing(10)
        self.grid.setVerticalSpacing(10)
        self.scroll.setWidget(self.wrap)
        root.addWidget(self.scroll, 1)

        self._render()

    def _render(self, data=None, query: str = ""):
        # limpiar
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        processes = data if data is not None else self._visible_processes()


        if not processes:
            if query == "":
                lbl = QLabel("No hay proyectos aún. Usa “Agregar Proyecto”.")
            else:
                lbl = QLabel(f"No hay resultados para {query}.")

            self.grid.addWidget(lbl, 0, 0, alignment=Qt.AlignTop)
            return

        processes.sort(
            key=lambda p: (
                not getattr(p, "is_pinned", False),
                getattr(p, "name", "").lower(),
            )
        )
        cols = 1  # vertical
        for idx, proc in enumerate(processes):
            r, c = divmod(idx, cols)
            self.grid.addWidget(self._make_card(proc), r, c, alignment=Qt.AlignTop)

        self.grid.setRowStretch(self.grid.rowCount(), 1)

    def _visible_processes(self) -> list[ProcessDef]:
        return [
            proc for proc in self.processes if not getattr(proc, "is_archived", False)
        ]

    def _find_process(self, proc_id: str) -> ProcessDef | None:
        for proc in self.processes:
            if proc.id == proc_id:
                return proc
        return None

    def _persist_process(self, proc: ProcessDef) -> None:
        for idx, existing in enumerate(self.processes):
            if existing.id == proc.id:
                self.processes[idx] = proc
                break
        else:
            self.processes.append(proc)
        self.repo.save(proc)

    def _remove_process(self, proc_id: str) -> None:
        self.processes = [proc for proc in self.processes if proc.id != proc_id]

    def _make_card(self, proc: ProcessDef) -> QWidget:

        card = QFrame()
        card.setObjectName("Card")
        v = QVBoxLayout(card)
        v.setContentsMargins(12, 10, 12, 10)
        v.setSpacing(6)

        is_pinned = getattr(proc, "is_pinned", False)
        headerW = QWidget(card)
        header = QHBoxLayout(headerW)
        header.setContentsMargins(0, 0, 0, 0)
        title = QLabel(proc.name, headerW)
        title.setObjectName("CardTitle")
        pin_icon = QLabel("📌", headerW)
        pin_icon.setObjectName("PinIcon")
        pin_icon.setVisible(is_pinned)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(pin_icon)

        # convert possible HTML description to plain text for card preview
        doc = QTextDocument()
        doc.setHtml(proc.description)
        plain_summary = doc.toPlainText()
        meta = QLabel(plain_summary[:120] + ("…" if len(plain_summary) > 120 else ""))
        meta.setObjectName("CardMeta")
        meta.setWordWrap(True)

        btns = QHBoxLayout()
        btn_edit = QPushButton("Editar")
        btn_edit.setObjectName("Edit")
        btn_edit.clicked.connect(lambda: self._open_builder_edit(proc))
        btn_del = QPushButton("Borrar")
        btn_del.setObjectName("Delete")
        btn_del.clicked.connect(lambda: self._delete_process(proc.id))

        def _on_card_click(event, proc=proc, parent=self):
            if event.button() == Qt.LeftButton:
                parent._open_runner(proc)

            elif event.button() == Qt.RightButton:
                menu = QMenu(card)
                act_edit = menu.addAction("Editar")

                if getattr(proc, "is_pinned", False):
                    act_pin = menu.addAction("Desfijar")
                else:
                    act_pin = menu.addAction("Fijar")

                act_archive_proc = menu.addAction("Archivar")

                menu.addSeparator()

                act_del = menu.addAction("Borrar")

                global_pos = card.mapToGlobal(event.position().toPoint())
                action = menu.exec(global_pos)

                if action == act_edit:
                    parent._open_builder_edit(proc)
                elif action == act_del:
                    parent._delete_process(proc.id)
                elif action == act_archive_proc:
                    parent._archive_process(proc.id)
                elif action == act_pin:
                    parent._pin_project(proc.id)

        card.mousePressEvent = _on_card_click
        card.setCursor(Qt.PointingHandCursor)

        btns.addWidget(btn_edit)
        btns.addWidget(btn_del)
        btns.addStretch()

        v.addWidget(headerW)
        v.addWidget(meta)
        v.addLayout(btns)

        return card

    # ---- open windows ----
    def _open_runner(self, proc: ProcessDef):
        w = ProjectViewWindow(proc, parent=self)
        # ensure modifications are written back to the database
        w.on_save_proc = self._runner_saved
        w.show()

    def _runner_saved(self, proc: ProcessDef):
        self._persist_process(proc)

    def _open_builder_new(self):
        dlg = NewProjectWindow(parent=self)
        if dlg.exec() == QDialog.Accepted:
            new_proc = dlg.result_process()
            self._persist_process(new_proc)
            self._render()

    def _open_builder_edit(self, proc: ProcessDef):
        dlg = NewProjectWindow(existing=proc, parent=self)
        if dlg.exec() == QDialog.Accepted:
            updated = dlg.result_process()
            self._persist_process(updated)
            self._render()

    def _delete_process(self, proc_id: str):
        if (
            QMessageBox.question(
                self,
                "Borrar proceso",
                "¿Seguro que quieres borrar este proceso?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            != QMessageBox.Yes
        ):
            return
        if self.repo.delete(proc_id):
            self._remove_process(proc_id)
        self._render()

    def _archive_process(self, proc_id: str):
        if (
            QMessageBox.question(
                self,
                "Archivar proceso",
                "¿Seguro que quieres archivar este proceso?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            != QMessageBox.Yes
        ):
            return

        now_iso = datetime.now().isoformat(timespec="seconds")
        proc = self._find_process(proc_id)
        if proc is None:
            return
        proc.is_archived = True
        proc.archived_at = now_iso
        self._persist_process(proc)
        self._render()

    def _open_archived_projects(self):
        self._archived_win = ArchivedProjectWindow(
            self.processes, on_unarchived=self._on_unarchived, parent=self
        )
        self._archived_win.show()

    def _on_unarchived(self, proc_id: str):
        proc = self._find_process(proc_id)
        if not proc:
            return
        proc.is_archived = False
        proc.archived_at = None
        self._persist_process(proc)
        self._render()

    def _on_search_changed(self, text: str):
        text = (text or "").strip().lower()

        if not text:
            return self._render()

        def matches(proc: ProcessDef) -> bool:
            name = (getattr(proc, "name", "") or "").lower()
            desc = (getattr(proc, "description", "") or "").lower()
            return text in name or text in desc

        filtered = [proc for proc in self._visible_processes() if matches(proc)]
        self._render(filtered, query=text)

    def _pin_project(self, proc_id: str):
        proc = self._find_process(proc_id)
        if not proc:
            return
        proc.is_pinned = not proc.is_pinned
        self._persist_process(proc)
        self._render()
