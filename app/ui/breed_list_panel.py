"""Breed List panel — left side of the home view."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.ui.widgets.egg_row_widget import EggRowWidget

if TYPE_CHECKING:
    from app.ui.viewmodels import BreedListRowViewModel


class BreedListPanel(QWidget):
    increment_requested = Signal(int)  # egg_type_id
    sort_changed = Signal(str)  # sort order string

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._row_widgets: dict[int, EggRowWidget] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 6, 8)

        header = QHBoxLayout()
        title = QLabel("Breed List")
        title.setObjectName("panelTitle")
        header.addWidget(title)
        header.addStretch()

        self._sort_combo = QComboBox()
        self._sort_combo.addItem("Longest breed first", "time_desc")
        self._sort_combo.addItem("Shortest breed first", "time_asc")
        self._sort_combo.addItem("Most remaining first", "remaining_desc")
        self._sort_combo.addItem("Name A–Z", "name_asc")
        self._sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        header.addWidget(self._sort_combo)

        layout.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setObjectName("breedListScroll")

        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(4)
        self._list_layout.addStretch()

        self._empty_label = QLabel("Add monsters from the Catalog to get started")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setObjectName("emptyHint")
        self._list_layout.insertWidget(0, self._empty_label)

        scroll.setWidget(self._list_container)
        layout.addWidget(scroll, stretch=1)

    def set_sort_order(self, order: str) -> None:
        for i in range(self._sort_combo.count()):
            if self._sort_combo.itemData(i) == order:
                self._sort_combo.blockSignals(True)
                self._sort_combo.setCurrentIndex(i)
                self._sort_combo.blockSignals(False)
                break

    def refresh(self, rows: list[BreedListRowViewModel]) -> None:
        incoming_ids = {r.egg_type_id for r in rows}
        # Remove widgets no longer present
        for eid in list(self._row_widgets):
            if eid not in incoming_ids:
                w = self._row_widgets.pop(eid)
                self._list_layout.removeWidget(w)
                w.deleteLater()

        # Update or create widgets
        for idx, row_vm in enumerate(rows):
            if row_vm.egg_type_id in self._row_widgets:
                self._row_widgets[row_vm.egg_type_id].update_data(row_vm)
            else:
                w = EggRowWidget(row_vm)
                w.clicked.connect(self._on_row_clicked)
                self._row_widgets[row_vm.egg_type_id] = w

            w = self._row_widgets[row_vm.egg_type_id]
            current_idx = self._list_layout.indexOf(w)
            if current_idx != idx:
                self._list_layout.removeWidget(w)
                self._list_layout.insertWidget(idx, w)

        self._empty_label.setVisible(len(rows) == 0)

    def on_completion(self, egg_type_id: int) -> None:
        """Trigger ding + fade for a completed row (called before refresh removes it)."""
        w = self._row_widgets.get(egg_type_id)
        if w:
            w.animate_completion()

    def _on_row_clicked(self, egg_type_id: int) -> None:
        self.increment_requested.emit(egg_type_id)

    def _on_sort_changed(self) -> None:
        order = self._sort_combo.currentData()
        if order:
            self.sort_changed.emit(order)
