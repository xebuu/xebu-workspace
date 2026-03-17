from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFrame, QSizePolicy, QVBoxLayout, QPushButton


class SidebarButton(QPushButton):
    """QPushButton variant that knows how to collapse/expand inside the overlay."""

    def __init__(
        self,
        text: str,
        icon: QIcon | None = None,
        page_key: str | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self.full_text = text
        self.page_key = page_key
        self._expanded = True

        if icon is not None:
            self.setIcon(icon)

        self.setObjectName("SidebarButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(48)
        self.setIconSize(QSize(20, 20))
        self.setProperty("selected", False)
        self.set_expanded(False)

    def set_expanded(self, expanded: bool) -> None:
        """Switch between icon-only (collapsed) and icon/text (expanded) states."""

        self._expanded = expanded

        if expanded:
            self.setText(self.full_text)
            self.setStyleSheet(
                "QPushButton { text-align: left; padding-left: 14px; }"
            )
            self.setToolTip("")
        else:
            self.setText("")
            self.setStyleSheet("QPushButton { text-align: center; padding: 0px; }")
            self.setToolTip(self.full_text)

        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def set_selected(self, selected: bool) -> None:
        """Provide a hook for stylesheets to respond to a selected state."""

        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()


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
