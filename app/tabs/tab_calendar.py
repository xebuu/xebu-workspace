# app/tabs/tab_calendar.py
from __future__ import annotations
import datetime

from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QTextCharFormat, QColor
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QCalendarWidget, QFrame, QSizePolicy, QScrollArea, QPushButton, QMessageBox
)
from app.utility.database import TasksRepo


class CalendarTab(QMainWindow):
    """Calendar Tab for viewing and managing tasks by date."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Calendario")
        self.resize(1000, 640)
        
        # Initialize database
        self.tasks_repo = TasksRepo()
        self.selected_date = QDate.currentDate()
        
        # Setup central widget and main layout
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)
        
        # Title
        title = QLabel("Calendario")
        title.setObjectName("Title")
        root.addWidget(title)
        
        # Main content area with calendar and tasks section
        content = QHBoxLayout()
        content.setSpacing(16)
        
        # Left side: Calendar widget
        self._setup_calendar_section(content)
        
        # Right side: Tasks section
        self._setup_tasks_section(content)
        
        root.addLayout(content, 1)
        
    def _setup_calendar_section(self, parent_layout: QHBoxLayout):
        """Setup the interactive calendar widget."""
        calendar_frame = QFrame()
        calendar_frame.setObjectName("CalendarFrame")
        calendar_frame.setFrameStyle(QFrame.Box | QFrame.Sunken)
        calendar_layout = QVBoxLayout(calendar_frame)
        calendar_layout.setContentsMargins(8, 8, 8, 8)
        
        # Create the calendar widget
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setSelectedDate(QDate.currentDate())
        self.calendar.clicked.connect(self._on_date_selected)
        
        calendar_layout.addWidget(self.calendar)
        parent_layout.addWidget(calendar_frame, 1)
        
        # Mark dates with tasks
        self._update_calendar_indicators()
        
    def _setup_tasks_section(self, parent_layout: QHBoxLayout):
        """Setup the tasks management section."""
        tasks_frame = QFrame()
        tasks_frame.setObjectName("TasksFrame")
        tasks_frame.setFrameStyle(QFrame.Box | QFrame.Sunken)
        tasks_layout = QVBoxLayout(tasks_frame)
        tasks_layout.setContentsMargins(8, 8, 8, 8)
        
        # Section header with selected date
        self.tasks_header = QLabel("Tareas del día")
        self.tasks_header.setObjectName("SectionHeader")
        tasks_layout.addWidget(self.tasks_header)
        
        # Scroll area for tasks list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("TasksScrollArea")
        
        self.tasks_container = QWidget()
        self.tasks_list_layout = QVBoxLayout(self.tasks_container)
        self.tasks_list_layout.setContentsMargins(0, 0, 0, 0)
        self.tasks_list_layout.setSpacing(6)
        
        scroll.setWidget(self.tasks_container)
        tasks_layout.addWidget(scroll, 1)
        
        tasks_frame.setMinimumWidth(300)
        parent_layout.addWidget(tasks_frame, 1)
        
        # Load initial tasks for today
        self._on_date_selected(self.selected_date)
        
    def _on_date_selected(self, date: QDate):
        """Handle calendar date selection and load tasks for that date."""
        self.selected_date = date
        selected_date_str = date.toString("yyyy-MM-dd")
        
        # Update header
        formatted_date = date.toString("dddd, d 'de' MMMM 'de' yyyy")
        self.tasks_header.setText(f"Tareas del día • {formatted_date}")
        
        # Load all tasks
        all_tasks = self.tasks_repo.load()
        
        # Filter tasks by deadline matching the selected date
        tasks_for_date = [
            t for t in all_tasks 
            if t.get("deadline", "").strip() == selected_date_str
        ]
        
        # Clear existing task widgets
        while self.tasks_list_layout.count():
            widget = self.tasks_list_layout.takeAt(0).widget()
            if widget:
                widget.deleteLater()
        
        # Display tasks for the selected date
        if not tasks_for_date:
            placeholder = QLabel("No hay tareas para este día")
            placeholder.setAlignment(Qt.AlignCenter)
            placeholder.setStyleSheet("color: #888; font-style: italic;")
            self.tasks_list_layout.addWidget(placeholder)
        else:
            for task in tasks_for_date:
                task_widget = self._create_task_widget(task)
                self.tasks_list_layout.addWidget(task_widget)
        
        # Add "Add Task" button at the end
        add_task_button = self._create_add_task_button()
        self.tasks_list_layout.addWidget(add_task_button)
        
        self.tasks_list_layout.addStretch()
    
    def _create_task_widget(self, task: dict) -> QFrame:
        """Create a widget to display a single task."""
        frame = QFrame()
        frame.setObjectName("TaskItemFrame")
        frame.setFrameStyle(QFrame.Box | QFrame.Plain)
        frame.setLineWidth(1)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        
        # Task text and status
        task_text = task.get("tarea", "Sin descripción")
        is_done = task.get("completado", False)
        is_daily = task.get("diaria", False)
        priority = (task.get("prioridad") or "media").lower()
        
        # Format task display
        status_icon = "✅" if is_done else "⏳"
        daily_tag = " (diaria)" if is_daily else ""
        priority_icon = "⚪⚪⚪" if priority == "alta" else ("⚪" if priority == "baja" else "⚪⚪")
        
        task_label = QLabel(f"{status_icon} {task_text}{daily_tag} {priority_icon}")
        task_label.setWordWrap(True)
        layout.addWidget(task_label)
        
        # Button row
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(4)
        
        # Toggle completion button
        toggle_text = "↩️ Deshacer" if is_done else "✔️ Completar"
        btn_toggle = QPushButton(toggle_text)
        btn_toggle.setMaximumWidth(100)
        btn_toggle.clicked.connect(lambda: self._toggle_task(task))
        btn_layout.addWidget(btn_toggle)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        return frame
    
    def _toggle_task(self, task: dict):
        """Toggle task completion status."""
        task["completado"] = not task.get("completado", False)
        self.tasks_repo.save(self.tasks_repo.load())
        
        # Reload tasks to update display
        all_tasks = self.tasks_repo.load()
        for t in all_tasks:
            if t.get("tarea") == task.get("tarea"):
                t["completado"] = task["completado"]
        
        self.tasks_repo.save(all_tasks)
        self._on_date_selected(self.selected_date)
        self._update_calendar_indicators()
    
    def _create_add_task_button(self) -> QFrame:
        """Create an elegant add task button that looks like a task item."""
        frame = QFrame()
        frame.setObjectName("AddTaskButtonFrame")
        frame.setFrameStyle(QFrame.Box | QFrame.Plain)
        frame.setLineWidth(1)
        frame.setStyleSheet("""
            QFrame#AddTaskButtonFrame {
                border-style: dashed;
                border-color: #aaa;
                background-color: transparent;
            }
            QFrame#AddTaskButtonFrame:hover {
                background-color: #f0f0f0;
            }
        """)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        
        # Add task label
        add_label = QLabel("➕ Agregar tarea")
        add_label.setStyleSheet("color: #666; font-weight: bold;")
        layout.addWidget(add_label)
        
        # Make the entire frame clickable
        frame.mousePressEvent = lambda event: self._show_add_task_dialog()
        
        return frame
    
    def _show_add_task_dialog(self):
        """Show dialog to add a new task for the selected date."""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox, QCheckBox, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Agregar Nueva Tarea")
        dialog.setModal(True)
        dialog.resize(400, 200)
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # Task description
        task_edit = QLineEdit()
        task_edit.setPlaceholderText("Descripción de la tarea...")
        layout.addWidget(QLabel("Tarea:"))
        layout.addWidget(task_edit)
        
        # Priority selector
        priority_combo = QComboBox()
        priority_combo.addItems(["baja", "media", "alta"])
        priority_combo.setCurrentText("media")
        layout.addWidget(QLabel("Prioridad:"))
        layout.addWidget(priority_combo)
        
        # Daily task checkbox
        daily_check = QCheckBox("Tarea diaria (se reinicia automáticamente)")
        layout.addWidget(daily_check)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(lambda: self._add_task_and_close(dialog, task_edit, priority_combo, daily_check))
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.exec()
    
    def _add_task_and_close(self, dialog, task_edit, priority_combo, daily_check):
        """Add the task and close the dialog."""
        task_text = task_edit.text().strip()
        if not task_text:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(dialog, "Error", "Por favor ingresa una descripción para la tarea.")
            return
        
        # Create new task
        new_task = {
            "tarea": task_text,
            "completado": False,
            "diaria": daily_check.isChecked(),
            "deadline": self.selected_date.toString("yyyy-MM-dd"),
            "prioridad": priority_combo.currentText(),
            "ultima_actualizacion": self.selected_date.toString("yyyy-MM-dd")
        }
        
        # Add to database
        all_tasks = self.tasks_repo.load()
        all_tasks.append(new_task)
        self.tasks_repo.save(all_tasks)
        
        # Refresh UI
        self._on_date_selected(self.selected_date)
        self._update_calendar_indicators()
        
        dialog.accept()
    
    def _update_calendar_indicators(self):
        """Mark dates with tasks using subtle visual indicators on the calendar."""
        # Load all tasks from database
        all_tasks = self.tasks_repo.load()
        
        # Extract unique deadline dates
        task_dates = set()
        for task in all_tasks:
            deadline = task.get("deadline", "").strip()
            if deadline:
                try:
                    # Validate and add to set
                    QDate.fromString(deadline, "yyyy-MM-dd")
                    task_dates.add(deadline)
                except:
                    pass
        
        # Create format for dates with tasks - subtle blue text
        task_format = QTextCharFormat()
        task_format.setForeground(QColor(72, 149, 239))  # Blue text
        task_format.setFontWeight(700)  # Bold
        
        # Apply format to dates with tasks
        for date_str in task_dates:
            date = QDate.fromString(date_str, "yyyy-MM-dd")
            if date.isValid():
                self.calendar.setDateTextFormat(date, task_format)
