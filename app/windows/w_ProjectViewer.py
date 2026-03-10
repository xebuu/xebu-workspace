# w_ProjectViewer.py
from __future__ import annotations
import sys, os,  subprocess, webbrowser
from pathlib import Path

from PySide6.QtCore import  QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QTextEdit, QFileDialog, QMessageBox, QComboBox)

from app.models.project_models import ProcessDef, ScriptItem, CopierItem

# -------------------- Runner: open a process and run scripts --------------------

class ProjectViewWindow(QMainWindow):
    def __init__(self, proc: "ProcessDef", parent=None):
        super().__init__(parent)
        self.proc = proc
        self.on_save_proc = None
        self.setWindowTitle(f"Proyecto — {proc.name}")
        self.resize(1000, 640)


        central = QWidget(); self.setCentralWidget(central)
        central.setObjectName("ProjectViewerBackground")
        root = QHBoxLayout(central); root.setContentsMargins(12,12,12,12); root.setSpacing(10)

        # ==== Left: Description + scripts + output ====
        left = QVBoxLayout(); left.setSpacing(4)  # less gap between sections
        title = QLabel(proc.name); title.setObjectName("RunTitle")

        # ===== Left: title and botones para edición de texto ==========
        title = QLabel(proc.name); title.setObjectName("RunTitle")
        left.addWidget(title)

        # enmarcamos los controles en un QFrame para separarlos visualmente
        header_frame = QFrame()
        header_frame.setFrameShape(QFrame.StyledPanel)
        header_frame.setFrameShadow(QFrame.Raised)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(6,4,6,4)
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
        try:
            self.desc.setHtml(proc.description)
        except Exception:
            self.desc.setPlainText(proc.description)
        self.desc.setContentsMargins(0,0,0,0)
        self.desc.setFixedHeight(700)
        self.desc.cursorPositionChanged.connect(self._update_format_buttons)
        # initialize size selector to current font size
        if hasattr(self, 'size_selector'):
            pt = self.desc.fontPointSize()
            if pt:
                self.size_selector.setCurrentText(str(int(pt)))

        scrollDesc = QScrollArea()
        scrollDesc.setWidgetResizable(True)
        scrollDesc.setFrameShape(QFrame.NoFrame)
        scrollDesc.setContentsMargins(0,0,0,0)
        scrollDesc.setMaximumHeight(500)  # ajusta si quieres
        scrollDesc.setWidget(self.desc)

        left.addWidget(title)
        # header_frame added earlier above, no need for TextEditHeader layout
        left.addWidget(scrollDesc)

        # --- Consola compacta + toggle (cambios mínimos) ---
        toggle_console = QPushButton("Ocultar consola")
        toggle_console.setCheckable(True)

        self.out = QTextEdit()
        self.out.setReadOnly(True)
        self.out.setPlaceholderText("Salida del proceso…")
        self.out.setMaximumHeight(220)  # hace la consola más pequeña

        toggle_console.toggled.connect(lambda on: (
            self.out.setVisible(not on),
            toggle_console.setText("Mostrar consola" if on else "Ocultar consola")
        ))

        left.addWidget(toggle_console)
        left.addWidget(self.out, 0)  # sin stretch para respetar el máximo de altura

        # Right: links + copiers
        right = QVBoxLayout(); right.setSpacing(8)
        right.addWidget(self._hlabel("Accesos"))
        for lk in proc.links:
            btn = QPushButton(f"🔗 {lk.title}")
            btn.setObjectName("LinkButton")
            btn.clicked.connect(lambda _=None, t=lk.target: self._open(t))
            right.addWidget(btn)

        if getattr(proc, "copiers", None):
            right.addWidget(self._hlabel("Copiadores"))
            for cp in proc.copiers:
                btn = QPushButton(f"📥 {cp.title}")
                btn.clicked.connect(lambda _=None, x=cp: self._runner_copy(x))
                right.addWidget(btn)

        if getattr(proc, "scripts", None):
            right.addWidget(self._hlabel("Scripts"))
            for s in proc.scripts:
                right.addWidget(self._script_row(s))

        right.addStretch()

        root.addLayout(left, 2)
        root.addLayout(right, 1)

    def _save_description(self):
        # capture HTML so bold and indentation are preserved
        html = self.desc.toHtml()
        self.proc.description = html  # actualizar el modelo en memoria

        # call optional callback to persist change
        if self.on_save_proc:
            self.on_save_proc(self.proc)

        if self.statusBar():
            self.statusBar().showMessage("Descripción guardada", 2000)

    def _toggle_bold(self, checked: bool = False):
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
        if hasattr(self, 'btn_bold'):
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
        if hasattr(self, 'size_selector'):
            self.size_selector.setCurrentText(str(int(size)))

    def _update_format_buttons(self):
        """Keep toolbar buttons in sync with current cursor format."""
        fmt = self.desc.currentCharFormat()
        if hasattr(self, 'btn_bold'):
            self.btn_bold.setChecked(fmt.fontWeight() == QFont.Bold)
        if hasattr(self, 'size_selector'):
            pt = fmt.fontPointSize() or self.desc.fontPointSize()
            if pt:
                self.size_selector.setCurrentText(str(int(pt)))

        # Si te pasaron un callback de guardado, úsalo
        if self.on_save_proc:
            self.on_save_proc(self.proc)

        # Feedback visual rápido (opcional)
        if self.statusBar():
            self.statusBar().showMessage("Descripción guardada", 2000)

    def _hlabel(self, text) -> QLabel:
        lbl = QLabel(text); lbl.setStyleSheet("color:#cfd6d6; font-weight:700;")
        return lbl

    def _script_row(self, s: "ScriptItem") -> QWidget:
        w = QFrame(); h = QVBoxLayout(w) if False else QHBoxLayout(w)
        h.setContentsMargins(0,0,0,0); h.setSpacing(6)
        lbl = QLabel(f"{Path(s.path).name}  {s.args}".strip()); lbl.setToolTip(s.path)
        btn = QPushButton("▶️ Run"); btn.setObjectName("Run")
        btn.clicked.connect(lambda: self._run_script(s))
        h.addWidget(lbl, 1); h.addWidget(btn)
        return w

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
                text=True
            )
        except Exception as e:
            QMessageBox.critical(self, "Run", str(e))
            return

        self.out.append(f"$ {' '.join(cmd)}")

        def _collect():
            try:
                out, _ = proc.communicate()
            except Exception as e:
                out = f"[error] {e}"
            self.out.append(out or "(sin salida)")

        QTimer.singleShot(10, _collect)

    def _open(self, target: str):
        try:
            if target.lower().startswith(("http://","https://")):
                webbrowser.open(target)
            else:
                os.startfile(target)
        except Exception as e:
            QMessageBox.warning(self, "Abrir", str(e))

    def _runner_copy(self, cp: "CopierItem"):
        target_dir = Path(cp.target_dir).expanduser()
        if not target_dir:
            QMessageBox.warning(self, "Copiar", "Este copiador no tiene carpeta destino.")
            return
        target_dir.mkdir(parents=True, exist_ok=True)
        history_dir = Path(cp.history_dir).expanduser() if cp.history_dir else None
        if history_dir:
            history_dir.mkdir(parents=True, exist_ok=True)

        filt = f"{cp.pattern};;Todos (*.*)" if cp.pattern else "Todos (*.*)"
        file_path, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo a copiar", str(Path.home()), filt)
        if not file_path:
            return

        try:
            import shutil
            from datetime import datetime
            if history_dir:
                for archivo in target_dir.glob(cp.pattern or "*.*"):
                    destino = history_dir / archivo.name
                    if destino.exists():
                        base, ext = os.path.splitext(archivo.name)
                        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                        destino = history_dir / f"{base}_{ts}{ext}"
                    shutil.move(str(archivo), str(destino))
            shutil.copy2(file_path, target_dir / Path(file_path).name)
            QMessageBox.information(self, "Copiar", "Archivo movido a histórico (si aplica) y copiado al destino ✅")
        except Exception as e:
            QMessageBox.critical(self, "Copiar", f"Error: {e}")