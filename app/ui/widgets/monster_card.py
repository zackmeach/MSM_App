"""Monster card widget used in catalog and in-work panel."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QCursor, QPixmap
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


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
        self.setFixedSize(QSize(100, 120))
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 4)
        layout.setSpacing(4)

        self._image = QLabel()
        self._image.setFixedSize(QSize(64, 64))
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

        self.setStyleSheet("""
            #monsterCard {
                background-color: #313244; border-radius: 8px;
            }
            #monsterCard:hover { background-color: #45475a; }
            #cardLabel { font-size: 11px; color: #cdd6f4; }
        """)

    def _set_initials(self, name: str) -> None:
        self._image.setText(name[:2].upper())
        self._image.setStyleSheet(
            "background-color: #45475a; border-radius: 8px; "
            "font-size: 18px; font-weight: bold; color: #89b4fa;"
        )

    def mousePressEvent(self, event) -> None:
        self.clicked.emit(self._monster_id)
        super().mousePressEvent(event)
