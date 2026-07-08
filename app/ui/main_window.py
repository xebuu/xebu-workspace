# app/main.py
import webbrowser
import sys
import uuid
from pathlib import Path
from time import perf_counter

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.core.task_helpers import attention_tasks
from app.ui.tabs.tab_calendar import CalendarTab
from app.ui.tabs.tab_configuracion import ConfiguracionTab
from app.ui.tabs.tab_inicio import TodayDashboardTab

# Vista interna
from app.ui.tabs.tab_projects import ProjectManagerTab
from app.database.toolbar_repository import ToolbarRepository
from app.core.helpers import open_resource_target
from app.core.paths import assets_path
from app.ui.widgets.overlay_sidebar import COLLAPSED_WIDTH, OverlaySidebar
from app.ui.windows.w_bitacora import BitacoraWindow
from app.ui.windows.w_notifications import NotificationDialog
from app.ui.windows.w_tasks import TasksWindow
from app.database.tasks_repository import TasksRepository


def _open_target(target: str):
    try:
        open_resource_target(target)
    except (OSError, webbrowser.Error) as e:
        QMessageBox.warning(None, "Abrir", str(e))


def hline() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setFrameShadow(QFrame.Sunken)
    return line


MAIN_NAV_ITEMS = [
    {"text": "Inicio", "page_key": "home"},
    {"text": "Proyectos", "page_key": "projects"},
    {"text": "Calendario", "page_key": "calendar"},
    {"text": "Configuracion", "page_key": "settings"},
]


class AddToolbarShortcutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Agregar acceso a la toolbar")
        self.setModal(True)
        self.resize(420, 180)

        root = QVBoxLayout(self)
        form = QVBoxLayout()
        root.addLayout(form)

        self.edt_title = QLineEdit()
        self.edt_title.setPlaceholderText("Título (p.ej. Directorio Bimbo)")
        form.addWidget(QLabel("Título"))
        form.addWidget(self.edt_title)

        row = QHBoxLayout()
        self.edt_target = QLineEdit()
        self.edt_target.setPlaceholderText("URL o ruta")
        btn = QPushButton("Buscar…")
        btn.clicked.connect(self._browse_any)
        row.addWidget(self.edt_target, 1)
        row.addWidget(btn)
        form.addWidget(QLabel("Destino"))
        form.addLayout(row)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _browse_any(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Elegir archivo (o Cancela para carpeta)", str(Path.home())
        )
        if path:
            self.edt_target.setText(path)
            return
        folder = QFileDialog.getExistingDirectory(
            self, "Elegir carpeta", str(Path.home())
        )
        if folder:
            self.edt_target.setText(folder)

    def _on_accept(self):
        if not self.edt_title.text().strip():
            QMessageBox.warning(self, "Acceso", "Escribe un título.")
            return
        if not self.edt_target.text().strip():
            QMessageBox.warning(self, "Acceso", "Escribe una URL o ruta.")
            return
        self.accept()

    def result_item(self) -> dict:
        return {
            "id": str(uuid.uuid4()),
            "title": self.edt_title.text().strip(),
            "target": self.edt_target.text().strip(),
        }


