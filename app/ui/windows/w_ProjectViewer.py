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
from PySide6.QtGui import QFont, QAction
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

if TYPE_CHECKING:
    from app.models.project_models import (
        CopierItem,
        LinkItem,
        ProcessDef,
        ScriptItem,
    )

# -------------------- Runner: open a process and run scripts --------------------


class ProjectViewWindow(QMainWindow):
    def __init__(self, proc: "ProcessDef", parent=None):
        super().__init__(parent)
        self.proc = proc
        self.on_save_proc = None
        self.setWindowTitle(f"Proyecto — {proc.name}")
        self.resize(1000, 640)

        toolbar = QToolBar("Accesos")
        toolbar.setObjectName("ProjectViewerToolbar")
        self.addToolBar(toolbar)
        self.access_toolbar = toolbar

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

        central = QWidget()
        self.setCentralWidget(central)
        central.setObjectName("ProjectViewerBackground")
        root = QHBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # ==== Left: Description + scripts + output ====
        left = QVBoxLayout()
        left.setSpacing(4)  # less gap between sections
        title = QLabel(proc.name)
        title.setObjectName("RunTitle")

        # ===== Left: title and botones para edición de texto ==========
        left.addWidget(title)

        # enmarcamos los controles en un QFrame para separarlos visualmente
        header_frame = QFrame()
        header_frame.setFrameShape(QFrame.StyledPanel)
        header_frame.setFrameShadow(QFrame.Raised)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(6, 4, 6, 4)
        header_layout.setSpacing(8)

        # text formatting controls
        btn_bold = QPushButton("N")  # Negrita
        # show bold letter on button itself
        bold_font = QFont()
        bold_font.setBold(True)
        btn_bold.setFont(bold_font)
        btn_bold.setCheckable(True)
        btn_bold.setToolTip("Negrita / Bold")
        btn_bold.clicked.connect(self._toggle_bold)
        self.btn_bold = btn_bold
        header_layout.addWidget(btn_bold)

        # size selector (simple dropdown with few point sizes)
        self.size_selector = QComboBox()
        for sz in (8, 12, 16, 20):
            self.size_selector.addItem(str(sz))
        self.size_selector.setToolTip("Tamaño de texto / Font size")
        # use text-based signal since activated(int) is the only overload available
        self.size_selector.currentTextChanged.connect(self._change_font_size)
        header_layout.addWidget(self.size_selector)
        # update formatting state when cursor moves
        # (connect after creating QTextEdit below)

        btn_save = QPushButton("💾 Guardar")
        btn_save.clicked.connect(self._save_description)
        header_layout.addWidget(btn_save)
        header_layout.addStretch(8)

        # insert the frame into the left layout
        left.addWidget(header_frame)

        # --- Descripción con scroll (cambio mínimo) ---
        self.desc = QTextEdit()
        # handle previously stored HTML or plain text transparently
        description = proc.description or ""
        if isinstance(description, str):
            try:
                self.desc.setHtml(description)
            except (TypeError, ValueError):
                self.desc.setPlainText(description)
        else:
            self.desc.setPlainText(str(description))
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
        scrollDesc.setMaximumHeight(500)  # ajusta si quieres
        scrollDesc.setWidget(self.desc)

        # header_frame added earlier above, no need for TextEditHeader layout
        left.addWidget(scrollDesc)

        # --- Consola compacta + toggle (cambios mínimos) ---
        toggle_console = QPushButton("Ocultar consola")
        toggle_console.setCheckable(True)

        self.out = QTextEdit()
        self.out.setReadOnly(True)
        self.out.setPlaceholderText("Salida del proceso…")
        self.out.setMaximumHeight(220)  # hace la consola más pequeña

        toggle_console.toggled.connect(
            lambda on: (
                self.out.setVisible(not on),
                toggle_console.setText("Mostrar consola" if on else "Ocultar consola"),
            )
        )

        left.addWidget(toggle_console)
        left.addWidget(self.out, 0)  # sin stretch para respetar el máximo de altura

        # Right: tareas
        right = QVBoxLayout()
        right.setSpacing(8)
        lbl_tasks = QLabel("Tasks")
        lbl_tasks.setObjectName("RunTitle")
        right.addWidget(lbl_tasks)
        placeholder = QLabel("Aquí irá la sección de tareas en la versión 2.0")
        placeholder.setAlignment(Qt.AlignCenter)
        right.addWidget(placeholder, 1)
        right.addStretch()
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

    def _notify_proc_updated(self):
        if self.on_save_proc:
            self.on_save_proc(self.proc)

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

    def _refresh_toolbar_access_actions(self):
        spacer = getattr(self, "_spacer_action", None)
        if spacer is None:
            return
        for act in getattr(self, "_access_actions", []):
            self.access_toolbar.removeAction(act)
        self._access_actions = []

        def add(text: str, target_callable):
            act = QAction(text, self)
            act.triggered.connect(target_callable)
            self.access_toolbar.insertAction(spacer, act)
            self._access_actions.append(act)

        for lk in self.proc.links:
            add(f"🔗 {lk.title}", lambda _=None, t=lk.target: self._open(t))
        for cp in self.proc.copiers:
            add(f"🗄️ {cp.title}", lambda _=None, x=cp: self._runner_copy(x))
        for s in self.proc.scripts:
            script_name = Path(s.path).name or s.path
            add(f"▶ {script_name}", lambda _=None, script=s: self._run_script(script))


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
