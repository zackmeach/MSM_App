"""Settings page — content updates, database info, BBB disclaimer."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.ui.widgets.info_row_widget import InfoRowWidget
from app.ui.widgets.surface_card import SurfaceCard

if TYPE_CHECKING:
    from app.ui.viewmodels import (
        SettingsDataRowViewModel,
        SettingsUpdateState,
        SettingsViewModel,
    )


class SettingsPanel(QWidget):
    """Full Settings page: header, content-update card, DB info card,
    disclaimer card, and app-info card inside a vertical scroll area.

    Signals:
        check_update_requested — emitted when the user wants to check
            the manifest for a newer content database version.
        apply_update_requested — emitted when the user wants to download
            and install an available content update.
    """

    check_update_requested = Signal()
    apply_update_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("pageCanvas")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._is_install_action = False
        self._build_ui()

    # ── Build ─────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("settingsPageScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.viewport().setObjectName("pageScrollViewport")
        scroll.viewport().setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        content = QWidget()
        content.setObjectName("settingsScrollContent")
        content.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(32)

        self._build_header(layout)

        top_row = QHBoxLayout()
        top_row.setSpacing(24)
        self._update_card = self._build_update_card()
        self._db_info_card = self._build_db_info_card()
        top_row.addWidget(self._update_card, stretch=1)
        top_row.addWidget(self._db_info_card, stretch=1)
        layout.addLayout(top_row)

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(24)
        self._data_view_card = self._build_data_view_card()
        bottom_row.addWidget(self._data_view_card, stretch=8)

        side_stack = QVBoxLayout()
        side_stack.setSpacing(24)
        self._disclaimer_card = self._build_disclaimer_card()
        self._app_info_card = self._build_app_info_card()
        side_stack.addWidget(self._disclaimer_card)
        side_stack.addWidget(self._app_info_card)
        side_stack.addStretch()
        bottom_row.addLayout(side_stack, stretch=4)
        layout.addLayout(bottom_row)

        layout.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _build_header(self, parent_layout: QVBoxLayout) -> None:
        title = QLabel("Settings")
        title.setObjectName("panelTitle")
        parent_layout.addWidget(title)

        subtitle = QLabel(
            "Manage content updates, view database details, "
            "and review fan content attribution."
        )
        subtitle.setObjectName("settingsSubtitle")
        subtitle.setWordWrap(True)
        parent_layout.addWidget(subtitle)

    # ── Content Updates card ──────────────────────────────────────────

    def _build_update_card(self) -> SurfaceCard:
        card = SurfaceCard()
        lay = card.card_layout()

        header = QHBoxLayout()
        header.setSpacing(12)

        icon = QLabel("\u2193")
        icon.setObjectName("settingsCardIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(40, 40)
        icon.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        header.addWidget(icon)

        title = QLabel("Content Updates")
        title.setObjectName("settingsCardTitle")
        header.addWidget(title)
        header.addStretch()
        lay.addLayout(header)

        desc = QLabel(
            "Updates replace your local content database with the latest "
            "monster data. Your progress is kept where it still matches "
            "updated content."
        )
        desc.setObjectName("settingsSupportingText")
        desc.setWordWrap(True)
        lay.addWidget(desc)

        # Status strip ─ dot + headline (left) / CTA button (right)
        strip = QWidget()
        strip.setObjectName("settingsStatusStrip")
        strip.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        strip_l = QHBoxLayout(strip)
        strip_l.setContentsMargins(16, 12, 16, 12)

        status_left = QHBoxLayout()
        status_left.setSpacing(8)

        self._status_dot = QLabel()
        self._status_dot.setObjectName("settingsStatusDot")
        self._status_dot.setFixedSize(8, 8)
        self._status_dot.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        status_left.addWidget(self._status_dot)

        self._status_headline = QLabel("READY TO CHECK")
        self._status_headline.setObjectName("settingsStatusBadge")
        status_left.addWidget(self._status_headline)
        status_left.addStretch()

        strip_l.addLayout(status_left, stretch=1)

        self._update_btn = QPushButton("Check for Updates")
        self._update_btn.setObjectName("primaryBtn")
        self._update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_btn.clicked.connect(self._on_update_btn)
        strip_l.addWidget(self._update_btn)

        lay.addWidget(strip)

        self._status_detail = QLabel("")
        self._status_detail.setObjectName("settingsSupportingText")
        self._status_detail.setWordWrap(True)
        self._status_detail.setVisible(False)
        lay.addWidget(self._status_detail)

        return card

    # ── Database Information card ─────────────────────────────────────

    def _build_db_info_card(self) -> SurfaceCard:
        card = SurfaceCard()
        lay = card.card_layout()

        header = QHBoxLayout()
        header.setSpacing(12)

        icon = QLabel("\u25a6")
        icon.setObjectName("settingsCardIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(40, 40)
        icon.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        header.addWidget(icon)

        title = QLabel("Database Information")
        title.setObjectName("settingsCardTitle")
        header.addWidget(title)
        header.addStretch()
        lay.addLayout(header)

        self._row_version = InfoRowWidget("Database Version", "\u2014")
        self._row_schema = InfoRowWidget("Schema Version", "\u2014")
        self._row_updated = InfoRowWidget("Last Updated", "\u2014", show_divider=False)
        lay.addWidget(self._row_version)
        lay.addWidget(self._row_schema)
        lay.addWidget(self._row_updated)

        return card

    def _build_data_view_card(self) -> SurfaceCard:
        card = SurfaceCard(object_name="settingsDataCard")
        lay = card.card_layout()
        lay.setSpacing(0)

        header = QWidget()
        header.setObjectName("settingsDataHeader")
        header.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        header_l = QVBoxLayout(header)
        header_l.setContentsMargins(0, 0, 0, 20)
        header_l.setSpacing(0)

        title = QLabel("Data View")
        title.setObjectName("settingsCardTitle")
        header_l.addWidget(title)
        lay.addWidget(header)

        self._data_table = QTableWidget(0, 5)
        self._data_table.setObjectName("settingsDataTable")
        self._data_table.setHorizontalHeaderLabels(
            ["Egg", "Monster Name", "Type", "Eggs Required", "Time"]
        )
        self._data_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._data_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._data_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._data_table.setShowGrid(False)
        self._data_table.setAlternatingRowColors(False)
        self._data_table.verticalHeader().setVisible(False)
        self._data_table.verticalHeader().setDefaultSectionSize(58)
        self._data_table.horizontalHeader().setStretchLastSection(False)
        self._data_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self._data_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._data_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self._data_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        self._data_table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.ResizeToContents
        )
        self._data_table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        lay.addWidget(self._data_table, stretch=1)

        return card

    # ── Disclaimer card ───────────────────────────────────────────────

    def _build_disclaimer_card(self) -> SurfaceCard:
        card = SurfaceCard()
        lay = card.card_layout()

        badge = QLabel("FAN CONTENT POLICY")
        badge.setObjectName("settingsInfoLabel")
        lay.addWidget(badge)

        self._disclaimer_label = QLabel()
        self._disclaimer_label.setObjectName("settingsDisclaimerText")
        self._disclaimer_label.setWordWrap(True)
        lay.addWidget(self._disclaimer_label)

        return card

    # ── App Information card ──────────────────────────────────────────

    def _build_app_info_card(self) -> SurfaceCard:
        card = SurfaceCard(object_name="settingsCardLow")
        lay = card.card_layout()

        header = QHBoxLayout()
        header.setSpacing(12)

        icon = QLabel("i")
        icon.setObjectName("settingsCardIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(40, 40)
        icon.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        header.addWidget(icon)

        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        lbl = QLabel("APPLICATION VERSION")
        lbl.setObjectName("settingsInfoLabel")
        info_col.addWidget(lbl)
        self._app_version_label = QLabel("\u2014")
        self._app_version_label.setObjectName("settingsInfoValue")
        info_col.addWidget(self._app_version_label)

        header.addLayout(info_col)
        header.addStretch()
        lay.addLayout(header)

        return card

    # ── Public API ────────────────────────────────────────────────────

    def refresh(self, vm: SettingsViewModel) -> None:
        """Full page refresh from a SettingsViewModel."""
        self._row_version.set_value(vm.content_version)
        self._row_schema.set_value(vm.schema_version)
        self._row_updated.set_value(vm.last_updated_display)
        self._app_version_label.setText(vm.app_version)
        self._disclaimer_label.setText(vm.disclaimer_text)
        self._populate_data_view(vm.data_rows)
        self.set_update_state(vm.update_state)

    def set_update_state(self, state: SettingsUpdateState) -> None:
        """Update the content-update card to reflect the current workflow state."""
        self._is_install_action = state.is_install_action
        self._update_btn.setText(state.button_label)
        self._update_btn.setEnabled(state.button_enabled)

        self._status_headline.setText(state.status_headline.upper())

        tone = state.tone
        self._status_headline.setProperty("tone", tone)
        self._status_headline.style().unpolish(self._status_headline)
        self._status_headline.style().polish(self._status_headline)

        self._status_dot.setProperty("tone", tone)
        self._status_dot.style().unpolish(self._status_dot)
        self._status_dot.style().polish(self._status_dot)

        has_detail = bool(state.status_detail)
        self._status_detail.setText(state.status_detail)
        self._status_detail.setVisible(has_detail)

    def set_status(self, text: str) -> None:
        """Update the status headline with transient progress text.

        Kept for compatibility with ``UpdateService.status_message`` during
        intermediate download / validation phases.
        """
        self._status_headline.setText(text.upper())

    # ── Internal ──────────────────────────────────────────────────────

    def _on_update_btn(self) -> None:
        if self._is_install_action:
            self.apply_update_requested.emit()
        else:
            self.check_update_requested.emit()

    def _populate_data_view(self, rows: list[SettingsDataRowViewModel]) -> None:
        self._data_table.setRowCount(len(rows))

        for row_idx, row in enumerate(rows):
            thumb = _SettingsDataThumb(
                row.monster_name,
                row.image_path,
                monster_type=row.monster_type,
                is_placeholder=row.is_placeholder,
            )
            self._data_table.setCellWidget(row_idx, 0, thumb)

            name_item = QTableWidgetItem(row.monster_name)
            type_item = QTableWidgetItem(row.monster_type_label)
            eggs_item = QTableWidgetItem(row.eggs_required_display)
            duration_item = QTableWidgetItem(row.duration_display)

            alignment = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            name_item.setTextAlignment(alignment)
            type_item.setTextAlignment(alignment)
            eggs_item.setTextAlignment(alignment)
            duration_item.setTextAlignment(alignment)

            name_item.setForeground(QColor("#e3e2e7"))
            eggs_item.setForeground(QColor("#cbc3d7"))
            duration_item.setForeground(QColor("#cbc3d7"))
            type_item.setForeground(_TYPE_COLORS.get(row.monster_type, QColor("#cbc3d7")))

            self._data_table.setItem(row_idx, 1, name_item)
            self._data_table.setItem(row_idx, 2, type_item)
            self._data_table.setItem(row_idx, 3, eggs_item)
            self._data_table.setItem(row_idx, 4, duration_item)


class _SettingsDataThumb(QWidget):
    def __init__(
        self,
        monster_name: str,
        image_path: str,
        *,
        monster_type: str,
        is_placeholder: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("settingsDataThumb")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setFixedSize(36, 36)

        pix = QPixmap(image_path) if image_path else QPixmap()
        if is_placeholder or pix.isNull():
            label.setObjectName("settingsDataThumbFallback")
            label.setText(monster_name[:2].upper())
            bg, border, fg = _THUMB_TONES.get(
                monster_type, ("#262332", "#343046", "#d0bcff")
            )
            label.setStyleSheet(
                f"background-color: {bg}; border: 1px solid {border}; "
                f"border-radius: 8px; color: {fg}; font-size: 12px; font-weight: 700;"
            )
            label.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        else:
            label.setObjectName("settingsDataThumbImage")
            label.setPixmap(pix)
            label.setScaledContents(True)

        layout.addWidget(label)


_TYPE_COLORS = {
    "wublin": QColor("#45e9d0"),
    "celestial": QColor("#ffba20"),
    "amber": QColor("#ff8a65"),
}

_THUMB_TONES = {
    "wublin": ("#1a2e31", "#275058", "#45e9d0"),
    "celestial": ("#352d12", "#5c4810", "#ffba20"),
    "amber": ("#38251f", "#6a3b2d", "#ff8a65"),
}
