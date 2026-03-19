from functools import partial

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QEvent,
    QPropertyAnimation,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStyle,
    QVBoxLayout,
)

COLLAPSED_WIDTH = 72
EXPANDED_WIDTH = 220
ANIMATION_DURATION = 180

DEFAULT_NAV_ITEMS = [
    {"text": "📁 Proyectos", "page_key": "projects"},
    {"text": "📅 Calendario", "page_key": "calendar"},
    {"text": "⚙️ Configuracion", "page_key": "settings"},
]


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

        self._collapsed_text = text.split(" ", 1)[0] if " " in text else text

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
            self.setStyleSheet("QPushButton { text-align: left; padding-left: 14px; }")
            self.setToolTip("")
        else:
            self.setText(self._collapsed_text)
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
    """Sidebar that expands on hover, manages navigation buttons, and emits selections."""

    page_requested = Signal(str)

    def __init__(self, navigation_items=None, parent=None):
        super().__init__(parent)

        self.setObjectName("OverlaySidebar")
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setAttribute(Qt.WA_Hover, True)
        self.setMouseTracking(True)

        self._panel_width = 0
        self._expanded = False
        self._selected_key: str | None = None
        self._items = navigation_items or DEFAULT_NAV_ITEMS
        self._buttons: dict[str, SidebarButton] = {}

        self._animation = QPropertyAnimation(self, b"panelWidth", self)
        self._animation.setDuration(ANIMATION_DURATION)
        self._animation.setEasingCurve(QEasingCurve.InOutCubic)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 12, 10, 12)
        layout.setSpacing(10)

        self._build_ui(layout)

        layout.addStretch()
        self.footer_label = QLabel("PySide6")
        self.footer_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.footer_label)

        if self._buttons:
            first_key = next(iter(self._buttons))
            self.select_page(first_key)

        self.panelWidth = COLLAPSED_WIDTH

    def _build_ui(self, layout: QVBoxLayout) -> None:

        style = QApplication.style()
        for entry in self._items:
            icon = self._resolve_entry_icon(entry, style)

            button = self._add_button(
                entry["text"],
                icon,
                entry["page_key"],
                layout,
            )
            self._buttons[entry["page_key"]] = button

    def _add_button(
        self, text: str, icon: QIcon | None, page_key: str, layout: QVBoxLayout
    ) -> SidebarButton:
        button = SidebarButton(text, icon, page_key, self)
        button.installEventFilter(self)
        button.clicked.connect(partial(self._on_button_clicked, page_key))
        layout.addWidget(button)
        return button

    def _resolve_entry_icon(self, entry: dict, style: QStyle):
        icon = None
        icon_theme = entry.get("icon_theme")
        if icon_theme:
            icon = QIcon.fromTheme(icon_theme)
            if icon.isNull():
                icon = None

        if icon is None:
            icon_role = entry.get("icon_role")
            if icon_role is not None:
                icon = style.standardIcon(icon_role)

        return icon

    def expand(self) -> None:
        """Force the sidebar into its expanded state."""

        self._set_expanded(True)

    def collapse(self) -> None:
        """Restore the sidebar to collapsed width."""

        self._set_expanded(False)

    def enterEvent(self, event):
        self.expand()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.collapse()
        super().leaveEvent(event)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Enter and watched in self._buttons.values():
            self.expand()
        return super().eventFilter(watched, event)

    def get_panel_width(self) -> int:
        return self._panel_width

    def set_panel_width(self, value: int) -> None:
        value = int(value)
        if self._panel_width == value:
            return
        self._panel_width = value
        self.setFixedWidth(value)
        self._update_expanded_state_visuals()

        parent = self.parent()
        if parent and hasattr(parent, "update_sidebar_geometry"):
            parent.update_sidebar_geometry()

    panelWidth = Property(int, get_panel_width, set_panel_width)

    def _on_button_clicked(self, page_key: str) -> None:
        self.select_page(page_key, emit=True)

    def _set_expanded(self, expanded: bool) -> None:
        expanded = bool(expanded)
        if self._expanded == expanded:
            return
        self._animation.stop()
        self._expanded = expanded
        self.setProperty("expanded", expanded)
        self._animate_width(EXPANDED_WIDTH if expanded else COLLAPSED_WIDTH)
        self.style().unpolish(self)
        self.style().polish(self)

    def _animate_width(self, target: int, immediate: bool = False) -> None:
        self._animation.stop()
        if immediate:
            self.panelWidth = target
            return
        self._animation.setStartValue(self.panelWidth)
        self._animation.setEndValue(target)
        self._animation.start()

    def _update_expanded_state_visuals(self) -> None:
        expanded = self._panel_width >= (COLLAPSED_WIDTH + EXPANDED_WIDTH) / 2
        self.footer_label.setVisible(expanded)
        for button in self._buttons.values():
            button.set_expanded(expanded)

    def select_page(self, page_key: str, emit: bool = False) -> bool:
        """Update selection state and optionally notify listeners."""

        button = self._buttons.get(page_key)
        if button is None:
            return False

        for key, control in self._buttons.items():
            control.set_selected(key == page_key)

        self._selected_key = page_key

        if emit:
            self.page_requested.emit(page_key)

        return True
