"""Tiny horizontal row of element-sigil pips for a Breed List row."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from app.assets import resolver
from app.ui.themes import element_icon_path, scaled


class ElementPipRow(QWidget):
    """Renders a small icon for each element key, in order."""

    def __init__(
        self,
        elements: tuple[str, ...] = (),
        *,
        size: int = 16,
        spacing: int = 4,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._size = scaled(size)
        self.setObjectName("elementPipRow")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(spacing)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._layout = layout

        self._labels: list[QLabel] = []
        self.set_elements(elements)

    def set_elements(self, elements: tuple[str, ...]) -> None:
        # Clear existing
        for lbl in self._labels:
            self._layout.removeWidget(lbl)
            lbl.deleteLater()
        self._labels.clear()

        for key in elements:
            lbl = QLabel()
            lbl.setFixedSize(QSize(self._size, self._size))
            lbl.setScaledContents(True)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setToolTip(_pretty_element_name(key))
            path = resolver.resolve(element_icon_path(key))
            if path:
                pix = QPixmap(path)
                if not pix.isNull():
                    lbl.setPixmap(pix)
            self._layout.addWidget(lbl)
            self._labels.append(lbl)

        # Hide entirely when empty so layout collapses cleanly.
        self.setVisible(bool(elements))


def _pretty_element_name(key: str) -> str:
    """natural-cold -> 'Natural Cold' for tooltip text."""
    return " ".join(part.capitalize() for part in key.split("-"))
