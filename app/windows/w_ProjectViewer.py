# w_ProjectViewer.py
from __future__ import annotations
import sys, os,  subprocess, webbrowser
from pathlib import Path

from PySide6.QtCore import  QTimer
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QTextEdit, QFileDialog, QMessageBox)

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
        root = QHBoxLayout(central); root.setContentsMargins(12,12,12,12); root.setSpacing(10)

        # ==== Left: Description + scripts + output ====
        left = QVBoxLayout(); left.setSpacing(8)
        title = QLabel(proc.name); title.setObjectName("RunTitle")

        # ===== Left: botones para edición de texto ==========

        TextEditHeader = QHBoxLayout()
        btn_save = QPushButton("💾 Guardar")
        btn_save.clicked.connect(self._save_description)
        TextEditHeader.addWidget(btn_save)
        TextEditHeader.addStretch(8)

        # --- Descripción con scroll (cambio mínimo) ---
        self.desc = QTextEdit()
        self.desc.setPlainText(proc.description)
        self.desc.setContentsMargins(0,0,0,0)
        self.desc.setFixedHeight(700)

        scrollDesc = QScrollArea()
        scrollDesc.setWidgetResizable(True)
        scrollDesc.setFrameShape(QFrame.NoFrame)
        scrollDesc.setMaximumHeight(500)  # ajusta si quieres
        scrollDesc.setWidget(self.desc)

        left.addWidget(title)
        left.addLayout(TextEditHeader)
        left.addWidget(scrollDesc)

        for s in proc.scripts:
            left.addWidget(self._script_row(s))

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
            btn.clicked.connect(lambda _=None, t=lk.target: self._open(t))
            right.addWidget(btn)

        if getattr(proc, "copiers", None):
            right.addWidget(self._hlabel("Copiadores"))
            for cp in proc.copiers:
                btn = QPushButton(f"📥 {cp.title}")
                btn.clicked.connect(lambda _=None, x=cp: self._runner_copy(x))
                right.addWidget(btn)

        right.addStretch()

        root.addLayout(left, 2)
        root.addLayout(right, 1)

    def _save_description(self):
        text = self.desc.toPlainText()
        self.proc.description = text  # actualizar el modelo en memoria

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