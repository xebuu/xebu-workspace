from __future__ import annotations

import shutil
import webbrowser
import zipfile
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QButtonGroup,
    QColorDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.core.helpers import open_resource_target
from app.core.paths import ensure_app_data_dir
from app.core.theme import THEME_REGISTRY, theme_manager
from app.database.bootstrap import initialize_database
from app.database.settings_repository import SettingsRepository


class ConfiguracionTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración")

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(16)
        root.setAlignment(Qt.AlignmentFlag.AlignTop)

        title = QLabel("Configuración")
        title.setObjectName("Title")
        root.addWidget(title)

        appearance_frame = QFrame()
        appearance_frame.setObjectName("AppearanceFrame")
        appearance_frame.setFrameStyle(QFrame.Box)
        appearance_frame.setLineWidth(1)
        appearance_layout = QVBoxLayout(appearance_frame)
        appearance_layout.setContentsMargins(16, 16, 16, 16)
        appearance_layout.setSpacing(14)

        appearance_title = QLabel("Apariencia")
        appearance_title.setObjectName("SectionHeading")
        appearance_layout.addWidget(appearance_title)

        color_label = QLabel("Color de resaltado")
        color_label.setObjectName("SectionHint")
        color_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        appearance_layout.addWidget(color_label)

        color_row = QHBoxLayout()
        color_row.setSpacing(12)
        color_row.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.settings_repo = SettingsRepository()
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self._buttons: dict[str, QToolButton] = {}
        stored_theme = self.settings_repo.get("theme")
        self.selected_theme_name = (
            stored_theme if stored_theme in THEME_REGISTRY else "Pink"
        )
        is_custom_theme = bool(stored_theme and stored_theme.startswith("Custom:"))

        for name, palette in THEME_REGISTRY.items():
            btn = self._make_color_dot(name, palette["accent"]["normal"])
            self.group.addButton(btn)
            self._buttons[name] = btn
            color_row.addWidget(btn)
            if not is_custom_theme and name == self.selected_theme_name:
                btn.setChecked(True)

        appearance_layout.addLayout(color_row)
        self.group.buttonToggled.connect(self._on_theme_toggled)

        custom_row = QHBoxLayout()
        custom_row.setSpacing(10)
        custom_row.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.custom_color_swatch = QFrame()
        self.custom_color_swatch.setObjectName("AccentSwatch")
        self.custom_color_swatch.setFixedSize(28, 28)
        self.custom_color_btn = QPushButton("Elegir color personalizado")
        self.custom_color_btn.setObjectName("AccentPickerBtn")
        self.custom_color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.custom_color_btn.clicked.connect(self._choose_custom_accent)
        custom_row.addWidget(self.custom_color_swatch)
        custom_row.addWidget(self.custom_color_btn)
        appearance_layout.addLayout(custom_row)
        self._update_custom_swatch()

        self.save_btn = QPushButton("Guardar")
        self.save_btn.setObjectName("SaveBtn")
        self.save_btn.setFixedHeight(42)
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.clicked.connect(self._save)
        save_row = QHBoxLayout()
        save_row.addStretch()
        save_row.addWidget(self.save_btn)
        save_row.addStretch()
        appearance_layout.addLayout(save_row)

        self.hint_label = QLabel(
            "Selecciona un color para aplicarlo al instante."
        )
        self.hint_label.setObjectName("HintLabel")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        appearance_layout.addWidget(self.hint_label)

        root.addWidget(appearance_frame)

        user_data_frame = QFrame()
        user_data_frame.setObjectName("UserDataFrame")
        user_data_frame.setFrameStyle(QFrame.Box)
        user_data_frame.setLineWidth(1)
        user_data_layout_outer = QVBoxLayout(user_data_frame)
        user_data_layout_outer.setContentsMargins(16, 16, 16, 16)
        user_data_layout_outer.setSpacing(10)

        user_data_title = QLabel("Datos de usuario")
        user_data_title.setObjectName("SectionHeading")
        user_data_layout_outer.addWidget(user_data_title)

        user_data_layout = QVBoxLayout()
        user_data_layout.setSpacing(8)
        user_data_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.export_btn = QPushButton("Exportar mis datos")
        self.export_btn.setObjectName("UserDataBtn")
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.setMaximumWidth(220)
        self.export_btn.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self.export_btn.clicked.connect(self._export_data_to_zip)
        user_data_layout.addWidget(self.export_btn)

        self.view_btn = QPushButton("Ver mis datos")
        self.view_btn.setObjectName("UserDataBtn")
        self.view_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.view_btn.setMaximumWidth(220)
        self.view_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.view_btn.clicked.connect(self._open_data_folder)
        user_data_layout.addWidget(self.view_btn)

        self.delete_btn = QPushButton("Eliminar mis datos")
        self.delete_btn.setObjectName("DeleteDataBtn")
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.setMaximumWidth(220)
        self.delete_btn.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self.delete_btn.clicked.connect(self._delete_local_data)
        user_data_layout.addWidget(self.delete_btn)

        user_data_layout_outer.addLayout(user_data_layout)
        root.addWidget(user_data_frame)

        root.addStretch()

        self._apply_button_styles()

    def _export_data_to_zip(self):
        data_dir = ensure_app_data_dir()
        default_name = f"xebu-workspace-data-{datetime.now():%Y%m%d-%H%M%S}.zip"
        default_path = str(Path.home() / default_name)
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar Datos",
            default_path,
            "Archivo ZIP (*.zip)",
        )
        if not file_path:
            return

        export_path = Path(file_path)
        if export_path.suffix.lower() != ".zip":
            export_path = export_path.with_suffix(".zip")

        try:
            self._write_data_export(data_dir, export_path)
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Exportar Datos",
                f"No se pudo exportar la carpeta de datos:\n{exc}",
            )
            return

        QMessageBox.information(
            self,
            "Exportar Datos",
            f"Datos exportados correctamente en:\n{export_path}",
        )
        self.hint_label.setText("Datos exportados correctamente.")

    def _open_data_folder(self):
        data_dir = ensure_app_data_dir()
        try:
            open_resource_target(str(data_dir))
        except (OSError, webbrowser.Error) as exc:
            QMessageBox.warning(self, "Ver Datos", f"No se pudo abrir la carpeta:\n{exc}")

    def _delete_local_data(self):
        data_dir = ensure_app_data_dir()
        reply = QMessageBox.question(
            self,
            "Eliminar Datos",
            (
                "Esto eliminara todos los datos locales de XebuWorkspace.\n\n"
                f"Carpeta:\n{data_dir}\n\n"
                "Esta accion no se puede deshacer. Se recomienda exportar "
                "una copia antes de continuar.\n\n"
                "Deseas continuar?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        errors = self._clear_data_dir(data_dir)
        if errors:
            QMessageBox.warning(
                self,
                "Eliminar Datos",
                "Algunos archivos no pudieron eliminarse:\n" + "\n".join(errors[:5]),
            )
            return

        initialize_database()
        QMessageBox.information(
            self,
            "Eliminar Datos",
            "Datos eliminados. Se preparo una base de datos vacia para continuar.",
        )
        self.hint_label.setText(
            "Datos eliminados. Reinicia la app para refrescar vistas abiertas."
        )

    def _write_data_export(self, data_dir: Path, export_path: Path) -> None:
        export_path.parent.mkdir(parents=True, exist_ok=True)
        resolved_export = export_path.resolve()
        with zipfile.ZipFile(export_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(data_dir.rglob("*")):
                if not path.is_file():
                    continue
                if path.resolve() == resolved_export:
                    continue
                zf.write(path, path.relative_to(data_dir))

    def _clear_data_dir(self, data_dir: Path) -> list[str]:
        data_dir.mkdir(parents=True, exist_ok=True)
        errors: list[str] = []
        for child in data_dir.iterdir():
            try:
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
            except OSError as exc:
                errors.append(f"{child}: {exc}")
        return errors

    def _make_color_dot(self, theme_name: str, color_hex: str) -> QToolButton:
        btn = QToolButton(self)
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedSize(38, 38)
        btn.setObjectName("ThemeDot")
        btn.setStyleSheet(f"""
            QToolButton#ThemeDot {{
                background-color: {color_hex};
                border-radius: 19px;
                border: 2px solid #596767;
            }}
            QToolButton#ThemeDot:hover {{
                border-color: #f2f0e8;
            }}
            QToolButton#ThemeDot:checked {{
                border: 3px solid #ffffff;
            }}
            """)
        btn.setToolTip(theme_name)
        return btn

    def _clear_preset_selection(self) -> None:
        self.group.setExclusive(False)
        for btn in self._buttons.values():
            btn.setChecked(False)
        self.group.setExclusive(True)

    def _update_custom_swatch(self) -> None:
        color = theme_manager.current_accent
        self.custom_color_swatch.setStyleSheet(f"""
            QFrame#AccentSwatch {{
                background: {color};
                border: 1px solid #596767;
                border-radius: 6px;
            }}
        """)

    def _choose_custom_accent(self) -> None:
        color = QColorDialog.getColor(
            QColor(theme_manager.current_accent),
            self,
            "Elegir color de resaltado",
        )
        if not color.isValid():
            return
        theme_manager.set_custom_accent(color.name())
        self.settings_repo.upsert("theme", theme_manager.serialize_current_theme())
        self._clear_preset_selection()
        self._update_custom_swatch()
        self.hint_label.setText("Color personalizado aplicado.")

    def _apply_button_styles(self):
        return

    def _on_theme_toggled(self, button: QToolButton, checked: bool):
        if not checked:
            return
        for name, btn in self._buttons.items():
            if btn is button:
                self.selected_theme_name = name
                theme_manager.set_theme(name)
                self.settings_repo.upsert("theme", theme_manager.serialize_current_theme())
                self._update_custom_swatch()
                break

    def _save(self):
        QMessageBox.information(self, "Guardado", "✔ Configuración guardada")
        self.hint_label.setText("✔ Configuración guardada")

    def _export_data(self):
        QMessageBox.information(
            self,
            "Exportar Datos",
            "¡Funcionalidad de exportación próximamente!\n\nEsto te permitirá exportar todos tus datos.",
        )

    def _delete_data(self):
        reply = QMessageBox.question(
            self,
            "Eliminar Datos",
            "¿Estás seguro de que quieres eliminar todos tus datos?\n\nEsta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            QMessageBox.information(
                self,
                "Eliminar Datos",
                "¡Funcionalidad de eliminación próximamente!\n\nTodos tus datos serían eliminados permanentemente.",
            )

    def _view_data(self):
        QMessageBox.information(
            self,
            "Ver Datos",
            "¡Funcionalidad de visualización próximamente!\n\nEsto te mostrará todos tus datos almacenados.",
        )
