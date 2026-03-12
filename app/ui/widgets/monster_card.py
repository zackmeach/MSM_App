"""Monster card widget used in catalog and in-work panel."""

from __future__ import annotations

from PySide6.QtCore import QSize, Signal
from PySide6.QtGui import QPixmap
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

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        self._image = QLabel()
        self._image.setFixedSize(QSize(64, 64))
        self._image.setScaledContents(True)
        self._image.setAlignment(
            __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.AlignmentFlag.AlignCenter
        )
        if image_path:
            pix = QPixmap(image_path)
            if not pix.isNull():
                self._image.setPixmap(pix)
            else:
                self._image.setText(name[:2])
        else:
            self._image.setText(name[:2])
        layout.addWidget(self._image)

        label_text = f"{name} {badge_text}".strip() if badge_text else name
        self._label = QLabel(label_text)
        self._label.setWordWrap(True)
        self._label.setObjectName("cardLabel")
        layout.addWidget(self._label)

        self.setStyleSheet("""
            #monsterCard {
                background-color: #313244; border-radius: 8px;
            }
            #monsterCard:hover { background-color: #45475a; }
            #cardLabel { font-size: 11px; }
        """)

    def mousePressEvent(self, event) -> None:
        self.clicked.emit(self._monster_id)
        super().mousePressEvent(event)
