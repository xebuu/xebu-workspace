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
