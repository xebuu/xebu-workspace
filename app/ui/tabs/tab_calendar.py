from __future__ import annotations

from PySide6.QtCore import QDate, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QTextCharFormat
from PySide6.QtWidgets import (
    QCalendarWidget,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
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
    DEFAULT_BITACORA_CATEGORY,
    DEFAULT_TASK_CATEGORY,
    category_color,
    category_label,
    normalize_category,
)
from app.core.theme import theme_manager
from app.database.bitacora_repository import BitacoraRepository
from app.database.tasks_repository import TasksRepository


class _CategoryCalendarWidget(QCalendarWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._markers: dict[str, list[str]] = {}

    def set_category_markers(self, markers: dict[str, list[str]]) -> None:
        self._markers = markers
        self.update()

    def paintCell(self, painter: QPainter, rect, date):
        super().paintCell(painter, rect, date)
        categories = self._markers.get(date.toString("yyyy-MM-dd"), [])
        if not categories:
            return

        painter.save()
        dot_size = 6
        gap = 3
        total_width = len(categories) * dot_size + max(0, len(categories) - 1) * gap
        start_x = rect.center().x() - (total_width / 2)
        y = rect.bottom() - 10

        for index, category in enumerate(categories[:4]):
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(category_color(category)))
            x = start_x + index * (dot_size + gap)
            painter.drawEllipse(QRectF(x, y, dot_size, dot_size))
        painter.restore()


