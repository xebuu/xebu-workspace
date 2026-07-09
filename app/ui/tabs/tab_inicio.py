from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.core.task_helpers import (
    dashboard_sections,
    delete_task_by_id,
    normalize_priority,
    parse_quick_task,
    today_iso,
)
from app.database.tasks_repository import TasksRepository


def _task_meta(task: dict) -> str:
    parts: list[str] = []
    deadline = str(task.get("deadline") or "").strip()
    if deadline:
        parts.append(deadline)
    if task.get("diaria"):
        parts.append("diaria")
    priority = normalize_priority(task.get("prioridad"))
    if priority != "media":
        parts.append(f"prioridad {priority}")
    return " | ".join(parts)


class _DashboardTaskRow(QFrame):
    def __init__(self, task: dict, on_done, on_delete, parent=None):
        super().__init__(parent)
        self.task = task
        self.setObjectName("DashboardTaskRow")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        text_col = QVBoxLayout()
        title = QLabel(str(task.get("tarea") or "Sin titulo"))
        title.setWordWrap(True)
        title.setObjectName("TaskLabel")
        meta = QLabel(_task_meta(task))
        meta.setObjectName("CardMeta")
        meta.setVisible(bool(meta.text()))
        text_col.addWidget(title)
        text_col.addWidget(meta)

        btn_done = QPushButton("Hecho")
        btn_done.setFixedWidth(72)
        btn_done.clicked.connect(lambda: on_done(task))
        btn_delete = QPushButton("Borrar")
        btn_delete.setFixedWidth(72)
        btn_delete.clicked.connect(lambda: on_delete(task))

        layout.addLayout(text_col, 1)
        layout.addWidget(btn_done)
        layout.addWidget(btn_delete)


class _DashboardSection(QFrame):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("DashboardSection")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        self.title = QLabel(title)
        self.title.setObjectName("SectionHeading")
        self.body = QVBoxLayout()
        self.body.setSpacing(8)
        layout.addWidget(self.title)
        layout.addLayout(self.body)

    def clear(self) -> None:
        while self.body.count():
            item = self.body.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def set_tasks(self, tasks: list[dict], on_done, on_delete) -> None:
        self.clear()
        if not tasks:
            empty = QLabel("Nada pendiente aqui.")
            empty.setObjectName("CardMeta")
            self.body.addWidget(empty)
            return
        for task in tasks:
            self.body.addWidget(_DashboardTaskRow(task, on_done, on_delete, self))


class TodayDashboardTab(QWidget):
    tasks_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.repo = TasksRepository()
        self.tasks: list[dict] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        header = QVBoxLayout()
        title = QLabel("Inicio")
        title.setObjectName("Title")
        subtitle = QLabel("Lo importante para hoy, sin buscar entre ventanas.")
        subtitle.setObjectName("CardMeta")
        header.addWidget(title)
        header.addWidget(subtitle)
        root.addLayout(header)

        quick = QFrame()
        quick.setObjectName("QuickAddFrame")
        quick_layout = QHBoxLayout(quick)
        quick_layout.setContentsMargins(12, 12, 12, 12)
        quick_layout.setSpacing(8)
        self.quick_input = QLineEdit()
        self.quick_input.setPlaceholderText(
            "Agregar rapido: pagar renta manana alta"
        )
        self.quick_input.returnPressed.connect(self._add_quick_task)
        self.quick_btn = QPushButton("Agregar")
        self.quick_btn.clicked.connect(self._add_quick_task)
        quick_layout.addWidget(self.quick_input, 1)
        quick_layout.addWidget(self.quick_btn)
        root.addWidget(quick)

        self.summary = QLabel("")
        self.summary.setObjectName("CardMeta")
        root.addWidget(self.summary)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        self.grid = QGridLayout(content)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(12)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        self.sections = {
            "overdue": _DashboardSection("Vencidas"),
            "today": _DashboardSection("Para hoy"),
            "high_priority": _DashboardSection("Alta prioridad"),
            "upcoming": _DashboardSection("Proximos 7 dias"),
            "inbox": _DashboardSection("Sin fecha"),
        }
        positions = {
            "overdue": (0, 0),
            "today": (0, 1),
            "high_priority": (1, 0),
            "upcoming": (1, 1),
            "inbox": (2, 0),
        }
        for key, widget in self.sections.items():
            row, col = positions[key]
            span = 2 if key == "inbox" else 1
            self.grid.addWidget(widget, row, col, 1, span)

        self.refresh()

    def refresh(self) -> None:
        self.tasks = self.repo.list_all()
        self.repo.reset_daily_if_needed(self.tasks)
        sections = dashboard_sections(self.tasks)
        total_attention = len(
            {
                task.get("id")
                for key in ("overdue", "today", "high_priority")
                for task in sections[key]
                if task.get("id")
            }
        )
        self.summary.setText(
            f"{total_attention} tareas piden atencion hoy | {len(self.tasks)} tareas totales"
        )
        for key, section in self.sections.items():
            section.set_tasks(sections[key], self._complete_task, self._delete_task)

    def _add_quick_task(self) -> None:
        task = parse_quick_task(
            self.quick_input.text(),
            default_deadline=today_iso(date.today()),
        )
        if task is None:
            return
        self.tasks.append(task)
        self.repo.save_all(self.tasks)
        self.quick_input.clear()
        self.refresh()
        self.tasks_changed.emit()

    def _complete_task(self, task: dict) -> None:
        for item in self.tasks:
            if item.get("id") == task.get("id"):
                item["completado"] = True
                item["ultima_actualizacion"] = today_iso(date.today())
                break
        self.repo.save_all(self.tasks)
        self.refresh()
        self.tasks_changed.emit()

    def _delete_task(self, task: dict) -> None:
        if delete_task_by_id(self.tasks, task):
            self.repo.save_all(self.tasks)
            self.refresh()
            self.tasks_changed.emit()
