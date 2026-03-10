# app/main.py
import sys, webbrowser, os, uuid
from time import perf_counter
from pathlib import Path

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer, QSize
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QStackedWidget, QSizePolicy, QFrame, QToolBar,  QMenu,  QSizePolicy,
    QLineEdit, QDialogButtonBox, QLabel,QMessageBox,QFileDialog, QDialog, QToolButton,
    QInputDialog)

from PySide6.QtGui import QAction, QKeySequence, QShortcut

# Vista interna
from app.tabs.tab_projects import ProjectManagerTab
from app.tabs.tab_configuracion import ConfiguracionTab
from app.windows.w_bitacora import BitacoraWindow
from app.windows.w_tasks import TasksWindow
from app.utility.helpers import show_loading_then
from app.utility.paths import assets_path,assets_path_yellow
from app.utility.database import MainWindowToolbarRepo

def _open_target(target: str):
    try:
        if target.lower().startswith(("http://", "https://")):
            webbrowser.open(target)
        else:
            os.startfile(target)
    except Exception as e:
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.warning(None, "Abrir", str(e))

def hline() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Sunken)
    return line

class AddToolbarShortcutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Agregar acceso a la toolbar")
        self.setModal(True)
        self.resize(420, 180)

        root = QVBoxLayout(self)
        form = QVBoxLayout(); root.addLayout(form)

        self.edt_title = QLineEdit(); self.edt_title.setPlaceholderText("Título (p.ej. Directorio Bimbo)")
        form.addWidget(QLabel("Título")); form.addWidget(self.edt_title)

        row = QHBoxLayout()
        self.edt_target = QLineEdit(); self.edt_target.setPlaceholderText("URL o ruta")
        btn = QPushButton("Buscar…"); btn.clicked.connect(self._browse_any)
        row.addWidget(self.edt_target, 1); row.addWidget(btn)
        form.addWidget(QLabel("Destino")); form.addLayout(row)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._on_accept); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _browse_any(self):
        path, _ = QFileDialog.getOpenFileName(self, "Elegir archivo (o Cancela para carpeta)", str(Path.home()))
        if path:
            self.edt_target.setText(path); return
        folder = QFileDialog.getExistingDirectory(self, "Elegir carpeta", str(Path.home()))
        if folder:
            self.edt_target.setText(folder)

    def _on_accept(self):
        if not self.edt_title.text().strip():
            QMessageBox.warning(self, "Acceso", "Escribe un título."); return
        if not self.edt_target.text().strip():
            QMessageBox.warning(self, "Acceso", "Escribe una URL o ruta."); return
        self.accept()

    def result_item(self) -> dict:
        return {
            "id": str(uuid.uuid4()),
            "title": self.edt_title.text().strip(),
            "target": self.edt_target.text().strip(),
        }


# ========= Sidebar =========
class SideBar(QWidget):
    def __init__(self, on_tab_selected, width_expanded=220, width_collapsed=56):
        super().__init__()
        self.on_tab_selected = on_tab_selected
        self.width_expanded = width_expanded
        self.width_collapsed = width_collapsed

        self.setFixedWidth(self.width_expanded)
        self.setObjectName("SideBar")

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self.toggle_btn = QPushButton("≡  Menu")
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.toggled.connect(self.toggle_menu)
        self.toggle_btn.setObjectName("ToggleBtn")
        root.addWidget(self.toggle_btn)
        root.addWidget(hline())

        self.buttons = []
        tabs = [
            ("📝  Proyectos", 0),
            ("🛰️  Coming Soon", 1),
            ("⚙️  Configuración", 2),
        ]
        for text, idx in tabs:
            btn = QPushButton(text)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setCheckable(True)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.clicked.connect(lambda _checked=False, i=idx: self._select(i))
            self.buttons.append(btn)
            root.addWidget(btn)

        root.addStretch()

        self._anim = QPropertyAnimation(self, b"minimumWidth")
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)
        self._anim.finished.connect(lambda: self.setFixedWidth(self.minimumWidth()))

        self._select(0)

    def _select(self, index: int):
        for i, b in enumerate(self.buttons):
            b.setChecked(i == index)
        self.on_tab_selected(index)

    def toggle_menu(self, collapsed: bool):
        target = self.width_collapsed if collapsed else self.width_expanded
        self._anim.stop()
        self._anim.setStartValue(self.width())
        self._anim.setEndValue(target)
        self._anim.start()


