"""Image-forward monster card for the Catalog grid."""

from __future__ import annotations

from PySide6.QtCore import QPropertyAnimation, QSize, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QVBoxLayout, QWidget

from app.ui.themes import placeholder_tones_3, scaled


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
        card_w = scaled(self.CARD_WIDTH)
        card_h = scaled(self.CARD_HEIGHT)
        img_sz = scaled(self.IMAGE_SIZE)
        self.setFixedSize(QSize(card_w, card_h))
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 10)
        layout.setSpacing(10)

        self._image = QLabel()
        self._image.setFixedSize(QSize(img_sz, img_sz))
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

        # iOS-style active-count badge (floats over card, not in layout)
        self._badge = QLabel(self)
        self._badge.setObjectName("catalogBadge")
        self._badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._badge.hide()

    @property
    def monster_id(self) -> int:
        return self._monster_id

    def set_active_count(self, count: int) -> None:
        """Show/hide the iOS-style notification badge with the active count."""
        if count <= 0:
            self._badge.hide()
            return

        self._badge.setText(str(count))
        # adjustSize() / sizeHint() return the bare-text size (~6px) until a
        # full paint cycle realises QSS. Compute the rendered size directly
        # from the QSS spec instead — min-width 20+offset, padding 0 5px
        # left/right, height locked at 20+offset. Add a few extra px for
        # multi-digit counts so they aren't truncated.
        text_w = self._badge.fontMetrics().horizontalAdvance(str(count))
        badge_w = max(scaled(20) + 10, text_w + 10)
        badge_h = scaled(20)
        self._badge.setFixedSize(badge_w, badge_h)
        # 10px inset keeps the badge clear of the card's 12px border-radius.
        self._badge.move(self.width() - badge_w - 10, 10)
        self._badge.show()
        self._badge.raise_()

    def _set_initials(self, name: str) -> None:
        initials = "".join(part[0] for part in name.split()[:2]).upper()
        bg, border, fg = placeholder_tones_3(self._monster_type)
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


