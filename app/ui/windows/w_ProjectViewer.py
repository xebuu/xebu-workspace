# w_ProjectViewer.py
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QMenu,
    QSizePolicy,
    QScrollArea,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QToolBar,
)

from app.core.task_helpers import create_task, delete_task_by_id
from app.database.tasks_repository import TasksRepository

if TYPE_CHECKING:
    from app.models.project_models import (
        CopierItem,
        LinkItem,
        ProcessDef,
        ScriptItem,
    )
from app.ui.windows.w_new_project import NewProjectWindow

# -------------------- Runner: open a process and run scripts --------------------


class ProjectViewWindow(QMainWindow):
    def __init__(self, proc: "ProcessDef", parent=None):
        super().__init__(parent)
        self.proc = proc
        self.on_save_proc = None
        self.on_delete_proc = None
        self.setWindowTitle(f"Proyecto — {proc.name}")
        self.resize(1000, 640)

        toolbar = QToolBar("Accesos")
        toolbar.setObjectName("ProjectViewerToolbar")
        self.addToolBar(toolbar)
        self.access_toolbar = toolbar

        toolbar.setContextMenuPolicy(Qt.CustomContextMenu)
        toolbar.customContextMenuRequested.connect(self._toolbar_context_menu)

        add_button = QToolButton()
        add_button.setText("Agregar   ")
        add_button.setPopupMode(QToolButton.InstantPopup)
        add_menu = QMenu(self)
        add_menu.addAction("Script", self._add_script_dialog)
        add_menu.addAction("Copiador", self._add_copier_dialog)
        add_menu.addAction("Acceso", self._add_link_dialog)
        add_button.setMenu(add_menu)
        toolbar.addWidget(add_button)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._spacer_action = toolbar.addWidget(spacer)
        self._access_actions: list[QAction] = []
        self.tasks_repo = TasksRepository()
        self.tasks = self.tasks_repo.list_all()
        self.tasks_repo.reset_daily_if_needed(self.tasks)

        central = QWidget()
        self.setCentralWidget(central)
        central.setObjectName("ProjectViewerBackground")
        root = QHBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # ==== Left: Description + scripts + output ====
        left = QVBoxLayout()
        left.setSpacing(4)
        desc_container = QFrame()
        desc_container.setObjectName("DescContainer")
        desc_container.setFrameShape(QFrame.StyledPanel)
        desc_container.setFrameShadow(QFrame.Raised)
        desc_layout = QVBoxLayout(desc_container)
        desc_layout.setContentsMargins(12, 12, 12, 12)
        desc_layout.setSpacing(8)

        self.title_label = QLabel(proc.name)
        self.title_label.setObjectName("RunTitle")
        desc_layout.addWidget(self.title_label)

        # enmarcamos los controles en un QFrame para separarlos visualmente
        header_frame = QFrame()
        header_frame.setFrameShape(QFrame.StyledPanel)
        header_frame.setFrameShadow(QFrame.Raised)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(6, 4, 6, 4)
        header_layout.setSpacing(8)

        # text formatting controls
        btn_bold = QPushButton("N")  # Negrita
        bold_font = QFont()
        bold_font.setBold(True)
        btn_bold.setFont(bold_font)
        btn_bold.setCheckable(True)
        btn_bold.setToolTip("Negrita / Bold")
        btn_bold.clicked.connect(self._toggle_bold)
        self.btn_bold = btn_bold
        header_layout.addWidget(btn_bold)

        self.size_selector = QComboBox()
        for sz in (8, 12, 16, 20):
            self.size_selector.addItem(str(sz))
        self.size_selector.setToolTip("Tamaño de texto / Font size")
        self.size_selector.currentTextChanged.connect(self._change_font_size)
        header_layout.addWidget(self.size_selector)

        btn_save = QPushButton("💾 Guardar")
        btn_save.clicked.connect(self._save_description)
        header_layout.addWidget(btn_save)
        header_layout.addStretch(8)

        desc_layout.addWidget(header_frame)

        # --- Descripción con scroll (cambio mínimo) ---
        self.desc = QTextEdit()
        self._apply_description_to_editor()
        self.desc.setContentsMargins(0, 0, 0, 0)
        self.desc.setFixedHeight(700)
        self.desc.cursorPositionChanged.connect(self._update_format_buttons)
        # initialize size selector to current font size
        if hasattr(self, "size_selector"):
            pt = self.desc.fontPointSize()
            if pt:
                self.size_selector.setCurrentText(str(int(pt)))

        scrollDesc = QScrollArea()
        scrollDesc.setWidgetResizable(True)
        scrollDesc.setFrameShape(QFrame.NoFrame)
        scrollDesc.setContentsMargins(0, 0, 0, 0)
        scrollDesc.setMaximumHeight(500)
        scrollDesc.setWidget(self.desc)
        desc_layout.addWidget(scrollDesc)
        left.addWidget(desc_container)

        self.out = QTextEdit()
        self.out.setReadOnly(True)
        self.out.setPlaceholderText("Salida del proceso…")
        self.out.setMaximumHeight(220)

        self._configure_console_section(left)

        # Right: tareas
        right = QVBoxLayout()
        right.setSpacing(8)
        task_container = QFrame()
        task_container.setObjectName("TaskContainer")
        task_container.setFrameShape(QFrame.StyledPanel)
        task_container.setFrameShadow(QFrame.Raised)
        container_layout = QVBoxLayout(task_container)
        container_layout.setContentsMargins(12, 12, 12, 12)
        container_layout.setSpacing(8)

        title_row = QHBoxLayout()
        lbl_tasks = QLabel("Tasks")
        lbl_tasks.setObjectName("RunTitle")
        title_row.addWidget(lbl_tasks)
        title_row.addStretch()
        container_layout.addLayout(title_row)

        search_row = QHBoxLayout()
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("Agregar tarea rápida")
        self.task_input.returnPressed.connect(self._add_quick_task)
        btn_task_add = QPushButton("Agregar")
        btn_task_add.clicked.connect(self._add_quick_task)
        search_row.addWidget(self.task_input)
        search_row.addWidget(btn_task_add)
        container_layout.addLayout(search_row)

        self.task_scroll = QScrollArea()
        self.task_scroll.setWidgetResizable(True)
        self.task_scroll.setMaximumHeight(300)
        self.task_wrapper = QWidget()
        self.task_layout = QVBoxLayout(self.task_wrapper)
        self.task_layout.setContentsMargins(8, 8, 8, 8)
        self.task_layout.setSpacing(8)
        self.task_scroll.setWidget(self.task_wrapper)
        container_layout.addWidget(self.task_scroll, 1)
        container_layout.addStretch(1)

        right.addWidget(task_container, 1)
        self._render_tasks()
        root.addLayout(left, 2)
        root.addLayout(right, 1)
        self._refresh_toolbar_access_actions()

    def _save_description(self):
        # capture HTML so bold and indentation are preserved
        html = self.desc.toHtml()
        self.proc.description = html  # actualizar el modelo en memoria

        # call optional callback to persist change
        if self.on_save_proc:
            self.on_save_proc(self.proc)

        if self.statusBar():
            self.statusBar().showMessage("Descripción guardada", 2000)

    def _apply_description_to_editor(self):
        description = self.proc.description or ""
        self.desc.blockSignals(True)
        try:
            if isinstance(description, str):
                try:
                    self.desc.setHtml(description)
                except (TypeError, ValueError):
                    self.desc.setPlainText(description)
            else:
                self.desc.setPlainText(str(description))
        finally:
            self.desc.blockSignals(False)

    def _toggle_bold(self, _checked: bool = False):
        """Toggle bold formatting for the current selection or future text."""
        cursor = self.desc.textCursor()
        if cursor.hasSelection():
            fmt = cursor.charFormat()
            current_weight = fmt.fontWeight()
            new_weight = QFont.Bold if current_weight != QFont.Bold else QFont.Normal
            fmt.setFontWeight(new_weight)
            cursor.mergeCharFormat(fmt)
        else:
            # when there's no selection, change the widget's default weight
            current_weight = self.desc.fontWeight()
            new_weight = QFont.Bold if current_weight != QFont.Bold else QFont.Normal
            self.desc.setFontWeight(new_weight)
        # reflect state on button
        if hasattr(self, "btn_bold"):
            self.btn_bold.setChecked(new_weight == QFont.Bold)

    def _change_font_size(self, text: str):
        """Change font size for selection or future typing."""
        try:
            size = float(text)
        except ValueError:
            return
        cursor = self.desc.textCursor()
        if cursor.hasSelection():
            fmt = cursor.charFormat()
            fmt.setFontPointSize(size)
            cursor.mergeCharFormat(fmt)
        else:
            self.desc.setFontPointSize(size)
        # keep combobox in sync
        if hasattr(self, "size_selector"):
            self.size_selector.setCurrentText(str(int(size)))

    def _update_format_buttons(self):
        """Keep toolbar buttons in sync with current cursor format."""
        fmt = self.desc.currentCharFormat()
        if hasattr(self, "btn_bold"):
            self.btn_bold.setChecked(fmt.fontWeight() == QFont.Bold)
        if hasattr(self, "size_selector"):
            pt = fmt.fontPointSize() or self.desc.fontPointSize()
            if pt:
                self.size_selector.setCurrentText(str(int(pt)))

        # Si te pasaron un callback de guardado, úsalo
        if self.on_save_proc:
            self.on_save_proc(self.proc)

        # Feedback visual rápido (opcional)
        if self.statusBar():
            self.statusBar().showMessage("Descripción guardada", 2000)

    def _run_script(self, s: "ScriptItem"):
        if not s.path or not Path(s.path).exists():
            QMessageBox.warning(self, "Run", f"No existe el script:\n{s.path}")
            return
        cmd = [sys.executable, s.path] + ([*s.args.split()] if s.args else [])
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=s.workdir or None,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except OSError as e:
            QMessageBox.critical(self, "Run", str(e))
            return

        self.out.append(f"$ {' '.join(cmd)}")

        def _collect():
            out = ""
            try:
                with proc:
                    out, _ = proc.communicate()
            except (OSError, ValueError) as e:
                out = f"[error] {e}"
            self.out.append(out or "(sin salida)")

        QTimer.singleShot(10, _collect)

    def _configure_console_section(self, layout: QVBoxLayout):
        toggle_console = QPushButton("Ocultar consola")
        toggle_console.setCheckable(True)
        toggle_console.toggled.connect(
            lambda on: (
                self.out.setVisible(not on),
                toggle_console.setText("Mostrar consola" if on else "Ocultar consola"),
            )
        )

        has_scripts = bool(getattr(self.proc, "scripts", []))
        if has_scripts:
            layout.addWidget(toggle_console)
            layout.addWidget(self.out, 0)
        else:
            self.out.hide()

    def _toolbar_context_menu(self, pos):
        action = self.access_toolbar.actionAt(pos)
        if action is None:
            return
        data = action.data()
        if not isinstance(data, dict):
            return
        menu = QMenu(self)
        menu.addAction("Editar", lambda: self._edit_toolbar_action(action))
        menu.addAction("Borrar", lambda: self._remove_toolbar_action(action))
        menu.exec_(self.access_toolbar.mapToGlobal(pos))

    def _edit_toolbar_action(self, action: QAction):
        data = action.data()
        kind = data.get("kind")
        item = data.get("item")
        if kind == "link":
            self._edit_link_item(item)
        elif kind == "copier":
            self._edit_copier_item(item)
        elif kind == "script":
            self._edit_script_item(item)

    def _remove_toolbar_action(self, action: QAction):
        data = action.data()
        kind = data.get("kind")
        item = data.get("item")
        arr = getattr(self.proc, f"{kind}s", [])
        if item in arr:
            arr.remove(item)
        self._refresh_toolbar_access_actions()


    def _add_script_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Nuevo script")
        v = QVBoxLayout(dlg)
        p = QLineEdit()
        p.setPlaceholderText("Ruta al script (.py)")
        a = QLineEdit()
        a.setPlaceholderText("Argumentos (opcional)")
        w = QLineEdit()
        w.setPlaceholderText("Directorio de trabajo (opcional)")
        rowp = QHBoxLayout()
        rowp.addWidget(p, 1)
        btnp = QPushButton("Buscar…")
        btnp.clicked.connect(lambda: self._browse_file_into(p, "Python (*.py)"))
        rowp.addWidget(btnp)
        roww = QHBoxLayout()
        roww.addWidget(w, 1)
        btnw = QPushButton("Carpeta…")
        btnw.clicked.connect(lambda: self._browse_dir_into(w))
        roww.addWidget(btnw)
        v.addWidget(QLabel("Ruta del script:"))
        v.addLayout(rowp)
        v.addWidget(QLabel("Argumentos:"))
        v.addWidget(a)
        v.addWidget(QLabel("Workdir:"))
        v.addLayout(roww)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        v.addWidget(btns)
        dlg.setStyleSheet(
            "QDialog{background:#1b2224;} QLabel{color:#EFEDE1;} QLineEdit{background:#1D2927;color:#EFEDE1;border:1px solid #2e3b3f;border-radius:8px;padding:6px 8px;} QPushButton{padding:6px 10px;}"
        )
        btns.accepted.connect(lambda: self._script_dialog_accept(dlg, p, a, w))
        btns.rejected.connect(dlg.reject)
        dlg.exec()

    def _script_dialog_accept(self, dlg, p: QLineEdit, a: QLineEdit, w: QLineEdit):
        path = p.text().strip()
        if not path:
            QMessageBox.warning(self, "Script", "Selecciona la ruta del script.")
            return
        from app.models.project_models import ScriptItem

        s = ScriptItem(
            path=path, args=a.text().strip(), workdir=(w.text().strip() or None)
        )
        self.proc.scripts.append(s)
        self._refresh_toolbar_access_actions()
        self._notify_proc_updated()
        dlg.accept()

    def _add_link_dialog(self):
        d = QDialog(self)
        d.setWindowTitle("Nuevo acceso")
        v = QVBoxLayout(d)
        t = QLineEdit()
        t.setPlaceholderText("Título")
        u = QLineEdit()
        u.setPlaceholderText("URL o ruta")
        row = QHBoxLayout()
        row.addWidget(u, 1)
        btn = QPushButton("Buscar…")
        btn.clicked.connect(lambda: self._browse_any_into(u))
        row.addWidget(btn)
        v.addWidget(QLabel("Título:"))
        v.addWidget(t)
        v.addWidget(QLabel("Destino:"))
        v.addLayout(row)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        v.addWidget(btns)
        d.setStyleSheet(
            "QDialog{background:#1b2224;} QLabel{color:#EFEDE1;} QLineEdit{background:#1D2927;color:#EFEDE1;border:1px solid #2e3b3f;border-radius:8px;padding:6px 8px;} QPushButton{padding:6px 10px;}"
        )
        btns.accepted.connect(lambda: self._link_dialog_accept(d, t, u))
        btns.rejected.connect(d.reject)
        d.exec()

    def _link_dialog_accept(self, dlg, t: QLineEdit, u: QLineEdit):
        title = t.text().strip()
        target = u.text().strip()
        if not title:
            QMessageBox.warning(self, "Acceso", "Escribe un título.")
            return
        if not target:
            QMessageBox.warning(self, "Acceso", "Escribe una URL o ruta.")
            return
        if not (
            target.lower().startswith(("http://", "https://")) or os.path.exists(target)
        ):
            ret = QMessageBox.question(
                self,
                "Confirmar",
                "El destino no parece válido.\n¿Guardar de todos modos?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if ret != QMessageBox.Yes:
                return
        from app.models.project_models import LinkItem

        lk = LinkItem(title=title, target=target)
        self.proc.links.append(lk)
        self._refresh_toolbar_access_actions()
        self._notify_proc_updated()
        dlg.accept()

    def _add_copier_dialog(self):
        d = QDialog(self)
        d.setWindowTitle("Nuevo copiador")
        v = QVBoxLayout(d)
        t = QLineEdit()
        t.setPlaceholderText("Título (ej. CSV a Input)")
        td = QLineEdit()
        td.setPlaceholderText("Carpeta destino")
        hd = QLineEdit()
        hd.setPlaceholderText("Carpeta histórico (opcional)")
        pt = QLineEdit()
        pt.setPlaceholderText("Patrón (ej. *.csv)")
        row_td = QHBoxLayout()
        row_td.addWidget(td, 1)
        bt_td = QPushButton("Carpeta…")
        bt_td.clicked.connect(lambda: self._browse_dir_into(td))
        row_td.addWidget(bt_td)
        row_hd = QHBoxLayout()
        row_hd.addWidget(hd, 1)
        bt_hd = QPushButton("Carpeta…")
        bt_hd.clicked.connect(lambda: self._browse_dir_into(hd))
        row_hd.addWidget(bt_hd)
        v.addWidget(QLabel("Título:"))
        v.addWidget(t)
        v.addWidget(QLabel("Carpeta destino:"))
        v.addLayout(row_td)
        v.addWidget(QLabel("Carpeta histórico:"))
        v.addLayout(row_hd)
        v.addWidget(QLabel("Patrón:"))
        v.addWidget(pt)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        v.addWidget(btns)
        d.setStyleSheet(
            "QDialog{background:#1b2224;} QLabel{color:#EFEDE1;} QLineEdit{background:#1D2927;color:#EFEDE1;border:1px solid #2e3b3f;border-radius:8px;padding:6px 8px;} QPushButton{padding:6px 10px;}"
        )
        btns.accepted.connect(lambda: self._copier_dialog_accept(d, t, td, hd, pt))
        btns.rejected.connect(d.reject)
        d.exec()

    def _copier_dialog_accept(
        self, dlg, t: QLineEdit, td: QLineEdit, hd: QLineEdit, pt: QLineEdit
    ):
        title = t.text().strip()
        target_dir = td.text().strip()
        history_dir = hd.text().strip()
        pattern = pt.text().strip() or "*.csv"
        if not title:
            QMessageBox.warning(self, "Copiador", "Escribe un título.")
            return
        if not target_dir:
            QMessageBox.warning(self, "Copiador", "Define la carpeta destino.")
            return
        from app.models.project_models import CopierItem

        cp = CopierItem(
            title=title, target_dir=target_dir, history_dir=history_dir, pattern=pattern
        )
        self.proc.copiers.append(cp)
        self._refresh_toolbar_access_actions()
        self._notify_proc_updated()
        dlg.accept()

    def _browse_file_into(self, line_edit: QLineEdit, filter_text: str = "Todos (*.*)"):
        path, _ = QFileDialog.getOpenFileName(self, "Elegir archivo", str(Path.home()), filter_text)
        if path:
            line_edit.setText(path)

    def _browse_any_into(self, line_edit: QLineEdit):
        path, _ = QFileDialog.getOpenFileName(
            self, "Elegir archivo (o Cancela para carpeta)", str(Path.home())
        )
        if path:
            line_edit.setText(path)
            return
        folder = QFileDialog.getExistingDirectory(
            self, "Elegir carpeta", str(Path.home())
        )
        if folder:
            line_edit.setText(folder)

    def _browse_dir_into(self, line_edit: QLineEdit):
        folder = QFileDialog.getExistingDirectory(
            self, "Elegir carpeta", str(Path.home())
        )
        if folder:
            line_edit.setText(folder)

    def _add_quick_task(self):
        text = self.task_input.text().strip()
        if not text:
            return
        new_task = create_task(text, today=datetime.now().date())
        self.tasks.append(new_task)
        self.tasks_repo.save_all(self.tasks)
        self.task_input.clear()
        self._render_tasks()

    def _render_tasks(self):
        for i in reversed(range(self.task_layout.count())):
            widget = self.task_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        if not self.tasks:
            empty = QLabel("No hay tareas registradas.")
            empty.setAlignment(Qt.AlignCenter)
            self.task_layout.addWidget(empty, 1)
            self.task_layout.addStretch(1)
            return
        for task in self.tasks:
            row = _MiniTaskRow(
                task,
                on_toggle=self._toggle_task,
                on_delete=self._delete_task,
                parent=self,
            )
            self.task_layout.addWidget(row)
        self.task_layout.addStretch(1)

    def _toggle_task(self, task: dict):
        task["completado"] = not task.get("completado", False)
        task["ultima_actualizacion"] = str(datetime.now().date())
        self.tasks_repo.save_all(self.tasks)
        self._render_tasks()

    def _delete_task(self, task: dict):
        delete_task_by_id(self.tasks, task)
        self.tasks_repo.save_all(self.tasks)
        self._render_tasks()

    def _refresh_toolbar_access_actions(self):
        spacer = getattr(self, "_spacer_action", None)
        if spacer is None:
            return
        for act in getattr(self, "_access_actions", []):
            self.access_toolbar.removeAction(act)
        self._access_actions = []

        def add(text: str, target_callable, payload: dict):
            act = QAction(text, self)
            act.triggered.connect(target_callable)
            self.access_toolbar.insertAction(spacer, act)
            self._access_actions.append(act)
            act.setData(payload)

        for lk in self.proc.links:
            add(
                f"🔗 {lk.title}",
                lambda _=None, t=lk.target: self._open(t),
                {"kind": "link", "item": lk},
            )
        for cp in self.proc.copiers:
            add(
                f"🗄️ {cp.title}",
                lambda _=None, x=cp: self._runner_copy(x),
                {"kind": "copier", "item": cp},
            )
        for s in self.proc.scripts:
            script_name = Path(s.path).name or s.path
            add(
                f"▶ {script_name}",
                lambda _=None, script=s: self._run_script(script),
                {"kind": "script", "item": s},
            )

    def _notify_proc_updated(self):
        if self.on_save_proc:
            self.on_save_proc(self.proc)

    def _edit_link_item(self, link: "LinkItem"):
        dlg = QDialog(self)
        dlg.setWindowTitle("Editar acceso")
        dlg.setStyleSheet("QDialog { background:#2d2d2d; }")
        v = QVBoxLayout(dlg)
        t = QLineEdit(link.title)
        u = QLineEdit(link.target)
        row = QHBoxLayout()
        row.addWidget(u, 1)
        btn = QPushButton("Buscar…")
        btn.clicked.connect(lambda: self._browse_any_into(u))
        row.addWidget(btn)
        v.addWidget(QLabel("Título:"))
        v.addWidget(t)
        v.addWidget(QLabel("Destino:"))
        v.addLayout(row)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        v.addWidget(btns)
        btns.accepted.connect(lambda: self._apply_link_edit(link, t, u, dlg))
        btns.rejected.connect(dlg.reject)
        dlg.exec()

    def _apply_link_edit(self, link, title_input, target_input, dlg):
        title = title_input.text().strip()
        target = target_input.text().strip()
        if not title or not target:
            QMessageBox.warning(self, "Acceso", "Título y destino son obligatorios.")
            return
        link.title = title
        link.target = target
        self._refresh_toolbar_access_actions()
        dlg.accept()

    def _edit_copier_item(self, copier: "CopierItem"):
        dlg = QDialog(self)
        dlg.setWindowTitle("Editar copiador")
        v = QVBoxLayout(dlg)
        t = QLineEdit(copier.title)
        td = QLineEdit(copier.target_dir)
        hd = QLineEdit(copier.history_dir)
        pt = QLineEdit(copier.pattern)
        v.addWidget(QLabel("Título:"))
        v.addWidget(t)
        v.addWidget(QLabel("Carpeta destino:"))
        v.addWidget(td)
        v.addWidget(QLabel("Carpeta histórico:"))
        v.addWidget(hd)
        v.addWidget(QLabel("Patrón:"))
        v.addWidget(pt)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        v.addWidget(btns)
        btns.accepted.connect(lambda: self._apply_copier_edit(copier, t, td, hd, pt, dlg))
        btns.rejected.connect(dlg.reject)
        dlg.exec()

    def _apply_copier_edit(self, copier, title_input, target_input, history_input, pattern_input, dlg):
        title = title_input.text().strip()
        target_dir = target_input.text().strip()
        if not title or not target_dir:
            QMessageBox.warning(self, "Copiador", "Título y carpeta destino son obligatorios.")
            return
        copier.title = title
        copier.target_dir = target_dir
        copier.history_dir = history_input.text().strip()
        copier.pattern = pattern_input.text().strip() or "*.csv"
        self._refresh_toolbar_access_actions()
        dlg.accept()

    def _edit_script_item(self, script: "ScriptItem"):
        dlg = QDialog(self)
        dlg.setWindowTitle("Editar script")
        v = QVBoxLayout(dlg)
        path_edit = QLineEdit(script.path)
        args_edit = QLineEdit(script.args)
        work_edit = QLineEdit(script.workdir or "")
        row = QHBoxLayout()
        row.addWidget(path_edit, 1)
        btn = QPushButton("Buscar…")
        btn.clicked.connect(lambda: self._browse_file_into(path_edit, "Python (*.py)"))
        row.addWidget(btn)
        v.addWidget(QLabel("Ruta del script:"))
        v.addLayout(row)
        v.addWidget(QLabel("Argumentos:"))
        v.addWidget(args_edit)
        v.addWidget(QLabel("Workdir:"))
        v.addWidget(work_edit)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        v.addWidget(btns)
        btns.accepted.connect(lambda: self._apply_script_edit(script, path_edit, args_edit, work_edit, dlg))
        btns.rejected.connect(dlg.reject)
        dlg.exec()

    def _apply_script_edit(self, script, path_edit, args_edit, work_edit, dlg):
        path = path_edit.text().strip()
        if not path:
            QMessageBox.warning(self, "Script", "Selecciona la ruta del script.")
            return
        script.path = path
        script.args = args_edit.text().strip()
        script.workdir = work_edit.text().strip() or None
        self._refresh_toolbar_access_actions()
        dlg.accept()


class _MiniTaskRow(QFrame):
    def __init__(self, task: dict, on_toggle, on_delete, parent=None):
        super().__init__(parent)
        self.task = task
        self.on_toggle = on_toggle
        self.on_delete = on_delete

        self.setObjectName("TaskRowMini")
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(6)

        self.lbl = QLabel()
        self.lbl.setWordWrap(True)
        self.btn_toggle = QPushButton()
        self.btn_toggle.setFixedWidth(32)
        btn_delete = QPushButton("✕")
        btn_delete.setFixedWidth(32)

        self.btn_toggle.clicked.connect(lambda: self.on_toggle(task))
        btn_delete.clicked.connect(lambda: self.on_delete(task))

        lay.addWidget(self.lbl, 1)
        lay.addWidget(self.btn_toggle)
        lay.addWidget(btn_delete)

        self.update_state()

    def update_state(self):
        done = self.task.get("completado", False)
        self.btn_toggle.setText("☑" if done else "☐")
        self.lbl.setText(self._format_text())

    def _format_text(self) -> str:
        text = self.task.get("tarea", "")
        details = text
        deadline = (self.task.get("deadline") or "").strip()
        if deadline:
            details += f" (vencimiento {deadline})"
        if self.task.get("diaria"):
            details += " • diaria"
        prioridad = (self.task.get("prioridad") or "media").lower()
        if prioridad == "alta":
            details += " • prioridad alta"
        elif prioridad == "baja":
            details += " • prioridad baja"
        return details

    def _open(self, target: str):
        try:
            from app.core.helpers import open_resource_target
        except ModuleNotFoundError as e:
            QMessageBox.warning(self, "Abrir", f"No se puede cargar helper: {e}")
            return

        try:
            open_resource_target(target)
        except (OSError, webbrowser.Error) as e:
            QMessageBox.warning(self, "Abrir", str(e))

    def _open_placeholder_dialog(self, title: str):
        QMessageBox.information(self, title, f"{title} placeholder")

    def _runner_copy(self, cp: "CopierItem"):
        target_dir = Path(cp.target_dir).expanduser()
        if not target_dir:
            QMessageBox.warning(
                self, "Copiar", "Este copiador no tiene carpeta destino."
            )
            return
        target_dir.mkdir(parents=True, exist_ok=True)
        history_dir = Path(cp.history_dir).expanduser() if cp.history_dir else None
        if history_dir:
            history_dir.mkdir(parents=True, exist_ok=True)

        filt = f"{cp.pattern};;Todos (*.*)" if cp.pattern else "Todos (*.*)"
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo a copiar", str(Path.home()), filt
        )
        if not file_path:
            return

        try:
            if history_dir:
                for archivo in target_dir.glob(cp.pattern or "*.*"):
                    destino = history_dir / archivo.name
                    if destino.exists():
                        base, ext = os.path.splitext(archivo.name)
                        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                        destino = history_dir / f"{base}_{ts}{ext}"
                    shutil.move(str(archivo), str(destino))
            shutil.copy2(file_path, target_dir / Path(file_path).name)
            QMessageBox.information(
                self,
                "Copiar",
                "Archivo movido a histórico (si aplica) y copiado al destino ✅",
            )
        except OSError as e:
            QMessageBox.critical(self, "Copiar", f"Error: {e}")

if __name__ == "__main__":
    PROJECT_ROOT = Path(__file__).resolve().parents[3]
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    from app.models.project_models import (
        CopierItem,
        LinkItem,
        ProcessDef,
        ScriptItem,
    )

    app = QApplication(sys.argv)
    sample_proc = ProcessDef(
        id="demo",
        name="Demo Project",
        description="Escribe aquí una descripción del proyecto.",
        is_pinned=True,
        links=[LinkItem(title="Documentación", target="https://example.com")],
        scripts=[ScriptItem(path=__file__)],
        copiers=[CopierItem(title="Copiar muestra", target_dir=str(Path.home()))],
    )
    window = ProjectViewWindow(sample_proc)
    window.show()
    sys.exit(app.exec())