# ========= Main Window =========
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("XebuWorkspace 2.0.0")
        self.resize(1200, 800)

        root = QWidget()
        self.setCentralWidget(root)
        hbox = QHBoxLayout(root)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(0)

        self.stack = QStackedWidget()
        self.pages = [None, None, None]  

        self.sidebar = SideBar(on_tab_selected=self.show_tab)
        hbox.addWidget(self.sidebar)
        hbox.addWidget(self.stack, 1)

        self._build_menubar()
        self._build_toolbar()

        self.statusBar().showMessage("Ready")

        self.show_tab(0)

        QShortcut(QKeySequence("Ctrl+R"), self, activated=self.apply_style)

        self.apply_style()

    def show_tab(self, idx: int):
        t0 = perf_counter()
        if self.pages[idx] is None:
            if idx == 0:
                page = ProjectManagerTab()
            elif idx == 1:
                page = self.tab_temporal("Coming Soon")
            elif idx == 2:
                page = ConfiguracionTab()
            else:
                raise IndexError("Índice de tab inválido")

            self.pages[idx] = page
            self.stack.addWidget(page)

        self.stack.setCurrentWidget(self.pages[idx])
        elapsed = (perf_counter() - t0) * 1000
        self.statusBar().showMessage(f"Tab {idx} listo • render: {elapsed:.1f} ms")
        QTimer.singleShot(2000, self.statusBar().clearMessage)

    def _build_menubar(self):
        mb = self.menuBar()

        # --- Menú Archivo ---
        menu_file = mb.addMenu("Archivo")
        act_exit = QAction("Salir", self)
        act_exit.triggered.connect(self.close)
        menu_file.addSeparator()
        menu_file.addAction(act_exit)

        style_file = mb.addMenu("Estilo")
        act_changeStyleN = QAction("Normal",self)
        act_changeStyleN.triggered.connect(self.apply_style)
        act_changeStyleY = QAction("Amarillo",self)
        act_changeStyleY.triggered.connect(self.apply_style_yellow)
        style_file.addSeparator()
        style_file.addAction(act_changeStyleN)
        style_file.addAction(act_changeStyleY)

    def _build_toolbar(self):
        tb = QToolBar("Main")
        tb.setIconSize(QSize(18, 18))
        tb.setMovable(True)
        tb.setFloatable(True)

        # ---- carga items existentes --
        self.toolbar_repo = MainWindowToolbarRepo()
        self._toolbar_db = self.toolbar_repo.load()
        self._toolbar_buttons: dict[str, QAction] = {}  # id -> action

        # Botón  (agregar acceso)
        act_add = QAction(" Agregar", self)
        act_add.triggered.connect(self._on_toolbar_add_item)
        tb.addAction(act_add)

        # separador expansible para empujar a la derecha el resto (opcional)
        spacer = QWidget(); spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tb.addWidget(spacer)

            # Botón Bitácora (nuevo)
        act_bitacora = QAction("Bitácora", self)
        act_bitacora.triggered.connect(self._open_bitacora)
        tb.addAction(act_bitacora)

        # Botón para abrir Tasks
        act_tasks = QAction("Tareas", self)
        act_tasks.triggered.connect(self._open_tasks)
        tb.addAction(act_tasks)

        # Botón Ayuda (ejemplo)
        act_help = QAction("Notificaciones", self)
        act_help.triggered.connect(self._open_alerts)
        tb.addAction(act_help)

        # inserta accesos (los agregamos a la izquierda del spacer)
        # Para que queden antes del spacer, añadimos en posición 1 (después del botón ➕)
        for item in self._toolbar_db.get("items", []):
            self._toolbar_add_action_from_item(tb, item, insert_before_spacer=True)

        # colócalo arriba (también puedes usar Left/Right/Bottom)
        self.addToolBar(Qt.TopToolBarArea, tb)
        self.toolbar = tb  # opcional: guarda la ref

    def _open_bitacora(self):
        if not hasattr(self, "_bitacora_win") or self._bitacora_win is None:
            self._bitacora_win = BitacoraWindow(self)
            # cuando se cierre, olvida el puntero
            self._bitacora_win.destroyed.connect(lambda: setattr(self, "_bitacora_win", None))
        self._bitacora_win.show()
        self._bitacora_win.raise_()
        self._bitacora_win.activateWindow()

    def _toolbar_add_action_from_item(self, tb: QToolBar, item: dict, insert_before_spacer: bool = False):
        """
        Crea una QAction para un item {'id','title','target'} y la inserta en la toolbar.
        Con menú contextual (clic derecho) para eliminar.
        """
        act = QAction(item["title"], self)
        act.setData(item["id"])
        act.triggered.connect(lambda _=None, t=item["target"]: _open_target(t))

        # Para menú contextual (el QToolBar usa QToolButton interno)
        btn = QToolButton()
        btn.setDefaultAction(act)
        btn.setPopupMode(QToolButton.InstantPopup)
        btn.setContextMenuPolicy(Qt.CustomContextMenu)
        btn.customContextMenuRequested.connect(lambda pos, bid=item["id"]: self._toolbar_item_context_menu(bid, btn))

        # Inserta la acción como widget (así podemos tener menú contextual)
        if insert_before_spacer:
            # Insertarlo en posición 1 (después del botón ➕, antes del spacer)
            tb.insertWidget(tb.actions()[1] if len(tb.actions()) > 1 else None, btn)
        else:
            tb.addWidget(btn)

        self._toolbar_buttons[item["id"]] = act


    def _on_toolbar_add_item(self):
        dlg = AddToolbarShortcutDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return
        item = dlg.result_item()

        # persiste
        db = self._toolbar_db or self.toolbar_repo.load()
        db["items"].append(item)
        self.toolbar_repo.save(db)
        self._toolbar_db = db

        # crea botón en runtime (antes del spacer)
        self._toolbar_add_action_from_item(self.toolbar, item, insert_before_spacer=True)
        

    def _toolbar_item_context_menu(self, item_id: str, btn: QToolButton):
        menu = QMenu(self)
        act_edit = menu.addAction("🛠️ Editar")
        act_del = menu.addAction("🗑️ Borrar")
        act = menu.exec_(btn.mapToGlobal(btn.rect().bottomLeft()))
        if act == act_del:
            self._toolbar_remove_item(item_id)
        elif act == act_edit:
            self._toolbar_edit_item(item_id)
    
    def _toolbar_edit_item(self, item_id: str):
        # 1) Cargar DB (caché o disco)
        db = self._toolbar_db or self.toolbar_repo.load()
        items = db.get("items",[])

        # 2) Buscar item
        itemSelected = None
        for item in items:
            if item.get("id") == item_id:
                itemSelected = item
                break
        if itemSelected is None:
            return

        curr_title  = itemSelected.get("title", "")
        curr_target = itemSelected.get("target", "")

        # 2) Pedir nuevo título
        new_title, ok = QInputDialog.getText(
            self,
            "Editar botón de toolbar",
            "Título del botón:",
            QLineEdit.Normal,
            curr_title)
        if not ok or not new_title.strip():
            return

        # 3) Pedir nuevo destino
        new_target, ok = QInputDialog.getText(
            self,
            "Editar botón de toolbar",
            "Destino (ruta/URL/comando):",
            QLineEdit.Normal,
            curr_target)
        if not ok or not new_target.strip():
            return

        new_title  = new_title.strip()
        new_target = new_target.strip()

        # 4) Actualizar el dict en memoria
        itemSelected["title"]  = new_title
        itemSelected["target"] = new_target

        # 5) Guardar JSON (ajusta al nombre de tu función de guardado)
        self._toolbar_db = db
        self.toolbar_repo.save(db)
        
        # 6) Actualizar la QAction ya existente en la barra
        act = self._toolbar_buttons.get(item_id)
        if act is not None:
            act.setText(new_title)
            # desconectar el slot anterior y volver a conectar con el nuevo target
            try:
                act.triggered.disconnect()
            except TypeError:
                # puede no tener conexiones previas
                pass
            act.triggered.connect(lambda _=None, t=new_target: _open_target(t))

    def _open_tasks(self):
        if not hasattr(self, "_tasks_win") or self._tasks_win is None:
            self._tasks_win = TasksWindow(self)
            self._tasks_win.destroyed.connect(lambda: setattr(self, "_tasks_win", None))
        self._tasks_win.show()
        self._tasks_win.raise_()
        self._tasks_win.activateWindow()

    def _toolbar_remove_item(self, item_id: str):
        # confirma
        if QMessageBox.question(self, "Quitar acceso", "¿Eliminar este acceso de la toolbar?",
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes:
            return

        # quita de la DB
        db = self._toolbar_db or self.toolbar_repo.load()
        db["items"] = [it for it in db.get("items", []) if it.get("id") != item_id]
        self.toolbar_repo.save(db)
        self._toolbar_db = db

        # reconstruir toolbar (más simple/robusto que buscar y eliminar widget por widget)
        self.removeToolBar(self.toolbar)
        self._build_toolbar()


    def _refresh_current_tab(self):
        # Llama a un método refresh() si la página actual lo implementa
        w = self.stack.currentWidget()
        if hasattr(w, "refresh"):
            try:
                w.refresh()
                self.statusBar().showMessage("Refrescado", 1500)
            except Exception as e:
                self.statusBar().showMessage(f"Error al refrescar: {e}", 2500)
        else:
            self.statusBar().showMessage("Nada que refrescar aquí", 1500)

    def _open_alerts(self):
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(self, "Acerca de", "XebuWorkspace 1.0.0\n — Desktop Productivity")

    def apply_style(self):
        with open(assets_path, "r", encoding="utf-8") as f:
            self.setStyleSheet(f.read())
        return

    def apply_style_yellow(self):
        with open(assets_path_yellow, "r", encoding="utf-8") as f:
            self.setStyleSheet(f.read())
        return
    
    def tab_temporal(self, title="Coming Soon"):
        w = QWidget()
        lay = QVBoxLayout(w)
        lbl = QLabel(f"{title}\n\nEsta sección está en desarrollo para la versión pública.")
        lbl.setAlignment(Qt.AlignCenter)
        lay.addStretch()
        lay.addWidget(lbl)
        lay.addStretch()
        return w


def build_main():
    return MainWindow()

def run():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    #show_loading_then(app,build_main, duration_ms=1500, text="CustomText")
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