class CalendarTab(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Calendario")
        self.resize(1000, 640)

        self.tasks_repo = TasksRepository()
        self.bitacora_repo = BitacoraRepository()
        self.tasks_repo.reset_daily_if_needed(self.tasks_repo.list_all())
        self.selected_date = QDate.currentDate()
        self.visible_categories = set(CATEGORY_DEFINITIONS)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        title = QLabel("Calendario")
        title.setObjectName("Title")
        root.addWidget(title)

        content = QHBoxLayout()
        content.setSpacing(16)
        self._setup_calendar_section(content)
        self._setup_tasks_section(content)
        root.addLayout(content, 1)

    def _setup_calendar_section(self, parent_layout: QHBoxLayout):
        calendar_frame = QFrame()
        calendar_frame.setObjectName("CalendarFrame")
        calendar_frame.setFrameStyle(QFrame.Box | QFrame.Sunken)
        calendar_layout = QVBoxLayout(calendar_frame)
        calendar_layout.setContentsMargins(8, 8, 8, 8)
        calendar_layout.setSpacing(8)

        filters = QHBoxLayout()
        filters.addWidget(QLabel("Mostrar:"))
        for key in CATEGORY_DEFINITIONS:
            check = QCheckBox(category_label(key))
            check.setChecked(True)
            check.toggled.connect(
                lambda checked, category=key: self._set_category_visible(
                    category, checked
                )
            )
            filters.addWidget(check)
        filters.addStretch()
        calendar_layout.addLayout(filters)

        self.calendar = _CategoryCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setSelectedDate(QDate.currentDate())
        self.calendar.clicked.connect(self._on_date_selected)
        theme_manager.theme_changed.connect(self._apply_calendar_theme)
        self._apply_calendar_theme()

        calendar_layout.addWidget(self.calendar)
        parent_layout.addWidget(calendar_frame, 1)
        self._update_calendar_indicators()

    def _setup_tasks_section(self, parent_layout: QHBoxLayout):
        tasks_frame = QFrame()
        tasks_frame.setObjectName("TasksFrame")
        tasks_frame.setFrameStyle(QFrame.Box | QFrame.Sunken)
        tasks_layout = QVBoxLayout(tasks_frame)
        tasks_layout.setContentsMargins(8, 8, 8, 8)

        self.tasks_header = QLabel("Actividad del día")
        self.tasks_header.setObjectName("SectionHeader")
        tasks_layout.addWidget(self.tasks_header)

        self.legend = QLabel("")
        self.legend.setStyleSheet("color: #888;")
        tasks_layout.addWidget(self.legend)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("TasksScrollArea")

        self.tasks_container = QWidget()
        self.tasks_list_layout = QVBoxLayout(self.tasks_container)
        self.tasks_list_layout.setContentsMargins(0, 0, 0, 0)
        self.tasks_list_layout.setSpacing(6)

        scroll.setWidget(self.tasks_container)
        tasks_layout.addWidget(scroll, 1)

        tasks_frame.setMinimumWidth(320)
        parent_layout.addWidget(tasks_frame, 1)
        self._on_date_selected(self.selected_date)

    def _set_category_visible(self, category: str, checked: bool):
        if checked:
            self.visible_categories.add(category)
        else:
            self.visible_categories.discard(category)
        self._update_calendar_indicators()
        self._on_date_selected(self.selected_date)

    def _load_day_data(self) -> dict[str, dict]:
        day_map: dict[str, dict] = {}

        for task in self.tasks_repo.list_all():
            deadline = (task.get("deadline") or "").strip()
            if not deadline:
                continue
            category = normalize_category(task.get("category"), DEFAULT_TASK_CATEGORY)
            day = day_map.setdefault(
                deadline, {"tasks": [], "entries": [], "categories": set()}
            )
            day["tasks"].append(task)
            day["categories"].add(category)

        for entry in self.bitacora_repo.list_entries():
            raw_date = (entry.get("fecha") or "").strip()
            parsed = QDate.fromString(raw_date, "dd-MM-yyyy")
            if not parsed.isValid():
                parsed = QDate.fromString(raw_date, "yyyy-MM-dd")
            if not parsed.isValid():
                continue

            key = parsed.toString("yyyy-MM-dd")
            category = normalize_category(
                entry.get("category"), DEFAULT_BITACORA_CATEGORY
            )
            day = day_map.setdefault(
                key, {"tasks": [], "entries": [], "categories": set()}
            )
            day["entries"].append(entry)
            day["categories"].add(category)

        return day_map

    def _filter_categories(self, categories) -> list[str]:
        return [category for category in categories if category in self.visible_categories]

    def _task_matches(self, left: dict, right: dict) -> bool:
        left_id = left.get("id")
        right_id = right.get("id")
        if left_id and right_id:
            return left_id == right_id
        return (
            left.get("tarea") == right.get("tarea")
            and (left.get("deadline") or "").strip()
            == (right.get("deadline") or "").strip()
        )

    def _on_date_selected(self, date: QDate):
        self.selected_date = date
        selected_date_str = date.toString("yyyy-MM-dd")
        formatted_date = date.toString("dddd, d 'de' MMMM 'de' yyyy")
        self.tasks_header.setText(f"Actividad del día • {formatted_date}")

        day_data = self._load_day_data().get(
            selected_date_str, {"tasks": [], "entries": [], "categories": set()}
        )
        categories = self._filter_categories(sorted(day_data["categories"]))
        self.legend.setText(
            "Visible: "
            + (
                ", ".join(category_label(category) for category in categories)
                if categories
                else "sin categorías activas"
            )
        )

        while self.tasks_list_layout.count():
            item = self.tasks_list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        visible_tasks = [
            task
            for task in day_data["tasks"]
            if normalize_category(task.get("category"), DEFAULT_TASK_CATEGORY)
            in self.visible_categories
        ]
        visible_entries = [
            entry
            for entry in day_data["entries"]
            if normalize_category(entry.get("category"), DEFAULT_BITACORA_CATEGORY)
            in self.visible_categories
        ]

        if not visible_tasks and not visible_entries:
            placeholder = QLabel("No hay actividad visible para este día")
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setStyleSheet("color: #888; font-style: italic;")
            self.tasks_list_layout.addWidget(placeholder)
        else:
            if visible_tasks:
                self.tasks_list_layout.addWidget(QLabel("Tareas"))
                for task in visible_tasks:
                    self.tasks_list_layout.addWidget(self._create_task_widget(task))
            if visible_entries:
                self.tasks_list_layout.addWidget(QLabel("Bitácora"))
                for entry in visible_entries:
                    self.tasks_list_layout.addWidget(
                        self._create_bitacora_widget(entry)
                    )

        self.tasks_list_layout.addWidget(self._create_add_task_button())
        self.tasks_list_layout.addStretch()

    def _create_task_widget(self, task: dict) -> QFrame:
        frame = QFrame()
        frame.setObjectName("TaskItemFrame")
        frame.setFrameStyle(QFrame.Box | QFrame.Plain)
        frame.setLineWidth(1)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        task_text = task.get("tarea", "Sin descripción")
        is_done = task.get("completado", False)
        is_daily = task.get("diaria", False)
        priority = (task.get("prioridad") or "media").lower()
        category = normalize_category(task.get("category"), DEFAULT_TASK_CATEGORY)

        status_icon = "✅" if is_done else "⏳"
        daily_tag = " (diaria)" if is_daily else ""
        priority_icon = (
            "⚪⚪⚪" if priority == "alta" else ("⚪" if priority == "baja" else "⚪⚪")
        )
        task_label = QLabel(
            f"{status_icon} {task_text}{daily_tag} [{category_label(category)}] {priority_icon}"
        )
        task_label.setWordWrap(True)
        layout.addWidget(task_label)

        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(4)

        toggle_text = "↩️ Deshacer" if is_done else "✔️ Completar"
        btn_toggle = QPushButton(toggle_text)
        btn_toggle.setMaximumWidth(110)
        btn_toggle.clicked.connect(lambda: self._toggle_task(task))
        btn_layout.addWidget(btn_toggle)

        btn_delete = QPushButton("🗑️")
        btn_delete.setMaximumWidth(40)
        btn_delete.setToolTip("Eliminar tarea")
        btn_delete.clicked.connect(lambda: self._delete_task(task))
        btn_layout.addWidget(btn_delete)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        return frame

    def _create_bitacora_widget(self, entry: dict) -> QFrame:
        frame = QFrame()
        frame.setFrameStyle(QFrame.Box | QFrame.Plain)
        frame.setLineWidth(1)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        category = normalize_category(
            entry.get("category"), DEFAULT_BITACORA_CATEGORY
        )
        note = (entry.get("nota") or "").strip()
        preview = note if len(note) <= 120 else note[:117].rstrip() + "..."

        label = QLabel(f"• [{category_label(category)}] {preview}")
        label.setWordWrap(True)
        layout.addWidget(label)
        return frame

    def _toggle_task(self, task: dict):
        task["completado"] = not task.get("completado", False)
        all_tasks = self.tasks_repo.list_all()
        for stored in all_tasks:
            if self._task_matches(stored, task):
                stored["completado"] = task["completado"]
                break
        self.tasks_repo.save_all(all_tasks)
        self._on_date_selected(self.selected_date)
        self._update_calendar_indicators()

    def _delete_task(self, task: dict):
        reply = QMessageBox.question(
            self,
            "Eliminar Tarea",
            f"¿Estás seguro de que quieres eliminar la tarea:\n\n\"{task.get('tarea', 'Sin descripción')}\"?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        all_tasks = self.tasks_repo.list_all()
        all_tasks = [
            stored for stored in all_tasks if not self._task_matches(stored, task)
        ]
        self.tasks_repo.save_all(all_tasks)
        self._on_date_selected(self.selected_date)
        self._update_calendar_indicators()

    def _create_add_task_button(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("AddTaskButtonFrame")
        frame.setFrameStyle(QFrame.Box | QFrame.Plain)
        frame.setLineWidth(1)
        frame.setStyleSheet(
            """
            QFrame#AddTaskButtonFrame {
                border-style: dashed;
                border-color: #aaa;
                background-color: transparent;
            }
            QFrame#AddTaskButtonFrame:hover {
                background-color: #f0f0f0;
            }
            """
        )

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        add_label = QLabel("➕ Agregar tarea")
        add_label.setStyleSheet("color: #666; font-weight: bold;")
        layout.addWidget(add_label)
        frame.mousePressEvent = lambda event: self._show_add_task_dialog()
        return frame

    def _show_add_task_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Agregar Nueva Tarea")
        dialog.setModal(True)
        dialog.resize(400, 240)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        task_edit = QLineEdit()
        task_edit.setPlaceholderText("Descripción de la tarea...")
        layout.addWidget(QLabel("Tarea:"))
        layout.addWidget(task_edit)

        priority_combo = QComboBox()
        priority_combo.addItems(["baja", "media", "alta"])
        priority_combo.setCurrentText("media")
        layout.addWidget(QLabel("Prioridad:"))
        layout.addWidget(priority_combo)

        category_combo = QComboBox()
        for key in CATEGORY_DEFINITIONS:
            category_combo.addItem(category_label(key), key)
        category_combo.setCurrentText(category_label(DEFAULT_TASK_CATEGORY))
        layout.addWidget(QLabel("Categoría:"))
        layout.addWidget(category_combo)

        daily_check = QCheckBox("Tarea diaria (se reinicia automáticamente)")
        layout.addWidget(daily_check)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(
            lambda: self._add_task_and_close(
                dialog, task_edit, priority_combo, category_combo, daily_check
            )
        )
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        dialog.exec()

    def _add_task_and_close(
        self, dialog, task_edit, priority_combo, category_combo, daily_check
    ):
        task_text = task_edit.text().strip()
        if not task_text:
            QMessageBox.warning(
                dialog, "Error", "Por favor ingresa una descripción para la tarea."
            )
            return

        new_task = {
            "tarea": task_text,
            "completado": False,
            "diaria": daily_check.isChecked(),
            "deadline": self.selected_date.toString("yyyy-MM-dd"),
            "prioridad": priority_combo.currentText(),
            "ultima_actualizacion": self.selected_date.toString("yyyy-MM-dd"),
            "category": category_combo.currentData() or DEFAULT_TASK_CATEGORY,
        }
        all_tasks = self.tasks_repo.list_all()
        all_tasks.append(new_task)
        self.tasks_repo.save_all(all_tasks)
        self._on_date_selected(self.selected_date)
        self._update_calendar_indicators()
        dialog.accept()

    def _update_calendar_indicators(self):
        day_map = self._load_day_data()
        self.calendar.setDateTextFormat(QDate(), QTextCharFormat())

        markers: dict[str, list[str]] = {}
        for date_str, day in day_map.items():
            visible = self._filter_categories(sorted(day["categories"]))
            if not visible:
                continue

            fmt = QTextCharFormat()
            fmt.setFontWeight(700)
            fmt.setForeground(QColor(category_color(visible[0])))

            date = QDate.fromString(date_str, "yyyy-MM-dd")
            if date.isValid():
                self.calendar.setDateTextFormat(date, fmt)
                markers[date_str] = visible[:4]

        self.calendar.set_category_markers(markers)

    def _apply_calendar_theme(self, _theme_name: str | None = None):
        nav_bg = theme_manager.get_color("calendar", "nav_bar_bg")
        nav_text = theme_manager.get_color(
            "calendar", "nav_bar_text", fallback="#ffffff"
        )
        style = f"""
            QCalendarWidget QWidget#qt_calendar_navigationbar {{
                background-color: {nav_bg};
            }}
            QCalendarWidget QWidget#qt_calendar_navigationbar QToolButton {{
                color: {nav_text};
                border: none;
            }}
        """
        self.calendar.setStyleSheet(style)
