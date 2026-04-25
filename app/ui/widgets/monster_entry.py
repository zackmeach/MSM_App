"""Compact horizontal entry row for a monster (used in In-Work and Catalog rails)."""

from __future__ import annotations

from PySide6.QtCore import QPropertyAnimation, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGraphicsOpacityEffect, QHBoxLayout, QLabel, QWidget

from app.ui.themes import placeholder_tones_2, scaled


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
        self._press_pending = False
        self.setObjectName("inworkEntry")

        if interactive:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)

        self._image = QLabel()
        s = scaled(36)
        self._image.setFixedSize(QSize(s, s))
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
        bg, fg = placeholder_tones_2(self._monster_type)
        self._image.setText(initials or name[:2].upper())
        self._image.setStyleSheet(
            f"background-color: {bg}; border-radius: 6px; "
            f"font-size: 14px; font-weight: bold; color: {fg};"
        )

    def _flash_and_emit(self) -> None:
        """Brief opacity pulse then emit clicked signal after a short delay."""
        if self._press_pending:
            return
        self._press_pending = True
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(150)
        anim.setStartValue(0.4)
        anim.setEndValue(1.0)
        anim.start()
        self._press_anim = anim  # prevent GC

        def _emit_and_clear() -> None:
            # Clear before emit so any synchronous handler that doesn't trigger
            # a state_changed rebuild (e.g. AppService.handle_close_out's
            # early-return path) leaves the row clickable again.
            self._press_pending = False
            self.clicked.emit(self._monster_id)

        QTimer.singleShot(150, _emit_and_clear)

    def mousePressEvent(self, event) -> None:
        if self._interactive:
            self._flash_and_emit()
        super().mousePressEvent(event)


