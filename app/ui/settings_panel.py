"""Settings panel — version info, update button (stub), BBB disclaimer."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

if TYPE_CHECKING:
    from app.ui.viewmodels import SettingsViewModel


class SettingsPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(12)

        title = QLabel("Settings")
        title.setObjectName("panelTitle")
        layout.addWidget(title)

        self._version_label = QLabel("Content version: —")
        layout.addWidget(self._version_label)

        self._updated_label = QLabel("Last updated: —")
        layout.addWidget(self._updated_label)

        self._update_btn = QPushButton("Check for Updates")
        self._update_btn.setEnabled(False)
        layout.addWidget(self._update_btn)

        layout.addSpacing(20)

        disclaimer_title = QLabel("Disclaimer")
        disclaimer_title.setObjectName("sectionLabel")
        layout.addWidget(disclaimer_title)

        self._disclaimer = QLabel()
        self._disclaimer.setWordWrap(True)
        self._disclaimer.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._disclaimer.setObjectName("disclaimerText")
        layout.addWidget(self._disclaimer)

        layout.addStretch()

    def refresh(self, vm: SettingsViewModel) -> None:
        self._version_label.setText(f"Content version: {vm.content_version}")
        self._updated_label.setText(f"Last updated: {vm.last_updated_display}")
        self._disclaimer.setText(vm.disclaimer_text)
