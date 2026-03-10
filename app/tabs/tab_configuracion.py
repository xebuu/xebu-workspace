# app/tabs/tab_configuracion.py
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

class ConfiguracionTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración")

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        title = QLabel("Configuración")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignCenter)
        root.addWidget(title)

        # Placeholder for future content
        placeholder = QLabel("Esta sección está en desarrollo.")
        placeholder.setAlignment(Qt.AlignCenter)
        root.addStretch()
        root.addWidget(placeholder)
        root.addStretch()