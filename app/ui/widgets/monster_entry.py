"""Compact horizontal entry row for a monster (used in In-Work and Catalog rails)."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget


class MonsterEntryRow(QWidget):
    """Image + name + optional badge row. Optionally clickable."""

    clicked = Signal(int)  # monster_id

    def __init__(
        self,
        monster_id: int,
        name: str,
        image_path: str,
        *,
        monster_type: str = "",
        is_placeholder: bool = False,
        badge_text: str = "",
        interactive: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._monster_id = monster_id
        self._interactive = interactive
        self._is_placeholder = is_placeholder
        self._monster_type = monster_type
        self.setObjectName("inworkEntry")

        if interactive:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)

        self._image = QLabel()
        self._image.setFixedSize(QSize(36, 36))
        self._image.setScaledContents(True)
        self._image.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if image_path and not self._is_placeholder:
            pix = QPixmap(image_path)
            if not pix.isNull():
                self._image.setPixmap(pix)
            else:
                self._set_initials(name)
        else:
            self._set_initials(name)
        layout.addWidget(self._image)

        label_text = f"{name} {badge_text}".strip() if badge_text else name
        self._label = QLabel(label_text)
        self._label.setObjectName("inworkEntryName")
        layout.addWidget(self._label, stretch=1)

    def _set_initials(self, name: str) -> None:
        initials = "".join(part[0] for part in name.split()[:2]).upper()
        bg, fg = _PLACEHOLDER_TONES.get(self._monster_type, ("#262332", "#d0bcff"))
        self._image.setText(initials or name[:2].upper())
        self._image.setStyleSheet(
            f"background-color: {bg}; border-radius: 6px; "
            f"font-size: 14px; font-weight: bold; color: {fg};"
        )

    def mousePressEvent(self, event) -> None:
        if self._interactive:
            self.clicked.emit(self._monster_id)
        super().mousePressEvent(event)


_PLACEHOLDER_TONES = {
    "wublin": ("#1a2e31", "#45e9d0"),
    "celestial": ("#352d12", "#ffba20"),
    "amber": ("#38251f", "#ff8a65"),
}
