"""In-Work Monsters panel — right side of the home view."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.ui.widgets.monster_card import MonsterCard

if TYPE_CHECKING:
    from app.ui.viewmodels import InWorkMonsterRowViewModel

_TYPE_LABELS = {
    "wublin": "Wublins",
    "celestial": "Celestials",
    "amber": "Amber Vessels",
}
_TYPE_ORDER = ["wublin", "celestial", "amber"]


class InWorkPanel(QWidget):
    close_out_requested = Signal(int)  # monster_id

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cards: list[MonsterCard] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 8, 12, 8)

        title = QLabel("In-Work Monsters")
        title.setObjectName("panelTitle")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(4)
        self._container_layout.addStretch()

        self._empty_label = QLabel("No active targets")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setObjectName("emptyHint")
        self._container_layout.insertWidget(0, self._empty_label)

        scroll.setWidget(self._container)
        layout.addWidget(scroll, stretch=1)

    def refresh(self, inwork_by_type: dict[str, list[InWorkMonsterRowViewModel]]) -> None:
        # Clear existing
        for card in self._cards:
            self._container_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()

        # Remove old section labels
        while self._container_layout.count() > 1:
            item = self._container_layout.takeAt(0)
            if item.widget() and item.widget() is not self._empty_label:
                item.widget().deleteLater()

        has_any = False
        insert_idx = 0

        for mtype in _TYPE_ORDER:
            monsters = inwork_by_type.get(mtype, [])
            if not monsters:
                continue
            has_any = True

            section = QLabel(_TYPE_LABELS.get(mtype, mtype))
            section.setObjectName("sectionLabel")
            self._container_layout.insertWidget(insert_idx, section)
            insert_idx += 1

            for m in monsters:
                badge = f"× {m.count}" if m.count > 1 else ""
                card = MonsterCard(m.monster_id, m.name, m.image_path, badge_text=badge)
                card.setToolTip("Click to close out (removes newest instance)")
                card.clicked.connect(self._on_card_clicked)
                self._container_layout.insertWidget(insert_idx, card)
                self._cards.append(card)
                insert_idx += 1

        self._empty_label.setVisible(not has_any)

    def _on_card_clicked(self, monster_id: int) -> None:
        self.close_out_requested.emit(monster_id)
