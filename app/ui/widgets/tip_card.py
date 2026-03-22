"""Reusable tip / getting-started card widget."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget


class TipCard(QWidget):
    """Contextual help card with icon, title, and body text."""

    def __init__(
        self,
        icon_text: str = "\U0001f52e",
        title: str = "Getting Started",
        body_text: str = "",
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("gettingStartedCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        icon = QLabel(icon_text)
        icon.setObjectName("gettingStartedIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon, alignment=Qt.AlignmentFlag.AlignTop)

        text_col = QVBoxLayout()
        text_col.setSpacing(4)

        heading = QLabel(title)
        heading.setObjectName("gettingStartedTitle")
        text_col.addWidget(heading)

        desc = QLabel(body_text)
        desc.setObjectName("gettingStartedText")
        desc.setWordWrap(True)
        text_col.addWidget(desc)

        layout.addLayout(text_col, stretch=1)
