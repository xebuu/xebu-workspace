# app/tabs/tab_configuracion.py
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QButtonGroup, QToolButton, QFrame
)

from app.utility.theme import THEME_REGISTRY, theme_manager

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
        theme_title = QLabel("Elegir color de resaltado")
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

        for name in THEME_REGISTRY.keys():
            btn = self._make_color_dot(name, THEME_REGISTRY[name]["accent"]["normal"])
            self.group.addButton(btn)
            self._buttons[name] = btn
            row.addWidget(btn)

            if name == self.selected_theme_name:
                btn.setChecked(True)

        self.group.buttonToggled.connect(self._on_theme_toggled)
        cosmetic_layout.addLayout(row)

        # Display mode selection section
        mode_title = QLabel("Elegir modo de visualización")
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
        self.save_btn = QPushButton("Guardar")
        self.save_btn.setObjectName("SaveBtn")
        self.save_btn.setFixedHeight(36)
        self.save_btn.clicked.connect(self._save)
        cosmetic_layout.addWidget(self.save_btn, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Small hint label
        self.hint_label = QLabel(f"Tema guardado: {self.selected_theme_name}, modo: {self.selected_mode}. Selección guardada en config.json.")
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
        user_data_title = QLabel("Datos de usuario")
        user_data_title.setObjectName("UserDataTitle")
        user_data_layout_outer.addWidget(user_data_title)

        # User data buttons in a vertical layout
        user_data_layout = QVBoxLayout()
        user_data_layout.setSpacing(8)

        self.export_btn = QPushButton("Exportar mis datos")
        self.export_btn.setObjectName("UserDataBtn")
        self.export_btn.setFixedHeight(32)
        self.export_btn.clicked.connect(self._export_data)
        user_data_layout.addWidget(self.export_btn)

        self.delete_btn = QPushButton("Eliminar mis datos")
        self.delete_btn.setObjectName("UserDataBtn")
        self.delete_btn.setFixedHeight(32)
        self.delete_btn.clicked.connect(self._delete_data)
        user_data_layout.addWidget(self.delete_btn)

        self.view_btn = QPushButton("Ver mis datos")
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
                self.hint_label.setText(f"Tema guardado: {self.selected_theme_name}, modo: {self.selected_mode}. Selección guardada en config.json.")
                theme_manager.set_theme(name)
                break

    def _make_mode_button(self, mode_name: str) -> QToolButton:
        btn = QToolButton(self)
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedSize(80, 36)  # rectangular button
        btn.setObjectName("ModeBtn")
        btn.setText(mode_name)

        # Optional: tooltip to show mode name
        btn.setToolTip(f"Modo {mode_name}")
        return btn

    def _on_mode_toggled(self, button: QToolButton, checked: bool):
        if not checked:
            return
        # Find which mode is checked
        for name, btn in self._mode_buttons.items():
            if btn is button:
                self.selected_mode = name
                self.hint_label.setText(f"Tema guardado: {self.selected_theme_name}, modo: {self.selected_mode}. Selección guardada en config.json.")
                break

    def _save(self):
        # Placeholder save functionality - just show message
        QMessageBox.information(self, "Guardado", f"Tema guardado: {self.selected_theme_name}, modo: {self.selected_mode}")
        self.hint_label.setText(
            f"Tema guardado: {self.selected_theme_name}, modo: {self.selected_mode}. Selección guardada en config.json.")

    def _export_data(self):
        # Placeholder export functionality
        QMessageBox.information(self, "Exportar Datos", "¡Funcionalidad de exportación próximamente!\n\nEsto te permitirá exportar todos tus datos.")

    def _delete_data(self):
        # Placeholder delete functionality with confirmation
        reply = QMessageBox.question(
            self, "Eliminar Datos",
            "¿Estás seguro de que quieres eliminar todos tus datos?\n\nEsta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            QMessageBox.information(self, "Eliminar Datos", "¡Funcionalidad de eliminación próximamente!\n\nTodos tus datos serían eliminados permanentemente.")

    def _view_data(self):
        # Placeholder view functionality
        QMessageBox.information(self, "Ver Datos", "¡Funcionalidad de visualización próximamente!\n\nEsto te mostrará todos tus datos almacenados.")
