"""In-Work Monsters panel — right side of the home view."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from app.assets import resolver
from app.ui._active_sections import TYPE_CONFIG, TYPE_ORDER
from app.ui.themes import island_icon_path
from app.ui.widgets.monster_entry import MonsterEntryRow
from app.ui.widgets.section_card import SectionCard
from app.ui.widgets.tip_card import TipCard

if TYPE_CHECKING:
    from app.ui.viewmodels import InWorkMonsterRowViewModel


class InWorkPanel(QWidget):
    close_out_requested = Signal(int)  # monster_id

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("activeRailPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        # Cap the rail width so on wide screens (>=1080p) the section cards
        # don't stretch absurdly far and the badge floats off in space —
        # matches the rail width used on the catalog page.
        self.setMaximumWidth(520)
        self._cards: list[MonsterEntryRow] = []
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

        for mtype in TYPE_ORDER:
            cfg = TYPE_CONFIG[mtype]
            island_path = resolver.resolve(island_icon_path(cfg["island"]))
            section = SectionCard(
                cfg["label"], cfg["icon"], cfg["empty_text"],
                icon_image_path=island_path or None,
                interactive=True,
            )
            self._sections[mtype] = section
            container_layout.addWidget(section)

        container_layout.addStretch()

        self._getting_started = TipCard(
            icon_text="i",
            title="Getting Started",
            body_text=(
                "Use the Catalog to browse available monsters. "
                "Once you start an awakening target, its remaining "
                "egg requirements will appear here and in the Breed List."
            ),
        )
        container_layout.addWidget(self._getting_started)

        scroll.setWidget(container)
        layout.addWidget(scroll, stretch=1)

    def refresh(
        self, inwork_by_type: dict[str, list[InWorkMonsterRowViewModel]]
    ) -> None:
        self._cards.clear()
        total = 0

        for mtype in TYPE_ORDER:
            section = self._sections[mtype]
            monsters = inwork_by_type.get(mtype, [])
            entries = section.refresh(monsters, self._on_card_clicked)
            self._cards.extend(entries)
            total += len(monsters)

        self._count_badge.setText(f"{total} Active" if total else "0 Active")
        self._getting_started.setVisible(total == 0)

    def _on_card_clicked(self, monster_id: int) -> None:
        self.close_out_requested.emit(monster_id)
