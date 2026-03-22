"""Home view — two-column layout with Breed List (left) and In-Work Monsters (right)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from app.ui.breed_list_panel import BreedListPanel
from app.ui.inwork_panel import InWorkPanel


class HomeView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("pageCanvas")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 32, 32, 32)
        outer.setSpacing(0)

        columns = QHBoxLayout()
        columns.setSpacing(32)

        self.breed_list_panel = BreedListPanel()
        self.inwork_panel = InWorkPanel()

        columns.addWidget(self.breed_list_panel, stretch=7)
        columns.addWidget(self.inwork_panel, stretch=5)

        outer.addLayout(columns)
