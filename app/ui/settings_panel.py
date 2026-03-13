"""Settings panel — version info, update system, BBB disclaimer."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

if TYPE_CHECKING:
    from app.ui.viewmodels import SettingsViewModel


class SettingsPanel(QWidget):
    check_update_requested = Signal()
    apply_update_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._update_available = False
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

        self._update_btn = QPushButton("Check for Content Updates")
        self._update_btn.clicked.connect(self._on_update_btn)
        layout.addWidget(self._update_btn)

        self._status_label = QLabel("")
        self._status_label.setObjectName("updateStatus")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

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
        self._version_label.setText(
            f"App version: {vm.app_version}  |  Content version: {vm.content_version}"
        )
        self._updated_label.setText(f"Last updated: {vm.last_updated_display}")
        self._disclaimer.setText(vm.disclaimer_text)

    def set_status(self, text: str) -> None:
        self._status_label.setText(text)

    def set_update_available(self, available: bool, remote_version: str = "") -> None:
        self._update_available = available
        if available:
            self._update_btn.setText(f"Install Content Update ({remote_version})")
            self._status_label.setText(f"Content update available: {remote_version}")
        else:
            self._update_btn.setText("Check for Content Updates")

    def set_busy(self, busy: bool) -> None:
        self._update_btn.setEnabled(not busy)

    def _on_update_btn(self) -> None:
        if self._update_available:
            self.apply_update_requested.emit()
        else:
            self.check_update_requested.emit()
