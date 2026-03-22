"""Image-forward monster card for the Catalog grid."""

from __future__ import annotations

from PySide6.QtCore import QPropertyAnimation, QSize, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QVBoxLayout, QWidget


class CatalogMonsterCard(QWidget):
    """Catalog grid tile — larger image, name, click-to-add with flash feedback."""

    clicked = Signal(int)  # monster_id

    CARD_WIDTH = 172
    CARD_HEIGHT = 230
    IMAGE_SIZE = 140

    def __init__(
        self,
        monster_id: int,
        name: str,
        image_path: str,
        *,
        monster_type: str = "",
        is_placeholder: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._monster_id = monster_id
        self._is_placeholder = is_placeholder
        self._monster_type = monster_type
        self.setObjectName("catalogCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedSize(QSize(self.CARD_WIDTH, self.CARD_HEIGHT))
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 10)
        layout.setSpacing(10)

        self._image = QLabel()
        self._image.setFixedSize(QSize(self.IMAGE_SIZE, self.IMAGE_SIZE))
        self._image.setScaledContents(True)
        self._image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image.setObjectName("catalogCardImage")
        self._image.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        if image_path and not self._is_placeholder:
            pix = QPixmap(image_path)
            if not pix.isNull():
                self._image.setPixmap(pix)
            else:
                self._set_initials(name)
        else:
            self._set_initials(name)
        layout.addWidget(self._image, alignment=Qt.AlignmentFlag.AlignCenter)

        self._label = QLabel(name)
        self._label.setObjectName("catalogCardName")
        self._label.setWordWrap(True)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._label)

    def _set_initials(self, name: str) -> None:
        initials = "".join(part[0] for part in name.split()[:2]).upper()
        bg, border, fg = _PLACEHOLDER_TONES.get(
            self._monster_type,
            ("#262332", "#343046", "#d0bcff"),
        )
        self._image.setText(initials or name[:2].upper())
        self._image.setStyleSheet(
            f"background-color: {bg}; border: 1px solid {border}; border-radius: 12px; "
            f"font-size: 28px; font-weight: bold; color: {fg};"
        )

    def flash_added(self) -> None:
        """Brief opacity pulse to acknowledge an add."""
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(200)
        anim.setStartValue(0.4)
        anim.setEndValue(1.0)
        anim.finished.connect(lambda: self.setGraphicsEffect(None))
        anim.start()
        self._flash_anim = anim

    def mousePressEvent(self, event) -> None:
        self.clicked.emit(self._monster_id)
        self.flash_added()
        super().mousePressEvent(event)


_PLACEHOLDER_TONES = {
    "wublin": ("#1a2e31", "#275058", "#45e9d0"),
    "celestial": ("#352d12", "#5c4810", "#ffba20"),
    "amber": ("#38251f", "#6a3b2d", "#ff8a65"),
}
