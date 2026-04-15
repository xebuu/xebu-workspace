from __future__ import annotations

import datetime
import sys

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.core.categories import (
    CATEGORY_DEFINITIONS,
    DEFAULT_TASK_CATEGORY,
    category_label,
    normalize_category,
)
from app.database.archived_tasks_repository import ArchivedTasksRepository
from app.database.tasks_repository import TasksRepository


class _TaskRow(QFrame):
    def __init__(self, task: dict, on_toggle, on_delete, on_archive, parent=None):
        super().__init__(parent)
        self.task = task
        self.on_toggle = on_toggle
        self.on_delete = on_delete
        self.on_archive = on_archive

        self.setObjectName("TaskRow")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(8)

        self.lbl = QLabel(self._format_text(task))
        self.lbl.setObjectName("TaskLabel")
        self.lbl.setWordWrap(True)

        is_done = task.get("completado", False)
        toggle_text = "↩️" if is_done else "✔"
        self.btn_toggle = QPushButton(toggle_text)
        self.btn_toggle.setObjectName("BtnOk")
        btn_delete = QPushButton("🗑️")
        btn_delete.setObjectName("BtnDel")
        btn_archive = QPushButton("🗃️")
        btn_archive.setObjectName("BtnArc")

        self.btn_toggle.setFixedWidth(40)
        btn_delete.setFixedWidth(40)
        btn_archive.setFixedWidth(40)

        self.btn_toggle.clicked.connect(lambda: self.on_toggle(task))
        btn_delete.clicked.connect(lambda: self.on_delete(task))
        btn_archive.clicked.connect(lambda: self.on_archive(task))

        lay.addWidget(self.lbl, 1)
        lay.addWidget(self.btn_toggle)
        lay.addWidget(btn_delete)
        lay.addWidget(btn_archive)

    def update_toggle_button(self):
        is_done = self.task.get("completado", False)
        self.btn_toggle.setText("↺" if is_done else "✔")
        self.lbl.setText(self._format_text(self.task))

    def _format_text(self, task: dict) -> str:
        texto = task.get("tarea", "")
        done = task.get("completado", False)
        diaria = task.get("diaria", False)
        prioridad = (task.get("prioridad") or "media").lower()
        category = normalize_category(task.get("category"), DEFAULT_TASK_CATEGORY)
        deadline = (task.get("deadline") or "").strip()

        estado = "✅" if done else "⏳"
        diaria_txt = " (diaria)" if diaria else ""
        category_txt = f" [{category_label(category)}]"
        if prioridad == "alta":
            icono = "⚪⚪⚪"
        elif prioridad == "baja":
            icono = "⚪"
        else:
            icono = "⚪⚪"

        dias_restantes = ""
        if deadline and not done and not diaria:
            try:
                fecha_limite = datetime.datetime.strptime(deadline, "%Y-%m-%d").date()
                diff = (fecha_limite - datetime.date.today()).days
                if diff >= 0:
                    dias_restantes = f" ({diff} días restantes)"
                else:
                    dias_restantes = f" (⚠ vencida hace {abs(diff)} días)"
            except ValueError:
                dias_restantes = " (fecha inválida)"

        return f"{estado} {texto}{dias_restantes}{diaria_txt}{category_txt} {icono}"


class TasksWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📋 Gestor de Tareas")
        self.resize(940, 600)

        self.tasks_repo = TasksRepository()
        self.arch_repo = ArchivedTasksRepository()

        self.tasks = self.tasks_repo.list_all()
        self.tasks_repo.reset_daily_if_needed(self.tasks)
        self.task_widgets = {}

        central = QWidget(self)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        top = QHBoxLayout()
        top.setSpacing(10)

        self.edt_new = QLineEdit()
        self.edt_new.setPlaceholderText("Escribe una nueva tarea")
        self.chk_daily = QCheckBox("Tarea diaria 🕓")
        self.edt_deadline = QDateEdit()
        self.edt_deadline.setDisplayFormat("yyyy-MM-dd")
        self.edt_deadline.setCalendarPopup(True)
        self.edt_deadline.setDate(QDate.currentDate())
        self.cmb_prio = QComboBox()
        self.cmb_prio.addItems(["alta", "media", "baja"])
        self.cmb_prio.setCurrentText("media")
        self.cmb_category = QComboBox()
        for key in CATEGORY_DEFINITIONS:
            self.cmb_category.addItem(category_label(key), key)
        self.cmb_category.setCurrentIndex(0)

        btn_add = QPushButton("+ Agregar tarea")
        btn_add.clicked.connect(self._add_task)

        top.addWidget(self.edt_new, 2)
        top.addWidget(self.chk_daily)
        top.addWidget(self.edt_deadline)
        top.addWidget(self.cmb_prio)
        top.addWidget(self.cmb_category)
        top.addWidget(btn_add)
        root.addLayout(top)

        cols = QHBoxLayout()
        cols.setSpacing(12)
        self._make_columns(cols)
        root.addLayout(cols, 1)

        act_add = QAction(self)
        act_add.setShortcut(QKeySequence(Qt.CTRL | Qt.Key_Return))
        act_add.triggered.connect(self._add_task)
        self.addAction(act_add)

        self._render()

    def _make_columns(self, container_layout: QHBoxLayout):
        self.scr_pending = QScrollArea()
        self.scr_pending.setWidgetResizable(True)
        self.wrap_pending = QWidget()
        self.v_pending = QVBoxLayout(self.wrap_pending)
        self.v_pending.setContentsMargins(10, 10, 10, 10)
        self.v_pending.setSpacing(8)
        self.scr_pending.setWidget(self.wrap_pending)

        self.scr_done = QScrollArea()
        self.scr_done.setWidgetResizable(True)
        self.wrap_done = QWidget()
        self.v_done = QVBoxLayout(self.wrap_done)
        self.v_done.setContentsMargins(10, 10, 10, 10)
        self.v_done.setSpacing(8)
        self.scr_done.setWidget(self.wrap_done)

        left = QVBoxLayout()
        left.addWidget(QLabel("⏳ Tareas Pendientes"))
        left.addWidget(self.scr_pending, 1)

        right = QVBoxLayout()
        right.addWidget(QLabel("✅ Tareas Completadas"))
        right.addWidget(self.scr_done, 1)

        container_layout.addLayout(left, 1)
        container_layout.addLayout(right, 1)

    def _add_task(self):
        text = self.edt_new.text().strip()
        deadline_str = self.edt_deadline.date().toString("yyyy-MM-dd")
        if not text:
            return

        new_task = {
            "tarea": text,
            "completado": False,
            "diaria": bool(self.chk_daily.isChecked()),
            "ultima_actualizacion": str(datetime.date.today()),
            "deadline": deadline_str,
            "prioridad": (self.cmb_prio.currentText() or "media").lower(),
            "category": self.cmb_category.currentData() or DEFAULT_TASK_CATEGORY,
        }
        self.tasks.append(new_task)
        self.tasks_repo.save_all(self.tasks)

        row = _TaskRow(
            new_task,
            on_toggle=self._toggle_task,
            on_delete=self._delete_task,
            on_archive=self._archive_task,
        )
        self.task_widgets[id(new_task)] = row
        stretch_index = self.v_pending.count() - 1
        self.v_pending.insertWidget(stretch_index, row)

        self.edt_new.clear()
        self.edt_deadline.setDate(QDate.currentDate())
        self.cmb_prio.setCurrentText("media")
        self.cmb_category.setCurrentIndex(0)
        self.chk_daily.setChecked(False)

    def _toggle_task(self, task: dict):
        task["completado"] = not task.get("completado", False)
        self.tasks_repo.save_all(self.tasks)

        task_id = id(task)
        if task_id in self.task_widgets:
            row = self.task_widgets[task_id]
            row.update_toggle_button()
            if task.get("completado", False):
                self.v_pending.removeWidget(row)
                stretch_index = self.v_done.count() - 1
                self.v_done.insertWidget(stretch_index, row)
            else:
                self.v_done.removeWidget(row)
                stretch_index = self.v_pending.count() - 1
                self.v_pending.insertWidget(stretch_index, row)

    def _delete_task(self, task: dict):
        task_id = id(task)
        if task_id in self.task_widgets:
            row = self.task_widgets[task_id]
            if task.get("completado", False):
                self.v_done.removeWidget(row)
            else:
                self.v_pending.removeWidget(row)
            row.setParent(None)
            del self.task_widgets[task_id]

        self.tasks = [t for t in self.tasks if t is not task]
        self.tasks_repo.save_all(self.tasks)

    def _archive_task(self, task: dict):
        ok, err = self.arch_repo.append_task(task)
        if not ok:
            QMessageBox.warning(self, "Archivar", f"No se pudo escribir CSV:\n{err}")
            return
        self._delete_task(task)

    def _render(self):
        def clear_layout(vbox: QVBoxLayout):
            for i in reversed(range(vbox.count())):
                w = vbox.itemAt(i).widget()
                if w:
                    w.setParent(None)

        clear_layout(self.v_pending)
        clear_layout(self.v_done)
        self.task_widgets.clear()

        for task in self.tasks:
            row = _TaskRow(
                task,
                on_toggle=self._toggle_task,
                on_delete=self._delete_task,
                on_archive=self._archive_task,
            )
            self.task_widgets[id(task)] = row
            if task.get("completado", False):
                self.v_done.addWidget(row)
            else:
                self.v_pending.addWidget(row)

        self.v_pending.addStretch(1)
        self.v_done.addStretch(1)


def run():
    app = QApplication(sys.argv)
    window = TasksWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
