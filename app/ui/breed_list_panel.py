"""Breed List panel — left side of the home view."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.ui.widgets.egg_row_widget import EggRowWidget

if TYPE_CHECKING:
    from app.services.audio_player import AudioPlayer
    from app.ui.viewmodels import BreedListRowViewModel


class BreedListPanel(QWidget):
    increment_requested = Signal(int)  # egg_type_id
    sort_changed = Signal(str)  # sort order string
    navigate_to_catalog = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._row_widgets: dict[int, EggRowWidget] = {}
        self._audio: "AudioPlayer | None" = None
        self._build_ui()

    def set_audio(self, audio: "AudioPlayer") -> None:
        """Inject the audio player so newly-built rows can play click/closeout sfx."""
        self._audio = audio

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Header row ──
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 24)

        title = QLabel("Breed List")
        title.setObjectName("panelTitle")
        header.addWidget(title)
        header.addStretch()

        self._active_badge = QLabel("0 Active")
        self._active_badge.setObjectName("activeBadge")
        header.addWidget(self._active_badge)
        header.addSpacing(8)

        self._sort_combo = QComboBox()
        self._sort_combo.addItem("Longest breed first", "time_desc")
        self._sort_combo.addItem("Shortest breed first", "time_asc")
        self._sort_combo.addItem("Most remaining first", "remaining_desc")
        self._sort_combo.addItem("Name A\u2013Z", "name_asc")
        self._sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        header.addWidget(self._sort_combo)

        layout.addLayout(header)

        # ── Empty state ──
        self._empty_state = _BreedListEmptyState()
        self._empty_state.catalog_requested.connect(self.navigate_to_catalog)
        layout.addWidget(self._empty_state, stretch=1)

        # ── Scrollable list (populated state) ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setObjectName("breedListScroll")
        scroll.viewport().setObjectName("breedListViewport")
        scroll.viewport().setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._list_container = QWidget()
        self._list_container.setObjectName("breedListContainer")
        self._list_container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(6)
        self._list_layout.addStretch()

        scroll.setWidget(self._list_container)
        self._scroll_area = scroll
        layout.addWidget(scroll, stretch=1)

        self._update_visibility(0)

    # ── Public API ──

    def set_sort_order(self, order: str) -> None:
        for i in range(self._sort_combo.count()):
            if self._sort_combo.itemData(i) == order:
                self._sort_combo.blockSignals(True)
                self._sort_combo.setCurrentIndex(i)
                self._sort_combo.blockSignals(False)
                break

    def refresh(self, rows: list[BreedListRowViewModel]) -> None:
        incoming_ids = {r.egg_type_id for r in rows}
        for eid in list(self._row_widgets):
            if eid not in incoming_ids:
                w = self._row_widgets[eid]
                # Don't tear down a row mid-completion-animation — it removes
                # the QPropertyAnimation's target and Qt logs warnings.  The
                # widget will emit completion_finished when the animation ends
                # and we'll clean it up there.
                if w.is_completing:
                    continue
                self._row_widgets.pop(eid)
                self._list_layout.removeWidget(w)
                w.deleteLater()

        for idx, row_vm in enumerate(rows):
            if row_vm.egg_type_id in self._row_widgets:
                self._row_widgets[row_vm.egg_type_id].update_data(row_vm)
            else:
                w = EggRowWidget(row_vm, audio=self._audio)
                w.clicked.connect(self._on_row_clicked)
                w.completion_finished.connect(self._on_row_completion_finished)
                self._row_widgets[row_vm.egg_type_id] = w

            w = self._row_widgets[row_vm.egg_type_id]
            current_idx = self._list_layout.indexOf(w)
            if current_idx != idx:
                self._list_layout.removeWidget(w)
                self._list_layout.insertWidget(idx, w)

        self._update_visibility(len(rows))

    def on_completion(self, egg_type_id: int) -> None:
        """Trigger fade for a completed row (called before refresh removes it)."""
        w = self._row_widgets.get(egg_type_id)
        if w:
            w.animate_completion()

    # ── Internal ──

    def _update_visibility(self, row_count: int) -> None:
        has_rows = row_count > 0
        self._empty_state.setVisible(not has_rows)
        self._scroll_area.setVisible(has_rows)
        self._sort_combo.setVisible(has_rows)
        self._active_badge.setText(f"{row_count} Active")

    def _on_row_clicked(self, egg_type_id: int) -> None:
        self.increment_requested.emit(egg_type_id)

    def _on_row_completion_finished(self, egg_type_id: int) -> None:
        """Tear down a completed row after its close-out animation finishes."""
        w = self._row_widgets.pop(egg_type_id, None)
        if w is not None:
            self._list_layout.removeWidget(w)
            w.deleteLater()

    def _on_sort_changed(self) -> None:
        order = self._sort_combo.currentData()
        if order:
            self.sort_changed.emit(order)


class _BreedListEmptyState(QWidget):
    """Polished empty state shown when no targets are active."""

    catalog_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("emptyStateContainer")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(64, 0, 64, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(0)

        icon = QLabel("\u25cc")
        icon.setObjectName("emptyStateIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(80, 80)
        icon.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout.addWidget(icon, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addSpacing(28)

        msg = QLabel("No active monsters to track")
        msg.setObjectName("emptyStateTitle")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(msg)

        layout.addSpacing(8)

        sub = QLabel(
            "Select an egg from the Catalog to begin\nyour awakening journey."
        )
        sub.setObjectName("emptyStateSubtitle")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub)

        layout.addSpacing(36)

        btn = QPushButton("Open Monster Catalog")
        btn.setObjectName("primaryBtn")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        btn.clicked.connect(self.catalog_requested)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
