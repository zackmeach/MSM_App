"""Catalog view — two-column page with browser (left) and active rail (right)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from app.ui.catalog_active_panel import CatalogActivePanel
from app.ui.catalog_browser_panel import CatalogBrowserPanel

if TYPE_CHECKING:
    from app.services.viewmodels import InWorkMonsterRowViewModel, MonsterCatalogItemViewModel


class CatalogView(QWidget):
    """Top-level Catalog page — mirrors HomeView's two-column composition."""

    add_target_requested = Signal(int)  # monster_id
    close_out_requested = Signal(int)  # monster_id

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("pageCanvas")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 32, 32, 32)
        outer.setSpacing(0)

        columns = QHBoxLayout()
        columns.setSpacing(32)

        self._browser = CatalogBrowserPanel()
        self._active = CatalogActivePanel()

        columns.addWidget(self._browser, stretch=7)
        columns.addWidget(self._active, stretch=5)

        outer.addLayout(columns)

        self._browser.add_target_requested.connect(
            self.add_target_requested
        )
        self._active.close_out_requested.connect(
            self.close_out_requested
        )

    def load_catalog(self, items: list[MonsterCatalogItemViewModel]) -> None:
        self._browser.load_catalog(items)

    def refresh_active(
        self, inwork_by_type: dict[str, list[InWorkMonsterRowViewModel]]
    ) -> None:
        self._active.refresh(inwork_by_type)

    def update_active_counts(self, counts: dict[int, int]) -> None:
        """Forward badge-count updates to the browser grid."""
        self._browser.update_active_counts(counts)
