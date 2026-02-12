from PySide6.QtWidgets import QLineEdit


class ProjectSearchBar(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("ProjectSearchBar") # QSS hooks

        self.setPlaceholderText("Buscar proyecto…") # UX defaults
        self.setClearButtonEnabled(True)

        # Basic rounded look for now (you can later move/override in your QSS)<
        self.setStyleSheet("""
            QLineEdit#ProjectSearchBar {
                border-radius: 12px;
                padding: 6px 10px;
            }
        """)
