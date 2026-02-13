# seg_processing_manager.py
from __future__ import annotations
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGridLayout, QMessageBox,
    QSizePolicy, QSpacerItem, QDialog, QMenu
)
from app.windows.w_archived_projects import ArchivedProjectWindow
from app.windows.w_ProjectViewer import ProjectViewWindow
from app.windows.w_project_editor import ProjectEditorWindow
from app.utility.database import ProjectsRepo
from app.models.project_models import ProcessDef

from app.widgets.search_bars import ProjectSearchBar

# -------------------- Main: Manager window --------------------
class ProjectManagerTab(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestión de Proyectos")
        self.resize(1000, 640)
        self.projects_repo = ProjectsRepo()
        self.db = self.projects_repo.load()
        #self.db = _load_db()

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Proyectos"); 
        title.setObjectName("Title")
        header.addWidget(title)
        header.addItem(QSpacerItem(10,10,QSizePolicy.Expanding,QSizePolicy.Minimum))

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
        self.grid.setContentsMargins(6,6,6,6)
        self.grid.setHorizontalSpacing(10)
        self.grid.setVerticalSpacing(10)
        self.scroll.setWidget(self.wrap)
        root.addWidget(self.scroll, 1)

        self._render()


    def _render(self, data=None, query:str = ""):
        # limpiar
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

        # Only render non-archived Projects
        raw_projs = self.db.get("processes", [])
        active_projs = [
            p for p in raw_projs
            if isinstance(p, dict) and p.get("is_archived") is not True
                        ]

        if data is None:
            processes = [ProcessDef.from_dict(p) for p in active_projs]
        else:   
            processes = [ProcessDef.from_dict(p) for p in data]

        if not processes:
            if query == "":
                lbl = QLabel("No hay proyectos aún. Usa “Agregar Proyecto”.")
            else:
                lbl = QLabel(f"No hay resultados para {query}.")
                
            self.grid.addWidget(lbl, 0,0, alignment=Qt.AlignTop)
            return

        processes.sort(key=lambda p: (not getattr(p,"is_pinned", False), getattr(p,"name","").lower()))
        cols = 1  # vertical
        for idx, proc in enumerate(processes):
            r, c = divmod(idx, cols)
            self.grid.addWidget(self._make_card(proc), r, c, alignment=Qt.AlignTop)


        self.grid.setRowStretch(self.grid.rowCount(), 1)

    def _make_card(self, proc: ProcessDef) -> QWidget:

        card = QFrame(); card.setObjectName("Card")
        v = QVBoxLayout(card); v.setContentsMargins(12,10,12,10); v.setSpacing(6)

        is_pinned = getattr(proc, "is_pinned", False)
        headerW = QWidget(card)
        header = QHBoxLayout(headerW)
        header.setContentsMargins(0, 0, 0, 0)
        title = QLabel(proc.name,headerW); title.setObjectName("CardTitle")
        pin_icon = QLabel("📌",headerW)
        pin_icon.setObjectName("PinIcon")
        pin_icon.setVisible(is_pinned)
        header.addWidget(title); header.addStretch();header.addWidget(pin_icon)

        meta = QLabel(proc.description[:120] + ("…" if len(proc.description)>120 else ""))
        meta.setObjectName("CardMeta")
        meta.setWordWrap(True)

        btns = QHBoxLayout() 
        btn_edit = QPushButton("Editar"); btn_edit.setObjectName("Edit") 
        btn_edit.clicked.connect(lambda: self._open_builder_edit(proc)) 
        btn_del = QPushButton("Borrar"); btn_del.setObjectName("Delete")
        btn_del.clicked.connect(lambda: self._delete_process(proc.id))

        def _on_card_click(event,proc=proc,parent=self):
            if event.button() == Qt.LeftButton:
                parent._open_runner(proc)

            elif event.button() == Qt.RightButton:
                menu = QMenu(card)
                act_edit = menu.addAction("Editar")

                if getattr(proc,"is_pinned",False):
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
        w.show()

    def _open_builder_new(self):
        dlg = ProjectEditorWindow(parent=self)
        if dlg.exec() == QDialog.Accepted:
            new_proc = dlg.result_process()
            self.db["processes"].append(new_proc.to_dict())
            self.projects_repo.save(self.db)
            self._render()

    def _open_builder_edit(self, proc: ProcessDef):
        dlg = ProjectEditorWindow(existing=proc, parent=self)
        if dlg.exec() == QDialog.Accepted:
            updated = dlg.result_process()
            for i, p in enumerate(self.db["processes"]):
                if p["id"] == updated.id:
                    self.db["processes"][i] = updated.to_dict()
                    break
            self.projects_repo.save(self.db)
            self._render()
    
    def _delete_process(self, proc_id: str):
        if QMessageBox.question(
            self, "Borrar proceso",
            "¿Seguro que quieres borrar este proceso?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        ) != QMessageBox.Yes:
            return
        procs = self.db.get("processes", [])
        procs = [p for p in procs if p.get("id") != proc_id]
        self.db["processes"] = procs
        self.projects_repo.save(self.db)
        self._render()

    def _archive_process(self, proc_id: str):
        if QMessageBox.question(
            self, "Archivar proceso",
            "¿Seguro que quieres archivar este proceso?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        ) != QMessageBox.Yes:
            return

        procs = self.db.get("processes", [])
        now_iso = datetime.now().isoformat(timespec="seconds")

        updated = False
        for p in procs:
            if p.get("id") == proc_id:
                p["is_archived"] = True
                p["archived_at"] = now_iso
                updated = True
                break

        self.db["processes"] = procs
        self.projects_repo.save(self.db)
        self._render()
    
    def _open_archived_projects(self):    
        def on_unarchived(proc_id: str):
            # mutate + persist using your existing patterns
            procs = self.db.get("processes", [])
            for p in procs:
                if p.get("id") == proc_id:
                    p["is_archived"] = False
                    p["archived_at"] = None
                    break
            self.db["processes"] = procs
            self.projects_repo.save(self.db)
            self._render()

        self._archived_win = ArchivedProjectWindow(self.db, on_unarchived=on_unarchived, parent=self)
        self._archived_win.show()

    def _on_search_changed(self, text: str):
        text = (text or "").strip().lower()

        raw_projs = self.db.get("processes", [])
        active_projs = [
            p for p in raw_projs
            if isinstance(p, dict) and p.get("is_archived") is not True
        ]

        if not text:
            return self._render(None)  # show all active

        def field(d: dict, key: str) -> str:
            v = d.get(key, "")
            return (v or "").lower() if isinstance(v, str) else str(v).lower()

        filtered = [
            p for p in active_projs
            if text in field(p, "name") or text in field(p, "title")
        ]

        self._render(filtered, query=text)

    def _pin_project(self, proc_id: str):
        procs = self.db.get("processes", [])
        updated = False
        for p in procs:
            if p.get("id") == proc_id:
                p["is_pinned"] = not p.get("is_pinned",False)
                updated = True
                break
        if not updated:
            return
        self.db["processes"] = procs
        self.projects_repo.save(self.db)
        self._render()
    