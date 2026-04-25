"""Horizontal row of small monster avatars showing who consumes this egg."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from app.ui.themes import placeholder_tones_3, scaled

if TYPE_CHECKING:
    from app.ui.viewmodels import ConsumerCardViewModel


_MAX_VISIBLE = 6


class ConsumerCardRow(QWidget):
    """Compact pip-row of monster avatars. Caps at 6 visible + '+N' chip."""

    def __init__(
        self,
        cards: tuple["ConsumerCardViewModel", ...] = (),
        *,
        size: int = 22,
        spacing: int = 4,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._size = scaled(size)
        self.setObjectName("consumerCardRow")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(spacing)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._layout = layout

        self._labels: list[QLabel] = []
        self.set_cards(cards)

    def set_cards(self, cards: tuple["ConsumerCardViewModel", ...]) -> None:
        for lbl in self._labels:
            self._layout.removeWidget(lbl)
            lbl.deleteLater()
        self._labels.clear()

        visible = cards[:_MAX_VISIBLE]
        overflow = len(cards) - len(visible)

        for c in visible:
            lbl = self._make_avatar(c)
            self._layout.addWidget(lbl)
            self._labels.append(lbl)

        if overflow > 0:
            chip = QLabel(f"+{overflow}")
            chip.setFixedSize(QSize(self._size, self._size))
            chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
            bg, _border, fg = placeholder_tones_3("")  # neutral fallback tones
            chip.setStyleSheet(
                f"background-color: {bg}; border-radius: {self._size // 2}px; "
                f"color: {fg}; font-size: 10px; font-weight: 700;"
            )
            chip.setToolTip(_overflow_tooltip(cards[_MAX_VISIBLE:]))
            self._layout.addWidget(chip)
            self._labels.append(chip)

        self.setVisible(bool(cards))

    def _make_avatar(self, c: "ConsumerCardViewModel") -> QLabel:
        lbl = QLabel()
        lbl.setFixedSize(QSize(self._size, self._size))
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setToolTip(c.name)

        bg, border, fg = placeholder_tones_3(c.monster_type)

        pix = QPixmap(c.image_path) if c.image_path and not c.is_placeholder else QPixmap()
        if not pix.isNull():
            lbl.setPixmap(_circular_pixmap(pix, self._size, border))
            # Reset stylesheet — pixmap is fully painted including the ring.
            lbl.setStyleSheet("background: transparent;")
        else:
            initials = "".join(part[0] for part in c.name.split()[:2]).upper() or c.name[:2].upper()
            lbl.setText(initials)
            lbl.setStyleSheet(
                f"background-color: {bg}; border: 1px solid {border}; "
                f"border-radius: {self._size // 2}px; color: {fg}; "
                f"font-size: 9px; font-weight: 700;"
            )
        return lbl


def _circular_pixmap(src: QPixmap, size: int, ring_color: str) -> QPixmap:
    """Render `src` as a circular avatar with a 1-px ring in `ring_color`."""
    out = QPixmap(size, size)
    out.fill(Qt.GlobalColor.transparent)

    painter = QPainter(out)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        path = QPainterPath()
        path.addEllipse(0.5, 0.5, size - 1, size - 1)
        painter.setClipPath(path)

        scaled_src = src.scaled(
            size,
            size,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = (size - scaled_src.width()) // 2
        y = (size - scaled_src.height()) // 2
        painter.drawPixmap(x, y, scaled_src)

        painter.setClipping(False)
        from PySide6.QtGui import QPen, QColor

        pen = QPen(QColor(ring_color))
        pen.setWidthF(1.2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(0.5, 0.5, size - 1, size - 1)
    finally:
        painter.end()
    return out


def _overflow_tooltip(remaining: tuple["ConsumerCardViewModel", ...]) -> str:
    return "\n".join(c.name for c in remaining)
