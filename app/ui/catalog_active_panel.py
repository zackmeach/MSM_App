"""Catalog active-monsters rail — interactive right column."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from app.ui.widgets.monster_entry import MonsterEntryRow
from app.ui.widgets.section_card import SectionCard
from app.ui.widgets.tip_card import TipCard

if TYPE_CHECKING:
    from app.ui.viewmodels import InWorkMonsterRowViewModel

_TYPE_ORDER = ["wublin", "celestial", "amber"]

_TYPE_CONFIG = {
    "wublin": {
        "label": "Wublins",
        "icon": "\u03df",
        "empty_text": "All Wublins still slumbering on their pedestals\u2026",
    },
    "celestial": {
        "label": "Celestials",
        "icon": "\u2726",
        "empty_text": "The Celestial realm awaits its first spark\u2026",
    },
    "amber": {
        "label": "Amber Vessels",
        "icon": "\u25c8",
        "empty_text": "No amber echoes stirring in the deep\u2026",
    },
}


class CatalogActivePanel(QWidget):
    """Right-side summary of currently active monsters."""

    close_out_requested = Signal(int)  # monster_id

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("activeRailPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._entries: list[MonsterEntryRow] = []
        self._sections: dict[str, SectionCard] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(24)

        header = QHBoxLayout()
        header.setSpacing(8)
        title = QLabel("Active Monsters")
        title.setObjectName("panelTitle")
        header.addWidget(title)
        header.addStretch()
        self._count_badge = QLabel("0 Active")
        self._count_badge.setObjectName("activeBadge")
        header.addWidget(self._count_badge)
        layout.addLayout(header)

        scroll = QScrollArea()
        scroll.setObjectName("activeRailScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.viewport().setObjectName("activeRailViewport")
        scroll.viewport().setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        container = QWidget()
        container.setObjectName("activeRailContent")
        container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(16)

        for mtype in _TYPE_ORDER:
            cfg = _TYPE_CONFIG[mtype]
            section = SectionCard(
                cfg["label"], cfg["icon"], cfg["empty_text"],
                interactive=True,
            )
            self._sections[mtype] = section
            container_layout.addWidget(section)

        container_layout.addStretch()

        self._tip = TipCard(
            icon_text="i",
            title="Getting Started",
            body_text=(
                "Click any monster in the grid to start tracking it. "
                "Your active targets will appear here."
            ),
        )
        container_layout.addWidget(self._tip)

        scroll.setWidget(container)
        layout.addWidget(scroll, stretch=1)

    def refresh(
        self, inwork_by_type: dict[str, list[InWorkMonsterRowViewModel]]
    ) -> None:
        self._entries.clear()
        total = 0

        for mtype in _TYPE_ORDER:
            section = self._sections[mtype]
            monsters = inwork_by_type.get(mtype, [])
            entries = section.refresh(monsters, self._on_entry_clicked)
            self._entries.extend(entries)
            total += len(monsters)

        self._count_badge.setText(f"{total} Active" if total else "0 Active")
        self._tip.setVisible(total == 0)

    def _on_entry_clicked(self, monster_id: int) -> None:
        self.close_out_requested.emit(monster_id)
