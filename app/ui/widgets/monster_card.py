"""Monster card widget used in catalog and in-work panel."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QCursor, QPixmap
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from app.ui.themes import THEMES, get_active_theme, scaled


class MonsterCard(QWidget):
    clicked = Signal(int)  # monster_id

    def __init__(
        self,
        monster_id: int,
        name: str,
        image_path: str,
        *,
        badge_text: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._monster_id = monster_id
        self.setObjectName("monsterCard")
        self.setFixedSize(QSize(scaled(100), scaled(120)))
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 4)
        layout.setSpacing(4)

        self._image = QLabel()
        s = scaled(64)
        self._image.setFixedSize(QSize(s, s))
        self._image.setScaledContents(True)
        self._image.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if image_path:
            pix = QPixmap(image_path)
            if not pix.isNull():
                self._image.setPixmap(pix)
            else:
                self._set_initials(name)
        else:
            self._set_initials(name)
        layout.addWidget(self._image, alignment=Qt.AlignmentFlag.AlignCenter)

        label_text = f"{name} {badge_text}".strip() if badge_text else name
        self._label = QLabel(label_text)
        self._label.setWordWrap(True)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setObjectName("cardLabel")
        layout.addWidget(self._label)

        # Card and label styles are in the central stylesheet (#monsterCard, #cardLabel).

    def _set_initials(self, name: str) -> None:
        self._image.setText(name[:2].upper())
        t = THEMES[get_active_theme()]
        self._image.setStyleSheet(
            f"background-color: {t['elevated']}; border-radius: 8px; "
            f"font-size: 18px; font-weight: bold; color: {t['accent']};"
        )

    def mousePressEvent(self, event) -> None:
        self.clicked.emit(self._monster_id)
        super().mousePressEvent(event)
