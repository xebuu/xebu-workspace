from __future__ import annotations

import shutil
import webbrowser
import zipfile
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
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
        title.setStyleSheet("font-size: 24px; letter-spacing: 0.5px;")
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
        appearance_title.setStyleSheet(
            "font-size: 16px; font-weight: 700; letter-spacing: 0.2px;"
        )
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

        for name, palette in THEME_REGISTRY.items():
            btn = self._make_color_dot(name, palette["accent"]["normal"])
            self.group.addButton(btn)
            self._buttons[name] = btn
            color_row.addWidget(btn)
            if name == self.selected_theme_name:
                btn.setChecked(True)

        appearance_layout.addLayout(color_row)
        self.group.buttonToggled.connect(self._on_theme_toggled)

        mode_label = QLabel("Modo de visualización")
        mode_label.setObjectName("SectionHint")
        mode_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        appearance_layout.addWidget(mode_label)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(0)
        mode_row.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        self._mode_buttons: dict[str, QToolButton] = {}
        self.selected_mode = "Dark"

        for mode in ("Dark", "Light"):
            btn = self._make_mode_button(mode)
            self.mode_group.addButton(btn)
            self._mode_buttons[mode] = btn
            mode_row.addWidget(btn)
            if mode == self.selected_mode:
                btn.setChecked(True)

        appearance_layout.addLayout(mode_row)
        self.mode_group.buttonToggled.connect(self._on_mode_toggled)

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
            "Selecciona un color y guarda para aplicar los cambios."
        )
        self.hint_label.setObjectName("HintLabel")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.hint_label.setStyleSheet("color: #8cbfdd; font-weight: 600;")
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
        user_data_title.setStyleSheet(
            "font-size: 16px; font-weight: 700; letter-spacing: 0.2px;"
        )
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
        self.delete_btn.setObjectName("UserDataBtn")
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
                border: 2px solid rgba(255, 255, 255, 0.35);
            }}
            QToolButton#ThemeDot:hover {{
                border-color: rgba(255, 255, 255, 0.65);
            }}
            QToolButton#ThemeDot:checked {{
                border: 3px solid #ffffff;
            }}
            """)
        btn.setToolTip(theme_name)
        return btn

    def _make_mode_button(self, mode_name: str) -> QToolButton:
        btn = QToolButton(self)
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedSize(100, 34)
        btn.setObjectName("ModeBtn")
        btn.setText(mode_name)
        btn.setStyleSheet("""
            QToolButton#ModeBtn {
                border: 1px solid #4b4b4b;
                background: transparent;
                color: #c9c9c9;
                font-weight: 600;
            }
            QToolButton#ModeBtn:first-of-type {
                border-top-left-radius: 8px;
                border-bottom-left-radius: 8px;
            }
            QToolButton#ModeBtn:last-of-type {
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
                border-left: none;
            }
            QToolButton#ModeBtn:checked {
                background: #2b2b2b;
                border-color: #6cc1ff;
                color: #ffffff;
            }
            """)
        return btn

    def _apply_button_styles(self):
        self.save_btn.setStyleSheet("""
            QPushButton#SaveBtn {
                background: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #5b8be8, stop:1 #3c71d5);
                color: white;
                border: none;
                border-radius: 10px;
                letter-spacing: 0.4px;
                font-weight: 700;
                padding: 10px 28px;
            }
            QPushButton#SaveBtn:hover {
                opacity: 0.9;
            }
            """)

        secondary_style = """
            QPushButton#UserDataBtn {
                border: 1px solid #3c3c3c;
                border-radius: 8px;
                background: #1d1d1d;
                color: #cfcfcf;
                padding: 8px 14px;
                text-align: left;
                font-weight: 600;
            }
            QPushButton#UserDataBtn:hover {
                border-color: #5f5f5f;
            }
        """

        for btn in (self.export_btn, self.view_btn):
            btn.setStyleSheet(secondary_style)

        self.delete_btn.setStyleSheet("""
            QPushButton#UserDataBtn {
                border: 1px solid #8b3a3a;
                border-radius: 8px;
                background: #2b1a1a;
                color: #f7b0b0;
                padding: 8px 14px;
                font-weight: 600;
            }
            QPushButton#UserDataBtn:hover {
                background: #391e1e;
            }
            """)

    def _on_theme_toggled(self, button: QToolButton, checked: bool):
        if not checked:
            return
        for name, btn in self._buttons.items():
            if btn is button:
                self.selected_theme_name = name
                theme_manager.set_theme(name)
                self.settings_repo.upsert("theme", name)
                break

    def _on_mode_toggled(self, button: QToolButton, checked: bool):
        if not checked:
            return
        for name, btn in self._mode_buttons.items():
            if btn is button:
                self.selected_mode = name
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
