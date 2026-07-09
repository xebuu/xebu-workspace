from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
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

from app.core.task_helpers import (
    create_task,
    delete_task_by_id,
    normalize_priority,
    tasks_for_deadline,
    today_iso,
    update_task_by_id,
)
from app.core.theme import theme_manager
from app.database.tasks_repository import TasksRepository


WEEKDAY_LABELS = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]


def _month_label(value: date) -> str:
    return value.strftime("%B %Y").capitalize()


def _task_line(task: dict) -> str:
    prefix = "[x]" if task.get("completado") else "[ ]"
    priority = normalize_priority(task.get("prioridad"))
    suffix = "" if priority == "media" else f" | {priority}"
    daily = " | diaria" if task.get("diaria") else ""
    return f"{prefix} {task.get('tarea', 'Sin titulo')}{suffix}{daily}"


class _DayCell(QFrame):
    def __init__(
        self,
        day: date,
        visible_month: int,
        selected: date,
        tasks: list[dict],
        on_select,
        parent=None,
    ):
        super().__init__(parent)
        self.day = day
        self.on_select = on_select
        is_today = day == date.today()
        is_selected = day == selected
        in_month = day.month == visible_month
        border = theme_manager.get_color("border", "subtle")
        if is_today:
            border = theme_manager.get_color("calendar", "today_border")
        if is_selected:
            border = theme_manager.get_color("accent", "normal")
        background = theme_manager.get_color("surface", "base")
        if not in_month:
            background = theme_manager.get_color("surface", "sunken")
        if is_selected:
            background = theme_manager.get_color("calendar", "selected_bg")
        self.setObjectName("CalendarDayCell")
        self.setMinimumHeight(118)
        self.setFrameStyle(QFrame.Box | QFrame.Plain)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QFrame#CalendarDayCell {{
                background: {background};
                border: 1px solid {border};
                border-radius: 8px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 7, 8, 7)
        layout.setSpacing(4)

        number = QLabel(str(day.day))
        number.setStyleSheet(
            "font-weight: 800;"
            if in_month
            else f"color: {theme_manager.get_color('text', 'muted')};"
        )
        layout.addWidget(number)

        pending_tasks = [task for task in tasks if not task.get("completado")]
        for task in pending_tasks[:3]:
            title = str(task.get("tarea") or "Sin titulo")
            display_title = title if len(title) <= 28 else title[:27].rstrip() + "..."
            chip = QLabel(display_title)
            chip.setObjectName("CalendarChip")
            chip.setWordWrap(False)
            chip.setToolTip(_task_line(task))
            layout.addWidget(chip)

        if len(pending_tasks) > 3:
            more = QLabel(f"+{len(pending_tasks) - 3} mas")
            more.setObjectName("CardMeta")
            layout.addWidget(more)

        layout.addStretch(1)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.on_select(self.day)
        super().mousePressEvent(event)


