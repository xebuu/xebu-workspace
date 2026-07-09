from __future__ import annotations

from datetime import date
from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.core.task_helpers import dashboard_sections, today_iso, update_task_by_id
from app.database.tasks_repository import TasksRepository


def _line(task: dict) -> str:
    deadline = str(task.get("deadline") or "").strip()
    suffix = f" | {deadline}" if deadline else ""
    return f"{task.get('tarea', 'Sin titulo')}{suffix}"


class NotificationDialog(QDialog):
    def __init__(
        self,
        parent=None,
        on_tasks_changed: Optional[Callable[[], None]] = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Notificaciones")
        self.resize(520, 520)
        self.repo = TasksRepository()
        self.tasks: list[dict] = []
        self.on_tasks_changed = on_tasks_changed

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        title = QLabel("Notificaciones")
        title.setObjectName("Title")
        root.addWidget(title)

        self.summary = QLabel("")
        self.summary.setObjectName("CardMeta")
        root.addWidget(self.summary)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        self.body = QVBoxLayout(content)
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(10)
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        self.refresh()

    def refresh(self) -> None:
        self.tasks = self.repo.list_all()
        self.repo.reset_daily_if_needed(self.tasks)
        while self.body.count():
            item = self.body.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        sections = dashboard_sections(self.tasks)
        unique_attention = {
            task.get("id")
            for key in ("overdue", "today", "high_priority")
            for task in sections[key]
            if task.get("id")
        }
        self.summary.setText(f"{len(unique_attention)} tareas necesitan atencion.")

        self._add_section("Vencidas", sections["overdue"])
        self._add_section("Para hoy", sections["today"])
        self._add_section("Alta prioridad", sections["high_priority"])
        self.body.addStretch(1)

    def _add_section(self, title: str, tasks: list[dict]) -> None:
        frame = QFrame()
        frame.setObjectName("NotificationSection")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        label = QLabel(f"{title} ({len(tasks)})")
        label.setObjectName("SectionHeading")
        layout.addWidget(label)

        if not tasks:
            empty = QLabel("Sin pendientes.")
            empty.setObjectName("CardMeta")
            layout.addWidget(empty)
        else:
            for task in tasks:
                layout.addWidget(self._make_row(task))
        self.body.addWidget(frame)

    def _make_row(self, task: dict) -> QWidget:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        label = QLabel(_line(task))
        label.setWordWrap(True)
        btn_done = QPushButton("Hecho")
        btn_done.setFixedWidth(72)
        btn_done.clicked.connect(lambda: self._complete_task(task))

        row_layout.addWidget(label, 1)
        row_layout.addWidget(btn_done)
        return row

    def _complete_task(self, task: dict) -> None:
        if update_task_by_id(
            self.tasks,
            task,
            completado=True,
            ultima_actualizacion=today_iso(date.today()),
        ):
            self.repo.save_all(self.tasks)
            self.refresh()
            if self.on_tasks_changed:
                self.on_tasks_changed()
