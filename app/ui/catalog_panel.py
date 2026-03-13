"""Monster Catalog panel — tabbed grid with search."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.ui.widgets.monster_card import MonsterCard

if TYPE_CHECKING:
    from app.ui.viewmodels import MonsterCatalogItemViewModel

_TAB_TYPES = [
    ("Wublins", "wublin"),
    ("Celestials", "celestial"),
    ("Amber Vessels", "amber"),
]


class CatalogPanel(QWidget):
    add_target_requested = Signal(int)  # monster_id

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._all_items: list[MonsterCatalogItemViewModel] = []
        self._tab_grids: dict[str, _GridContainer] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        title = QLabel("Monster Catalog")
        title.setObjectName("panelTitle")
        layout.addWidget(title)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search monsters\u2026")
        self._search.textChanged.connect(self._on_search)
        layout.addWidget(self._search)

        self._tabs = QTabWidget()
        for label, mtype in _TAB_TYPES:
            grid = _GridContainer()
            self._tab_grids[mtype] = grid
            self._tabs.addTab(grid, label)
        layout.addWidget(self._tabs, stretch=1)

    def load_catalog(self, items: list[MonsterCatalogItemViewModel]) -> None:
        self._all_items = list(items)
        self._apply_filter("")

    def _on_search(self, text: str) -> None:
        self._apply_filter(text)

    def _apply_filter(self, needle: str) -> None:
        needle_lower = needle.lower()
        for mtype, grid in self._tab_grids.items():
            filtered = [
                it for it in self._all_items
                if it.monster_type == mtype and needle_lower in it.name.lower()
            ]
            grid.populate(filtered, self._on_card_clicked)

    def _on_card_clicked(self, monster_id: int) -> None:
        self.add_target_requested.emit(monster_id)


class _GridContainer(QScrollArea):
    """Scrollable area displaying monster cards in a responsive grid."""

    COLUMN_COUNT = 4

    def __init__(self) -> None:
        super().__init__()
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._inner = QWidget()
        self._grid = QGridLayout(self._inner)
        self._grid.setSpacing(10)
        self._grid.setContentsMargins(8, 8, 8, 8)
        self.setWidget(self._inner)
        self._cards: list[MonsterCard] = []

    def populate(self, items: list, on_click) -> None:
        for c in self._cards:
            self._grid.removeWidget(c)
            c.deleteLater()
        self._cards.clear()

        for idx, it in enumerate(items):
            card = MonsterCard(it.monster_id, it.name, it.image_path)
            card.clicked.connect(on_click)
            row = idx // self.COLUMN_COUNT
            col = idx % self.COLUMN_COUNT
            self._grid.addWidget(card, row, col)
            self._cards.append(card)
