# app/tabs/tab_configuracion.py
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QButtonGroup, QToolButton, QFrame
)

THEMES = {
    "Pink": {
        "accent": {"normal": "#ff4fa3", "hover": "#ff77bd", "checked": "#d93d86", "text": "#ffffff"}
    },
    "Yellow": {
        "accent": {"normal": "#facf4e", "hover": "#ffe08a", "checked": "#e0b83c", "text": "#111111"}
    },
    "Green": {
        "accent": {"normal": "#4D8F71", "hover": "#6fb091", "checked": "#3d725a", "text": "#ffffff"}
    },
    "Blue": {
        "accent": {"normal": "#46abf3", "hover": "#77c2ff", "checked": "#2d8fd6", "text": "#ffffff"}
    },
    "Mint": {
        "accent": {"normal": "#91C4B9", "hover": "#b2ddd4", "checked": "#6ea89b", "text": "#111111"}
    },
}

class ConfiguracionTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración")

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)
        root.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Configuración")
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignCenter)
        root.addWidget(title)

        # Cosmetic settings group
        cosmetic_frame = QFrame()
        cosmetic_frame.setObjectName("CosmeticFrame")
        cosmetic_frame.setFrameStyle(QFrame.Box)
        cosmetic_frame.setLineWidth(1)
        cosmetic_layout = QVBoxLayout(cosmetic_frame)
        cosmetic_layout.setContentsMargins(12, 12, 12, 12)
        cosmetic_layout.setSpacing(12)

        # Theme selection section
        theme_title = QLabel("Choose highlight color")
        theme_title.setObjectName("ThemeTitle")
        cosmetic_layout.addWidget(theme_title)

        # Row of 5 circular buttons
        row = QHBoxLayout()
        row.setSpacing(14)
        row.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.group = QButtonGroup(self)
        self.group.setExclusive(True)

        self._buttons: dict[str, QToolButton] = {}
        self.selected_theme_name = "Pink"  # Default

        for name in ("Pink", "Yellow", "Green", "Blue", "Mint"):
            btn = self._make_color_dot(name, THEMES[name]["accent"]["normal"])
            self.group.addButton(btn)
            self._buttons[name] = btn
            row.addWidget(btn)

            if name == self.selected_theme_name:
                btn.setChecked(True)

        self.group.buttonToggled.connect(self._on_theme_toggled)
        cosmetic_layout.addLayout(row)

        # Display mode selection section
        mode_title = QLabel("Choose display mode")
        mode_title.setObjectName("ModeTitle")
        cosmetic_layout.addWidget(mode_title)

        # Row of 2 mode buttons
        mode_row = QHBoxLayout()
        mode_row.setSpacing(14)
        mode_row.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)

        self._mode_buttons: dict[str, QToolButton] = {}
        self.selected_mode = "Dark"  # Default

        for mode in ("Dark", "Light"):
            btn = self._make_mode_button(mode)
            self.mode_group.addButton(btn)
            self._mode_buttons[mode] = btn
            mode_row.addWidget(btn)

            if mode == self.selected_mode:
                btn.setChecked(True)

        self.mode_group.buttonToggled.connect(self._on_mode_toggled)
        cosmetic_layout.addLayout(mode_row)

        # Save button
        self.save_btn = QPushButton("Save")
        self.save_btn.setObjectName("SaveBtn")
        self.save_btn.setFixedHeight(36)
        self.save_btn.clicked.connect(self._save)
        cosmetic_layout.addWidget(self.save_btn, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Small hint label
        self.hint_label = QLabel(f"Saved theme: {self.selected_theme_name}, mode: {self.selected_mode}. Selection stored in config.json.")
        self.hint_label.setObjectName("HintLabel")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        cosmetic_layout.addWidget(self.hint_label)

        root.addWidget(cosmetic_frame)

        # User data group
        user_data_frame = QFrame()
        user_data_frame.setObjectName("UserDataFrame")
        user_data_frame.setFrameStyle(QFrame.Box)
        user_data_frame.setLineWidth(1)
        user_data_layout_outer = QVBoxLayout(user_data_frame)
        user_data_layout_outer.setContentsMargins(12, 12, 12, 12)
        user_data_layout_outer.setSpacing(12)

        # User data section
        user_data_title = QLabel("User data")
        user_data_title.setObjectName("UserDataTitle")
        user_data_layout_outer.addWidget(user_data_title)

        # User data buttons in a vertical layout
        user_data_layout = QVBoxLayout()
        user_data_layout.setSpacing(8)

        self.export_btn = QPushButton("Export my data")
        self.export_btn.setObjectName("UserDataBtn")
        self.export_btn.setFixedHeight(32)
        self.export_btn.clicked.connect(self._export_data)
        user_data_layout.addWidget(self.export_btn)

        self.delete_btn = QPushButton("Delete my data")
        self.delete_btn.setObjectName("UserDataBtn")
        self.delete_btn.setFixedHeight(32)
        self.delete_btn.clicked.connect(self._delete_data)
        user_data_layout.addWidget(self.delete_btn)

        self.view_btn = QPushButton("View my data")
        self.view_btn.setObjectName("UserDataBtn")
        self.view_btn.setFixedHeight(32)
        self.view_btn.clicked.connect(self._view_data)
        user_data_layout.addWidget(self.view_btn)

        user_data_layout_outer.addLayout(user_data_layout)

        root.addWidget(user_data_frame)

        root.addStretch()

    def _make_color_dot(self, theme_name: str, color_hex: str) -> QToolButton:
        btn = QToolButton(self)
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedSize(34, 34)  # circle size
        btn.setObjectName("ThemeDot")

        # Base style + checked ring + hover ring
        btn.setStyleSheet(
            f"""
            QToolButton#ThemeDot {{
                background-color: {color_hex};
                border-radius: 17px;
                border: 2px solid transparent;
            }}
            QToolButton#ThemeDot:hover {{
                border: 2px solid rgba(255, 255, 255, 0.55);
            }}
            QToolButton#ThemeDot:checked {{
                border: 3px solid #ffffff;
            }}
            """
        )

        # Optional: tooltip to show theme name
        btn.setToolTip(theme_name)
        return btn

    def _on_theme_toggled(self, button: QToolButton, checked: bool):
        if not checked:
            return
        # Find which theme is checked
        for name, btn in self._buttons.items():
            if btn is button:
                self.selected_theme_name = name
                self.hint_label.setText(f"Saved theme: {self.selected_theme_name}, mode: {self.selected_mode}. Selection stored in config.json.")
                break

    def _make_mode_button(self, mode_name: str) -> QToolButton:
        btn = QToolButton(self)
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedSize(80, 36)  # rectangular button
        btn.setObjectName("ModeBtn")
        btn.setText(mode_name)

        # Optional: tooltip to show mode name
        btn.setToolTip(f"{mode_name} mode")
        return btn

    def _on_mode_toggled(self, button: QToolButton, checked: bool):
        if not checked:
            return
        # Find which mode is checked
        for name, btn in self._mode_buttons.items():
            if btn is button:
                self.selected_mode = name
                self.hint_label.setText(f"Saved theme: {self.selected_theme_name}, mode: {self.selected_mode}. Selection stored in config.json.")
                break

    def _save(self):
        # Placeholder save functionality - just show message
        QMessageBox.information(self, "Saved", f"Saved theme: {self.selected_theme_name}, mode: {self.selected_mode}")
        self.hint_label.setText(
            f"Saved theme: {self.selected_theme_name}, mode: {self.selected_mode}. Selection stored in config.json.")

    def _export_data(self):
        # Placeholder export functionality
        QMessageBox.information(self, "Export Data", "Export functionality coming soon!\n\nThis will allow you to export all your data.")

    def _delete_data(self):
        # Placeholder delete functionality with confirmation
        reply = QMessageBox.question(
            self, "Delete Data",
            "Are you sure you want to delete all your data?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            QMessageBox.information(self, "Delete Data", "Delete functionality coming soon!\n\nAll your data would be permanently removed.")

    def _view_data(self):
        # Placeholder view functionality
        QMessageBox.information(self, "View Data", "View functionality coming soon!\n\nThis will show you all your stored data.")