"""Catalog browser panel — left column with search, tabs, and monster grid."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.ui.themes import scaled
from app.ui.widgets.catalog_monster_card import CatalogMonsterCard

if TYPE_CHECKING:
    from app.ui.viewmodels import MonsterCatalogItemViewModel

_TAB_TYPES = [
    ("Wublins", "wublin"),
    ("Celestials", "celestial"),
    ("Amber Vessels", "amber"),
]


class CatalogBrowserPanel(QWidget):
    """Search, type tabs, and responsive monster-card grid."""

    add_target_requested = Signal(int)  # monster_id

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("catalogBrowserPanel")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._all_items: list[MonsterCatalogItemViewModel] = []
        self._current_tab: str = _TAB_TYPES[0][1]
        self._cards: list[CatalogMonsterCard] = []
        self._last_col_count: int = 0
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title = QLabel("Monster Catalog")
        title.setObjectName("panelTitle")
        layout.addWidget(title)

        subtitle = QLabel(
            "Browse Wublins, Celestials, and Amber Vessels, "
            "then click once to begin tracking."
        )
        subtitle.setObjectName("catalogSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)
        layout.addSpacing(16)

        search_row = QWidget()
        search_row.setObjectName("catalogSearchRow")
        search_row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        search_l = QHBoxLayout(search_row)
        search_l.setContentsMargins(14, 0, 14, 0)
        search_l.setSpacing(10)

        search_icon = QLabel("\u2315")
        search_icon.setObjectName("catalogSearchIcon")
        search_l.addWidget(search_icon)

        self._search = QLineEdit()
        self._search.setObjectName("catalogSearch")
        self._search.setPlaceholderText("Search monsters by name\u2026")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._on_search)
        search_l.addWidget(self._search)
        layout.addWidget(search_row)
        layout.addSpacing(16)

        tab_row = QHBoxLayout()
        tab_row.setObjectName("catalogTabBar")
        tab_row.setSpacing(0)
        self._tab_btns: list[QPushButton] = []
        for label, mtype in _TAB_TYPES:
            btn = QPushButton(label)
            btn.setObjectName("catalogTabBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFocusPolicy(Qt.FocusPolicy.TabFocus)
            btn.clicked.connect(lambda checked=False, t=mtype: self._on_tab(t))
            self._tab_btns.append(btn)
            tab_row.addWidget(btn)
        tab_row.addStretch()
        layout.addLayout(tab_row)
        layout.addSpacing(16)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("catalogGridScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._scroll.viewport().setObjectName("catalogGridViewport")
        self._scroll.viewport().setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._grid_container = QWidget()
        self._grid_container.setObjectName("catalogGridContainer")
        self._grid_container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        grid_outer = QVBoxLayout(self._grid_container)
        grid_outer.setContentsMargins(0, 0, 0, 0)
        grid_outer.setSpacing(0)

        self._grid_inner = QWidget()
        self._grid_layout = QGridLayout(self._grid_inner)
        self._grid_layout.setSpacing(20)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_outer.addWidget(self._grid_inner)

        self._no_results = QLabel("\U0001f50d  No monsters match your search")
        self._no_results.setObjectName("catalogNoResults")
        self._no_results.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._no_results.setVisible(False)
        grid_outer.addWidget(self._no_results)

        grid_outer.addStretch()
        self._scroll.setWidget(self._grid_container)
        layout.addWidget(self._scroll, stretch=1)

        self._set_active_tab(self._current_tab)

    # ── Public API ──

    def load_catalog(self, items: list[MonsterCatalogItemViewModel]) -> None:
        self._all_items = list(items)
        self._apply_filter()

    def update_active_counts(self, counts: dict[int, int]) -> None:
        """Update badge counts on visible cards without rebuilding the grid."""
        for card in self._cards:
            card.set_active_count(counts.get(card._monster_id, 0))

    # ── Internal ──

    def _on_search(self, _text: str) -> None:
        self._apply_filter()

    def _on_tab(self, mtype: str) -> None:
        self._current_tab = mtype
        self._set_active_tab(mtype)
        self._apply_filter()

    def _set_active_tab(self, mtype: str) -> None:
        for i, (_, t) in enumerate(_TAB_TYPES):
            btn = self._tab_btns[i]
            btn.setProperty("active", t == mtype)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _apply_filter(self) -> None:
        needle = self._search.text().lower()
        visible = [
            it for it in self._all_items
            if it.monster_type == self._current_tab
            and needle in it.name.lower()
        ]
        self._populate_grid(visible)

    def _populate_grid(self, items: list[MonsterCatalogItemViewModel]) -> None:
        for c in self._cards:
            self._grid_layout.removeWidget(c)
            c.deleteLater()
        self._cards.clear()

        cols = self._compute_columns()

        for idx, it in enumerate(items):
            card = CatalogMonsterCard(
                it.monster_id,
                it.name,
                it.image_path,
                monster_type=it.monster_type,
                is_placeholder=it.is_placeholder,
            )
            card.set_active_count(it.active_count)
            card.clicked.connect(self._on_card_clicked)
            row = idx // cols
            col = idx % cols
            self._grid_layout.addWidget(card, row, col)
            self._cards.append(card)

        has_items = bool(items)
        self._grid_inner.setVisible(has_items)
        self._no_results.setVisible(not has_items and bool(self._search.text()))

    def _compute_columns(self) -> int:
        card_w = scaled(CatalogMonsterCard.CARD_WIDTH)
        spacing = self._grid_layout.spacing()
        available = self._scroll.viewport().width() if self._scroll.viewport() else 480
        cols = max(2, available // (card_w + spacing))
        return min(cols, 5)

    def _on_card_clicked(self, monster_id: int) -> None:
        self.add_target_requested.emit(monster_id)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        new_cols = self._compute_columns()
        if new_cols != self._last_col_count and self._cards:
            self._last_col_count = new_cols
            self._apply_filter()
