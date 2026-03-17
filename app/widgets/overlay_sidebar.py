from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QSizePolicy, QVBoxLayout, QPushButton


class SidebarButton(QPushButton):
    """A stylized button intended for use in the overlay sidebar."""

    def __init__(self, text="", icon=None, parent=None):
        super().__init__(text, parent)

        self.setObjectName("SidebarButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        if icon is not None:
            self.setIcon(icon)

        self.setMinimumHeight(32)

    def set_selected(self, selected: bool) -> None:
        """Toggle a visual selected state so stylesheet hooks can work."""

        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)


class OverlaySidebar(QFrame):
    """A vertical sidebar that can be floated on top of other widgets."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("OverlaySidebar")
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        layout.addStretch()
        self._layout = layout

    def add_button(self, button: SidebarButton) -> None:
        """Insert a button into the sidebar stack."""

        self._layout.insertWidget(self._layout.count() - 1, button)

