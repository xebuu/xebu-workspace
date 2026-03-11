# app/tabs/tab_calendar.py
from __future__ import annotations

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QCalendarWidget, QFrame, QSizePolicy
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
        self.db = self.tasks_repo.load()
        
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
        
        # Right side: Tasks section (placeholder for now)
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
        
    def _setup_tasks_section(self, parent_layout: QHBoxLayout):
        """Setup the tasks management section."""
        tasks_frame = QFrame()
        tasks_frame.setObjectName("TasksFrame")
        tasks_frame.setFrameStyle(QFrame.Box | QFrame.Sunken)
        tasks_layout = QVBoxLayout(tasks_frame)
        tasks_layout.setContentsMargins(8, 8, 8, 8)
        
        # Placeholder section header
        tasks_header = QLabel("Tareas del día")
        tasks_header.setObjectName("SectionHeader")
        tasks_layout.addWidget(tasks_header)
        
        # Placeholder for tasks list (TODO: implement task list widget)
        placeholder = QLabel("Selecciona una fecha para ver tareas")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("color: #888; font-style: italic;")
        tasks_layout.addWidget(placeholder, 1)
        
        tasks_frame.setMinimumWidth(300)
        parent_layout.addWidget(tasks_frame, 1)
        
    def _on_date_selected(self, date: QDate):
        """Handle calendar date selection."""
        # This will be expanded to load and display tasks for the selected date
        selected_date = date.toString("yyyy-MM-dd")
        print(f"Selected date: {selected_date}")
        # TODO: Load tasks for this date from database
