"""Reusable labelled key/value row for metadata display cards."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget


class InfoRowWidget(QWidget):
    """A single key-value metadata row with an optional bottom divider.

    The *label* is displayed upper-case on the left; *value* is displayed
    bold/accent on the right.  Call :meth:`set_value` to update at runtime.
    """

    def __init__(
        self,
        label: str,
        value: str = "",
        *,
        show_divider: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        row = QHBoxLayout()
        row.setContentsMargins(0, 8, 0, 8)

        self._label = QLabel(label.upper())
        self._label.setObjectName("settingsInfoLabel")
        row.addWidget(self._label)

        row.addStretch()

        self._value = QLabel(value)
        self._value.setObjectName("settingsInfoValue")
        self._value.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        row.addWidget(self._value)

        root.addLayout(row)

        if show_divider:
            divider = QWidget()
            divider.setObjectName("settingsInfoDivider")
            divider.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            divider.setFixedHeight(1)
            root.addWidget(divider)

    def set_value(self, text: str) -> None:
        """Replace the displayed value text."""
        self._value.setText(text)