# ========= Main Window =========
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("XebuWorkspace 2.0.0")
        self.resize(1200, 800)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.central_widget.update_sidebar_geometry = self.update_sidebar_geometry

        content_layout = QVBoxLayout(self.central_widget)
        content_layout.setContentsMargins(COLLAPSED_WIDTH, 0, 0, 0)
        content_layout.setSpacing(0)

        self.stack = QStackedWidget()
        self.pages = [None, None, None, None]
        content_layout.addWidget(self.stack)

        self.sidebar = OverlaySidebar(
            navigation_items=MAIN_NAV_ITEMS,
            parent=self.central_widget,
        )
        self.sidebar.page_requested.connect(self._on_sidebar_page_requested)
        self._page_key_map = {
            "home": 0,
            "projects": 1,
            "calendar": 2,
            "settings": 3,
        }
        self._bitacora_win = None
        self._tasks_win = None
        self._notification_win = None
        self._toolbar_items: list[dict[str, str]] = []
        self.toolbar_repo = ToolbarRepository()
        self.tasks_repo = TasksRepository()

        self._build_menubar()
        self._build_toolbar()
        self._update_notification_badge()

        self.statusBar().showMessage("Ready")

        self.update_sidebar_geometry()
        self.show_tab(0)

        QShortcut(QKeySequence("Ctrl+R"), self, activated=self.apply_style)

        self.apply_style()

    def show_tab(self, idx: int):
        t0 = perf_counter()
        if self.pages[idx] is None:
            if idx == 0:
                page = TodayDashboardTab()
            elif idx == 1:
                page = ProjectManagerTab()
            elif idx == 2:
                page = CalendarTab()
            elif idx == 3:
                page = ConfiguracionTab()
            else:
                raise IndexError("Índice de tab inválido")

            self.pages[idx] = page
            self.stack.addWidget(page)
            self._wire_task_page(page)

        self.stack.setCurrentWidget(self.pages[idx])
        if hasattr(self.pages[idx], "refresh"):
            self.pages[idx].refresh()
        elapsed = (perf_counter() - t0) * 1000
        self.statusBar().showMessage(f"Tab {idx} listo • render: {elapsed:.1f} ms")
        QTimer.singleShot(2000, self.statusBar().clearMessage)

    def _wire_task_page(self, page) -> None:
        signal = getattr(page, "tasks_changed", None)
        if signal is not None:
            signal.connect(self._on_tasks_changed)

    def _on_tasks_changed(self) -> None:
        self._update_notification_badge()
        if self._notification_win is not None:
            self._notification_win.refresh()
        for page in self.pages:
            if page is None:
                continue
            refresh = getattr(page, "refresh", None)
            if callable(refresh):
                refresh()

    def _on_sidebar_page_requested(self, page_key: str) -> None:
        match_idx = self._page_key_map.get(page_key)
        if match_idx is None:
            return
        self.show_tab(match_idx)

    def update_sidebar_geometry(self) -> None:
        if not hasattr(self, "sidebar"):
            return

        sidebar = self.sidebar
        sidebar.setFixedHeight(self.central_widget.height())
        sidebar.move(0, 0)
        sidebar.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_sidebar_geometry()

    def _build_menubar(self):
        mb = self.menuBar()

        # --- Menú Archivo ---
        menu_file = mb.addMenu("Archivo")
        act_exit = QAction("Salir", self)
        act_exit.triggered.connect(self.close)
        menu_file.addSeparator()
        menu_file.addAction(act_exit)

    def _build_toolbar(self):
        tb = QToolBar("Main")
        tb.setIconSize(QSize(18, 18))
        tb.setMovable(True)
        tb.setFloatable(True)

        # ---- carga items existentes --
        self._toolbar_items = self.toolbar_repo.list_items()
        self._toolbar_buttons: dict[str, QAction] = {}  # id -> action

        # Botón  (agregar acceso)
        act_add = QAction(" Agregar", self)
        act_add.triggered.connect(self._on_toolbar_add_item)
        tb.addAction(act_add)

        # separador expansible para empujar a la derecha el resto (opcional)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
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
        self.act_notifications = QAction("Notificaciones", self)
        self.act_notifications.triggered.connect(self._open_notifications)
        tb.addAction(self.act_notifications)

        # inserta accesos (los agregamos a la izquierda del spacer)
        # Para que queden antes del spacer, añadimos en posición 1 (después del botón ➕)
        for item in self._toolbar_items:
            self._toolbar_add_action_from_item(tb, item, insert_before_spacer=True)

        # colócalo arriba (también puedes usar Left/Right/Bottom)
        self.addToolBar(Qt.TopToolBarArea, tb)
        self.toolbar = tb  # opcional: guarda la ref

    def _open_bitacora(self):
        if self._bitacora_win is None:
            self._bitacora_win = BitacoraWindow(self)
            # cuando se cierre, olvida el puntero
            self._bitacora_win.destroyed.connect(
                lambda: setattr(self, "_bitacora_win", None)
            )
        self._bitacora_win.show()
        self._bitacora_win.raise_()
        self._bitacora_win.activateWindow()

    def _toolbar_add_action_from_item(
        self, tb: QToolBar, item: dict, insert_before_spacer: bool = False
    ):
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
        btn.customContextMenuRequested.connect(
            lambda pos, bid=item["id"]: self._toolbar_item_context_menu(bid, btn)
        )

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
        new_item = self.toolbar_repo.insert_item(item)
        self._toolbar_items.append(new_item)

        # crea botón en runtime (antes del spacer)
        self._toolbar_add_action_from_item(
            self.toolbar, new_item, insert_before_spacer=True
        )

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
        items = self._toolbar_items

        # 2) Buscar item
        itemSelected = None
        for item in items:
            if item.get("id") == item_id:
                itemSelected = item
                break
        if itemSelected is None:
            return

        curr_title = itemSelected.get("title", "")
        curr_target = itemSelected.get("target", "")

        # 2) Pedir nuevo título
        new_title, ok = QInputDialog.getText(
            self,
            "Editar botón de toolbar",
            "Título del botón:",
            QLineEdit.Normal,
            curr_title,
        )
        if not ok or not new_title.strip():
            return

        # 3) Pedir nuevo destino
        new_target, ok = QInputDialog.getText(
            self,
            "Editar botón de toolbar",
            "Destino (ruta/URL/comando):",
            QLineEdit.Normal,
            curr_target,
        )
        if not ok or not new_target.strip():
            return

        new_title = new_title.strip()
        new_target = new_target.strip()

        # 5) Guardar cambios
        updated = self.toolbar_repo.update_item(
            item_id, title=new_title, target=new_target
        )
        if not updated:
            return

        # 4) Actualizar el dict en memoria
        itemSelected["title"] = new_title
        itemSelected["target"] = new_target

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
        if self._tasks_win is None:
            self._tasks_win = TasksWindow(self)
            self._tasks_win.tasks_changed.connect(self._on_tasks_changed)
            self._tasks_win.destroyed.connect(lambda: setattr(self, "_tasks_win", None))
        self._tasks_win.show()
        self._tasks_win.raise_()
        self._tasks_win.activateWindow()

    def _toolbar_remove_item(self, item_id: str):
        # confirma
        if (
            QMessageBox.question(
                self,
                "Quitar acceso",
                "¿Eliminar este acceso de la toolbar?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            != QMessageBox.Yes
        ):
            return

        # quita de la DB
        deleted = self.toolbar_repo.delete_item(item_id)
        if not deleted:
            return
        self._toolbar_items = [it for it in self._toolbar_items if it.get("id") != item_id]

        # reconstruir toolbar (más simple/robusto que buscar y eliminar widget por widget)
        self.removeToolBar(self.toolbar)
        self._build_toolbar()
        self._update_notification_badge()

    def _refresh_current_tab(self):
        # Llama a un método refresh() si la página actual lo implementa
        w = self.stack.currentWidget()
        if hasattr(w, "refresh"):
            try:
                w.refresh()
                self.statusBar().showMessage("Refrescado", 1500)
            except (AttributeError, ValueError, RuntimeError) as exc:
                self.statusBar().showMessage(f"Error al refrescar: {exc}", 2500)
        else:
            self.statusBar().showMessage("Nada que refrescar aquí", 1500)

    def _update_notification_badge(self) -> None:
        if not hasattr(self, "act_notifications"):
            return
        tasks = self.tasks_repo.list_all()
        self.tasks_repo.reset_daily_if_needed(tasks)
        count = len(attention_tasks(tasks))
        text = f"Notificaciones ({count})" if count else "Notificaciones"
        self.act_notifications.setText(text)

    def _open_notifications(self):
        if self._notification_win is None:
            self._notification_win = NotificationDialog(
                self,
                on_tasks_changed=self._on_tasks_changed,
            )
            self._notification_win.destroyed.connect(
                lambda: setattr(self, "_notification_win", None)
            )
        self._notification_win.refresh()
        self._notification_win.show()
        self._notification_win.raise_()
        self._notification_win.activateWindow()

    def _open_alerts(self):
        QMessageBox.information(
            self, "Acerca de", "XebuWorkspace 1.0.0\n — Desktop Productivity"
        )

    def apply_style(self):
        with open(assets_path, "r", encoding="utf-8") as f:
            self.setStyleSheet(f.read())
        return

    def tab_temporal(self, title="Coming Soon"):
        w = QWidget()
        lay = QVBoxLayout(w)
        lbl = QLabel(
            f"{title}\n\nEsta sección está en desarrollo para la versión pública."
        )
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
    # show_loading_then(app,build_main, duration_ms=1500, text="CustomText")
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
