"""Floating toast notification that auto-fades."""

from __future__ import annotations

from PySide6.QtCore import QPropertyAnimation, QTimer, Qt
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel, QWidget


class ToastWidget(QLabel):
    """Bottom-center floating notification that fades out after a delay."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("toast")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setFixedHeight(40)
        self.hide()

    def show_message(self, text: str, duration_ms: int = 2000) -> None:
        self.setText(text)
        self.adjustSize()
        width = max(self.sizeHint().width() + 40, 200)
        self.setFixedWidth(width)
        self._reposition()
        self.setGraphicsEffect(None)
        self.show()
        self.raise_()

        QTimer.singleShot(duration_ms, self._fade_out)

    def _reposition(self) -> None:
        p = self.parent()
        if p is None:
            return
        x = (p.width() - self.width()) // 2
        y = p.height() - self.height() - 24
        self.move(x, y)

    def _fade_out(self) -> None:
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(400)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.finished.connect(self.hide)
        anim.start()
        self._anim = anim
