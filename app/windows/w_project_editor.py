# seg_processing_manager.py
from __future__ import annotations
import os, uuid

from pathlib import Path
from typing import Optional
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QFileDialog, QMessageBox,
    QDialog, QDialogButtonBox, QListWidget, QListWidgetItem
)

from app.models.project_models import ProcessDef, ScriptItem, LinkItem, CopierItem

class ProjectEditorWindow(QDialog):
    """
    Permite la construccion de proyectos: solo Nombre, Descripción, botón “➕ Agregar…” y
    las 3 listas (Scripts / Accesos / Copiadores).
    La adición se hace mediante mini-diálogos por tipo.
    """
    def __init__(self, existing: Optional[ProcessDef]=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Process builder")
        self.resize(800, 550)
        self.setModal(True)
        self.proc = existing or ProcessDef(
            id=str(uuid.uuid4()), name="", description="", scripts=[], links=[], copiers=[], is_pinned=False
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # Header: Nombre + Add chooser
        head = QHBoxLayout()
        self.edt_name = QLineEdit(self.proc.name); self.edt_name.setPlaceholderText("Nombre del proceso")
        head.addWidget(QLabel("Nombre:")); head.addWidget(self.edt_name)
        self.btn_add_any = QPushButton("➕ Agregar…")
        self.btn_add_any.clicked.connect(self._open_add_chooser)
        head.addWidget(self.btn_add_any)
        root.addLayout(head)

        self.edt_desc = QTextEdit()
        # support existing HTML or plain text descriptions
        try:
            self.edt_desc.setHtml(self.proc.description)
        except Exception:
            self.edt_desc.setPlainText(self.proc.description)
        self.edt_desc.setPlaceholderText("Descripción del proceso (qué hace, notas, etc.)")
        self.edt_desc.setFixedHeight(90)
        root.addWidget(self.edt_desc)

        # 3 listas, sin editores ni controles extra
        lists_container = QWidget()
        lists_layout = QVBoxLayout(lists_container)
        lists_layout.setContentsMargins(8, 8, 8, 8)
        lists_layout.setSpacing(10)

        # Left: Scripts + Accesos (para balance)
        lists_layout.addWidget(self._hlabel("Scripts"))
        self.lst_scripts = QListWidget()
        self.lst_scripts.setAlternatingRowColors(True)
        for s in self.proc.scripts:
            self._add_script_item_to_list(s)
        lists_layout.addWidget(self.lst_scripts, 1)

        lists_layout.addWidget(self._hlabel("Accesos rápidos"))
        self.lst_links = QListWidget()
        self.lst_links.setAlternatingRowColors(True)
        for lk in self.proc.links:
            self._add_link_item_to_list(lk)
        lists_layout.addWidget(self.lst_links, 1)

        lists_layout.addWidget(self._hlabel("Copiadores"))
        self.lst_copiers = QListWidget()
        self.lst_copiers.setAlternatingRowColors(True)
        for cp in self.proc.copiers:
            self._add_copier_item_to_list(cp)
        lists_layout.addWidget(self.lst_copiers, 1)

        # Menú contextual en las tres listas

        for lst in (self.lst_scripts, self.lst_links, self.lst_copiers):
            lst.setContextMenuPolicy(Qt.CustomContextMenu)
            lst.customContextMenuRequested.connect(self._on_list_context_menu)

        # Atajos de teclado Delete

        QShortcut(QKeySequence.Delete, self.lst_scripts,
                activated=lambda: self._delete_selected_item('script'))
        QShortcut(QKeySequence.Delete, self.lst_links,
                activated=lambda: self._delete_selected_item('link'))
        QShortcut(QKeySequence.Delete, self.lst_copiers,
                activated=lambda: self._delete_selected_item('copier'))


        # se agrega lista a la base de la app

        root.addWidget(lists_container, 1)

        # buttons
        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)


    def _hlabel(self, text) -> QLabel:
        lbl = QLabel(text); lbl.setStyleSheet("font-size:14px;")
        return lbl

    # ========== ADD CHOOSER ==========
    def _open_add_chooser(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Agregar a este proceso")
        lay = QVBoxLayout(dlg)
        lay.addWidget(QLabel("¿Qué deseas agregar?"))
        row = QHBoxLayout()
        btn_script = QPushButton("➕ Script")
        btn_link   = QPushButton("➕ Link")
        btn_copier = QPushButton("➕ Copier")
        row.addWidget(btn_script); row.addWidget(btn_link); row.addWidget(btn_copier)
        lay.addLayout(row)
        btns = QDialogButtonBox(QDialogButtonBox.Close)
        lay.addWidget(btns)
        dlg.setStyleSheet("QDialog{background:#1b2224;} QLabel{color:#EFEDE1;} QPushButton{padding:6px 10px;}")
        btns.rejected.connect(dlg.reject)
        btns.accepted.connect(dlg.accept)
        btn_script.clicked.connect(lambda: (dlg.close(), self._add_script_via_dialog()))
        btn_link.clicked.connect(lambda: (dlg.close(), self._add_link_via_dialog()))
        btn_copier.clicked.connect(lambda: (dlg.close(), self._add_copier_via_dialog()))
        dlg.exec()

    # ========== DIALOGS PARA AGREGAR ==========
    def _add_script_via_dialog(self):
        d = QDialog(self); d.setWindowTitle("Nuevo script"); v = QVBoxLayout(d)
        p = QLineEdit(); p.setPlaceholderText("Ruta al script (.py)")
        a = QLineEdit(); a.setPlaceholderText("Argumentos (opcional)")
        w = QLineEdit(); w.setPlaceholderText("Directorio de trabajo (opcional)")
        rowp = QHBoxLayout(); rowp.addWidget(p,1)
        btnp = QPushButton("Buscar…"); btnp.clicked.connect(lambda: self._browse_file_into(p, "Python (*.py)"))
        rowp.addWidget(btnp)
        roww = QHBoxLayout(); roww.addWidget(w,1)
        btnw = QPushButton("Carpeta…"); btnw.clicked.connect(lambda: self._browse_dir_into(w))
        roww.addWidget(btnw)
        v.addWidget(QLabel("Ruta del script:")); v.addLayout(rowp)
        v.addWidget(QLabel("Argumentos:")); v.addWidget(a)
        v.addWidget(QLabel("Workdir:")); v.addLayout(roww)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); v.addWidget(btns)
        d.setStyleSheet("QDialog{background:#1b2224;} QLabel{color:#EFEDE1;} QLineEdit{background:#1D2927;color:#EFEDE1;border:1px solid #2e3b3f;border-radius:8px;padding:6px 8px;} QPushButton{padding:6px 10px;}")
        btns.accepted.connect(lambda: self._script_dialog_accept(d, p, a, w))
        btns.rejected.connect(d.reject)
        d.exec()

    def _script_dialog_accept(self, dlg, p: QLineEdit, a: QLineEdit, w: QLineEdit):
        path = p.text().strip()
        if not path:
            QMessageBox.warning(self, "Script", "Selecciona la ruta del script.")
            return
        s = ScriptItem(path=path, args=a.text().strip(), workdir=(w.text().strip() or None))
        self.proc.scripts.append(s)
        self._add_script_item_to_list(s)
        self.lst_scripts.setCurrentRow(self.lst_scripts.count()-1)
        dlg.accept()

    def _add_link_via_dialog(self):
        d = QDialog(self); d.setWindowTitle("Nuevo acceso"); v = QVBoxLayout(d)
        t = QLineEdit(); t.setPlaceholderText("Título")
        u = QLineEdit(); u.setPlaceholderText("URL o ruta")
        row = QHBoxLayout(); row.addWidget(u,1)
        btn = QPushButton("Buscar…"); btn.clicked.connect(lambda: self._browse_any_into(u))
        row.addWidget(btn)
        v.addWidget(QLabel("Título:")); v.addWidget(t)
        v.addWidget(QLabel("Destino:")); v.addLayout(row)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); v.addWidget(btns)
        d.setStyleSheet("QDialog{background:#1b2224;} QLabel{color:#EFEDE1;} QLineEdit{background:#1D2927;color:#EFEDE1;border:1px solid #2e3b3f;border-radius:8px;padding:6px 8px;} QPushButton{padding:6px 10px;}")
        btns.accepted.connect(lambda: self._link_dialog_accept(d, t, u))
        btns.rejected.connect(d.reject)
        d.exec()

    def _link_dialog_accept(self, dlg, t: QLineEdit, u: QLineEdit):
        title = t.text().strip()
        target = u.text().strip()
        if not title:
            QMessageBox.warning(self, "Acceso", "Escribe un título."); return
        if not target:
            QMessageBox.warning(self, "Acceso", "Escribe una URL o ruta."); return
        if not (target.lower().startswith(("http://","https://")) or os.path.exists(target)):
            ret = QMessageBox.question(self, "Confirmar", "El destino no parece válido.\n¿Guardar de todos modos?",
                                       QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if ret != QMessageBox.Yes:
                return
        lk = LinkItem(title=title, target=target)
        self.proc.links.append(lk)
        self._add_link_item_to_list(lk)
        self.lst_links.setCurrentRow(self.lst_links.count()-1)
        dlg.accept()

    def _add_copier_via_dialog(self):
        d = QDialog(self); d.setWindowTitle("Nuevo copiador"); v = QVBoxLayout(d)
        t  = QLineEdit(); t.setPlaceholderText("Título (ej. CSV a Input)")
        td = QLineEdit(); td.setPlaceholderText("Carpeta destino")
        hd = QLineEdit(); hd.setPlaceholderText("Carpeta histórico (opcional)")
        pt = QLineEdit(); pt.setPlaceholderText("Patrón (ej. *.csv)")
        row_td = QHBoxLayout(); row_td.addWidget(td,1)
        bt_td = QPushButton("Carpeta…"); bt_td.clicked.connect(lambda: self._browse_dir_into(td))
        row_td.addWidget(bt_td)
        row_hd = QHBoxLayout(); row_hd.addWidget(hd,1)
        bt_hd = QPushButton("Carpeta…"); bt_hd.clicked.connect(lambda: self._browse_dir_into(hd))
        row_hd.addWidget(bt_hd)
        v.addWidget(QLabel("Título:")); v.addWidget(t)
        v.addWidget(QLabel("Carpeta destino:")); v.addLayout(row_td)
        v.addWidget(QLabel("Carpeta histórico:")); v.addLayout(row_hd)
        v.addWidget(QLabel("Patrón:")); v.addWidget(pt)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); v.addWidget(btns)
        d.setStyleSheet("QDialog{background:#1b2224;} QLabel{color:#EFEDE1;} QLineEdit{background:#1D2927;color:#EFEDE1;border:1px solid #2e3b3f;border-radius:8px;padding:6px 8px;} QPushButton{padding:6px 10px;}")
        btns.accepted.connect(lambda: self._copier_dialog_accept(d, t, td, hd, pt))
        btns.rejected.connect(d.reject)
        d.exec()

    def _copier_dialog_accept(self, dlg, t: QLineEdit, td: QLineEdit, hd: QLineEdit, pt: QLineEdit):
        title = t.text().strip()
        target_dir = td.text().strip()
        history_dir = hd.text().strip()
        pattern = (pt.text().strip() or "*.csv")
        if not title:
            QMessageBox.warning(self, "Copiador", "Escribe un título."); return
        if not target_dir:
            QMessageBox.warning(self, "Copiador", "Define la carpeta destino."); return
        cp = CopierItem(title=title, target_dir=target_dir, history_dir=history_dir, pattern=pattern)
        self.proc.copiers.append(cp)
        self._add_copier_item_to_list(cp)
        self.lst_copiers.setCurrentRow(self.lst_copiers.count()-1)
        dlg.accept()

    # ========== helpers comunes de browse ==========
    def _browse_file_into(self, line_edit: QLineEdit, filter_text: str = "Todos (*.*)"):
        path, _ = QFileDialog.getOpenFileName(self, "Elegir archivo", str(Path.home()), filter_text)
        if path:
            line_edit.setText(path)

    def _browse_any_into(self, line_edit: QLineEdit):
        path, _ = QFileDialog.getOpenFileName(self, "Elegir archivo (o Cancela para carpeta)", str(Path.home()))
        if path:
            line_edit.setText(path); return
        folder = QFileDialog.getExistingDirectory(self, "Elegir carpeta", str(Path.home()))
        if folder:
            line_edit.setText(folder)

    # ========== listas (añadir visualmente) ==========
    def _add_script_item_to_list(self, s: ScriptItem):
        it = QListWidgetItem(f"{s.path}  {s.args}".strip())
        it.setData(Qt.UserRole, s)
        self.lst_scripts.addItem(it)

    def _add_link_item_to_list(self, lk: LinkItem):
        it = QListWidgetItem(f"{lk.title}  →  {lk.target}")
        it.setData(Qt.UserRole, lk)
        self.lst_links.addItem(it)

    def _add_copier_item_to_list(self, cp: CopierItem):
        it = QListWidgetItem(f"{cp.title}  →  {cp.target_dir}")
        it.setData(Qt.UserRole, cp)
        self.lst_copiers.addItem(it)

    # ---- save
    def _on_accept(self):
        name = self.edt_name.text().strip()
        if not name:
            QMessageBox.information(self, "Builder", "El proceso necesita un nombre.")
            return
        self.proc.name = name
        # store HTML so formatting is kept
        self.proc.description = self.edt_desc.toHtml().strip()
        self.accept()
    
    def _on_list_context_menu(self, pos):
        lst = self.sender()  # cuál lista abrió el menú
        if lst not in (self.lst_scripts, self.lst_links, self.lst_copiers):
            return
        from PySide6.QtWidgets import QMenu
        menu = QMenu(self)

        # Determina el tipo
        if lst is self.lst_scripts:
            kind = 'script'
        elif lst is self.lst_links:
            kind = 'link'
        else:
            kind = 'copier'

        act_del = menu.addAction("🗑️ Borrar")
        action = menu.exec_(lst.mapToGlobal(pos))
        if action == act_del:
            self._delete_selected_item(kind)


    def _delete_selected_item(self, kind: str):
        if kind == 'script':
            lst = self.lst_scripts
            arr = self.proc.scripts
        elif kind == 'link':
            lst = self.lst_links
            arr = self.proc.links
        else:
            lst = self.lst_copiers
            arr = self.proc.copiers

        row = lst.currentRow()
        if row < 0:
            return
        # borra visual
        lst.takeItem(row)
        # borra del modelo
        if 0 <= row < len(arr):
            del arr[row]

    # dentro de la clase ProcessBuilderWindow
    def _browse_dir_into(self, line_edit: QLineEdit):
        folder = QFileDialog.getExistingDirectory(self, "Elegir carpeta", str(Path.home()))
        if folder:
            line_edit.setText(folder)

    def result_process(self) -> ProcessDef:
        return self.proc