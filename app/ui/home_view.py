"""Home view — split panel with Breed List (left) and In-Work (right)."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QSplitter, QWidget

from app.ui.breed_list_panel import BreedListPanel
from app.ui.inwork_panel import InWorkPanel


class HomeView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter()
        self.breed_list_panel = BreedListPanel()
        self.inwork_panel = InWorkPanel()

        splitter.addWidget(self.breed_list_panel)
        splitter.addWidget(self.inwork_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter)
