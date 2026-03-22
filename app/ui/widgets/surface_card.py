"""Generic styled card surface for non-section contexts (Settings, info panels)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget


class SurfaceCard(QWidget):
    """A rounded, bordered card container matching the app's surface-container palette.

    Use as a parent for any card-like grouping that doesn't need SectionCard's
    monster-group semantics (icon header, dashed body, empty state).

    Pass *object_name* to select a stylesheet variant (e.g. ``"settingsCardLow"``
    for a lower-emphasis surface).
    """

    def __init__(
        self,
        *,
        object_name: str = "settingsCard",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName(object_name)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(24, 24, 24, 24)
        self._layout.setSpacing(16)

    def card_layout(self) -> QVBoxLayout:
        """Return the inner layout so callers can add child widgets."""
        return self._layout