class CalendarTab(QMainWindow):
    tasks_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Calendario")
        self.resize(1000, 640)
        self.tasks_repo = TasksRepository()
        self.tasks: list[dict] = []
        self.selected_date = date.today()
        self.visible_month = self.selected_date.replace(day=1)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        title = QLabel("Calendario")
        title.setObjectName("Title")
        root.addWidget(title)

        nav = QHBoxLayout()
        self.btn_prev = QPushButton("<")
        self.btn_prev.setFixedWidth(44)
        self.btn_prev.clicked.connect(lambda: self._change_month(-1))
        self.month_title = QLabel("")
        self.month_title.setStyleSheet("font-size: 16px; font-weight: 800;")
        self.btn_today = QPushButton("Hoy")
        self.btn_today.clicked.connect(self._go_today)
        self.btn_next = QPushButton(">")
        self.btn_next.setFixedWidth(44)
        self.btn_next.clicked.connect(lambda: self._change_month(1))
        nav.addWidget(self.btn_prev)
        nav.addWidget(self.month_title)
        nav.addStretch()
        nav.addWidget(self.btn_today)
        nav.addWidget(self.btn_next)
        root.addLayout(nav)

        content = QHBoxLayout()
        content.setSpacing(16)
        root.addLayout(content, 1)

        month_frame = QFrame()
        month_frame.setObjectName("CalendarMonthFrame")
        month_frame.setFrameStyle(QFrame.Box | QFrame.Plain)
        month_layout = QVBoxLayout(month_frame)
        month_layout.setContentsMargins(8, 8, 8, 8)
        month_layout.setSpacing(8)
        weekday_row = QGridLayout()
        for col, label in enumerate(WEEKDAY_LABELS):
            weekday = QLabel(label)
            weekday.setAlignment(Qt.AlignCenter)
            weekday.setObjectName("CardMeta")
            weekday_row.addWidget(weekday, 0, col)
        month_layout.addLayout(weekday_row)
        self.month_grid = QGridLayout()
        self.month_grid.setHorizontalSpacing(6)
        self.month_grid.setVerticalSpacing(6)
        month_layout.addLayout(self.month_grid, 1)
        content.addWidget(month_frame, 3)

        agenda_frame = QFrame()
        agenda_frame.setObjectName("CalendarAgendaFrame")
        agenda_frame.setFrameStyle(QFrame.Box | QFrame.Plain)
        agenda_layout = QVBoxLayout(agenda_frame)
        agenda_layout.setContentsMargins(10, 10, 10, 10)
        agenda_layout.setSpacing(8)
        self.tasks_header = QLabel("")
        self.tasks_header.setObjectName("SectionHeader")
        agenda_layout.addWidget(self.tasks_header)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.tasks_container = QWidget()
        self.tasks_list_layout = QVBoxLayout(self.tasks_container)
        self.tasks_list_layout.setContentsMargins(0, 0, 0, 0)
        self.tasks_list_layout.setSpacing(6)
        scroll.setWidget(self.tasks_container)
        agenda_layout.addWidget(scroll, 1)
        agenda_frame.setMinimumWidth(320)
        content.addWidget(agenda_frame, 1)

        self.refresh()

    def refresh(self) -> None:
        self.tasks = self.tasks_repo.list_all()
        self.tasks_repo.reset_daily_if_needed(self.tasks)
        self._render_month()
        self._render_agenda()

    def _change_month(self, delta: int) -> None:
        month = self.visible_month.month + delta
        year = self.visible_month.year
        while month < 1:
            month += 12
            year -= 1
        while month > 12:
            month -= 12
            year += 1
        self.visible_month = date(year, month, 1)
        self._render_month()

    def _go_today(self) -> None:
        self.selected_date = date.today()
        self.visible_month = self.selected_date.replace(day=1)
        self.refresh()

    def _select_date(self, selected: date) -> None:
        self.selected_date = selected
        if (
            selected.month != self.visible_month.month
            or selected.year != self.visible_month.year
        ):
            self.visible_month = selected.replace(day=1)
        self._render_month()
        self._render_agenda()

    def _render_month(self) -> None:
        self.month_title.setText(_month_label(self.visible_month))
        while self.month_grid.count():
            item = self.month_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        first_weekday = self.visible_month.weekday()
        first_cell = self.visible_month - timedelta(days=first_weekday)
        for row in range(6):
            for col in range(7):
                current_day = first_cell + timedelta(days=row * 7 + col)
                tasks = tasks_for_deadline(self.tasks, str(current_day))
                cell = _DayCell(
                    current_day,
                    self.visible_month.month,
                    self.selected_date,
                    tasks,
                    self._select_date,
                    self,
                )
                self.month_grid.addWidget(cell, row, col)

    def _render_agenda(self) -> None:
        self.tasks_header.setText(
            f"Tareas del dia | {self.selected_date.strftime('%Y-%m-%d')}"
        )
        while self.tasks_list_layout.count():
            item = self.tasks_list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        tasks = tasks_for_deadline(self.tasks, str(self.selected_date))
        if not tasks:
            empty = QLabel("No hay tareas para este dia")
            empty.setAlignment(Qt.AlignCenter)
            empty.setObjectName("CardMeta")
            self.tasks_list_layout.addWidget(empty)
        else:
            for task in tasks:
                self.tasks_list_layout.addWidget(self._create_task_widget(task))

        self.tasks_list_layout.addWidget(self._create_add_task_button())
        self.tasks_list_layout.addStretch(1)

    def _create_task_widget(self, task: dict) -> QFrame:
        frame = QFrame()
        frame.setObjectName("TaskItemFrame")
        frame.setFrameStyle(QFrame.Box | QFrame.Plain)
        frame.setLineWidth(1)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        task_label = QLabel(_task_line(task))
        task_label.setWordWrap(True)
        layout.addWidget(task_label)

        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(4)

        toggle_text = "Deshacer" if task.get("completado") else "Completar"
        btn_toggle = QPushButton(toggle_text)
        btn_toggle.clicked.connect(lambda: self._toggle_task(task))
        btn_layout.addWidget(btn_toggle)

        btn_delete = QPushButton("Borrar")
        btn_delete.clicked.connect(lambda: self._delete_task(task))
        btn_layout.addWidget(btn_delete)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        return frame

    def _toggle_task(self, task: dict) -> None:
        if update_task_by_id(
            self.tasks,
            task,
            completado=not task.get("completado", False),
            ultima_actualizacion=today_iso(date.today()),
        ):
            self.tasks_repo.save_all(self.tasks)
            self.refresh()
            self.tasks_changed.emit()

    def _delete_task(self, task: dict) -> None:
        reply = QMessageBox.question(
            self,
            "Eliminar Tarea",
            f"Eliminar la tarea:\n\n\"{task.get('tarea', 'Sin titulo')}\"?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes and delete_task_by_id(self.tasks, task):
            self.tasks_repo.save_all(self.tasks)
            self.refresh()
            self.tasks_changed.emit()

    def _create_add_task_button(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("AddTaskButtonFrame")
        frame.setFrameStyle(QFrame.Box | QFrame.Plain)
        frame.setLineWidth(1)
        frame.setCursor(Qt.PointingHandCursor)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        add_label = QLabel("+ Agregar tarea")
        add_label.setObjectName("CardMeta")
        layout.addWidget(add_label)
        frame.mousePressEvent = lambda event: self._show_add_task_dialog()
        return frame

    def _show_add_task_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Agregar Nueva Tarea")
        dialog.setModal(True)
        dialog.resize(420, 220)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        task_edit = QLineEdit()
        task_edit.setPlaceholderText("Descripcion de la tarea...")
        priority_combo = QComboBox()
        priority_combo.addItems(["baja", "media", "alta"])
        priority_combo.setCurrentText("media")
        daily_check = QCheckBox("Tarea diaria")

        layout.addWidget(QLabel("Tarea:"))
        layout.addWidget(task_edit)
        layout.addWidget(QLabel("Prioridad:"))
        layout.addWidget(priority_combo)
        layout.addWidget(daily_check)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(
            lambda: self._add_task_and_close(
                dialog, task_edit, priority_combo, daily_check
            )
        )
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()

    def _add_task_and_close(self, dialog, task_edit, priority_combo, daily_check) -> None:
        task_text = task_edit.text().strip()
        if not task_text:
            QMessageBox.warning(
                dialog, "Error", "Por favor ingresa una descripcion para la tarea."
            )
            return
        self.tasks.append(
            create_task(
                task_text,
                deadline=str(self.selected_date),
                prioridad=priority_combo.currentText(),
                diaria=daily_check.isChecked(),
            )
        )
        self.tasks_repo.save_all(self.tasks)
        self.refresh()
        self.tasks_changed.emit()
        dialog.accept()
