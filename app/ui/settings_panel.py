"""Settings page — content updates, database info, BBB disclaimer."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.ui.themes import placeholder_tones_3, scaled
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
    ui_options_apply_requested = Signal(str, str)  # (theme_name, font_size_label)

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

        columns = QHBoxLayout()
        columns.setSpacing(24)

        # ── Left column: Content Updates + Data View ──
        left_col = QVBoxLayout()
        left_col.setSpacing(24)
        self._update_card = self._build_update_card()
        self._data_view_card = self._build_data_view_card()
        left_col.addWidget(self._update_card)
        left_col.addWidget(self._data_view_card, stretch=1)
        columns.addLayout(left_col, stretch=1)

        # ── Right column: DB Info + UI Options + Disclaimer + App Info ──
        right_col = QVBoxLayout()
        right_col.setSpacing(24)
        self._db_info_card = self._build_db_info_card()
        self._ui_options_card = self._build_ui_options_card()
        self._disclaimer_card = self._build_disclaimer_card()
        self._app_info_card = self._build_app_info_card()
        right_col.addWidget(self._db_info_card)
        right_col.addWidget(self._ui_options_card)
        right_col.addWidget(self._disclaimer_card)
        right_col.addWidget(self._app_info_card)
        right_col.addStretch()
        columns.addLayout(right_col, stretch=1)

        layout.addLayout(columns, stretch=1)

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
        icon.setFixedSize(scaled(40), scaled(40))
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
        self._update_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
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
        icon.setFixedSize(scaled(40), scaled(40))
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

    # ── UI Options card ──────────────────────────────────────────────

    def _build_ui_options_card(self) -> SurfaceCard:
        from app.ui.themes import FONT_SIZE_OPTIONS, THEME_NAMES

        card = SurfaceCard()
        lay = card.card_layout()

        header = QHBoxLayout()
        header.setSpacing(12)

        icon = QLabel("\u2699")
        icon.setObjectName("settingsCardIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(scaled(40), scaled(40))
        icon.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        header.addWidget(icon)

        title = QLabel("UI Options")
        title.setObjectName("settingsCardTitle")
        header.addWidget(title)
        header.addStretch()
        lay.addLayout(header)

        desc = QLabel(
            "Customize the app\u2019s visual appearance. "
            "Changes take effect when you press Apply."
        )
        desc.setObjectName("settingsSupportingText")
        desc.setWordWrap(True)
        lay.addWidget(desc)

        # Theme row
        theme_row = QHBoxLayout()
        theme_row.setSpacing(12)
        theme_label = QLabel("Theme")
        theme_label.setObjectName("settingsInfoLabel")
        theme_label.setMinimumWidth(80)
        theme_row.addWidget(theme_label)
        self._theme_combo = QComboBox()
        for name in THEME_NAMES:
            self._theme_combo.addItem(name, name)
        theme_row.addWidget(self._theme_combo, stretch=1)
        lay.addLayout(theme_row)

        # Font size row
        font_row = QHBoxLayout()
        font_row.setSpacing(12)
        font_label = QLabel("Font Size")
        font_label.setObjectName("settingsInfoLabel")
        font_label.setMinimumWidth(80)
        font_row.addWidget(font_label)
        self._font_combo = QComboBox()
        for label, _offset in FONT_SIZE_OPTIONS:
            self._font_combo.addItem(label, label)
        font_row.addWidget(self._font_combo, stretch=1)
        lay.addLayout(font_row)

        # Apply button
        self._ui_apply_btn = QPushButton("Apply")
        self._ui_apply_btn.setObjectName("primaryBtn")
        self._ui_apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._ui_apply_btn.clicked.connect(self._on_ui_apply)
        lay.addWidget(self._ui_apply_btn, alignment=Qt.AlignmentFlag.AlignRight)

        return card

    def _on_ui_apply(self) -> None:
        theme = self._theme_combo.currentData()
        font_label = self._font_combo.currentData()
        self.ui_options_apply_requested.emit(theme, font_label)
        # Brief visual feedback
        self._ui_apply_btn.setText("Applied \u2713")
        self._ui_apply_btn.setEnabled(False)
        QTimer.singleShot(1500, self._reset_apply_btn)

    def _reset_apply_btn(self) -> None:
        self._ui_apply_btn.setText("Apply")
        self._ui_apply_btn.setEnabled(True)

    def set_ui_options(self, theme: str, font_size_label: str) -> None:
        """Set the combo box selections (e.g. on page load)."""
        for i in range(self._theme_combo.count()):
            if self._theme_combo.itemData(i) == theme:
                self._theme_combo.setCurrentIndex(i)
                break
        for i in range(self._font_combo.count()):
            if self._font_combo.itemData(i) == font_size_label:
                self._font_combo.setCurrentIndex(i)
                break

    # ── Data View card ─────────────────────────────────────────────

    def _build_data_view_card(self) -> SurfaceCard:
        card = SurfaceCard(object_name="settingsDataCard")
        lay = card.card_layout()
        lay.setSpacing(0)

        title = QLabel("Data View")
        title.setObjectName("settingsCardTitle")
        title.setSizePolicy(
            title.sizePolicy().horizontalPolicy(),
            QSizePolicy.Policy.Maximum,
        )
        lay.addWidget(title)
        lay.addSpacing(12)

        self._data_table = QTableWidget(0, 5)
        self._data_table.setObjectName("settingsDataTable")
        self._data_table.setHorizontalHeaderLabels(
            ["Icons", "Monster Name", "Type", "Eggs Required", "Time"]
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
            2, QHeaderView.ResizeMode.Stretch
        )
        self._data_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch
        )
        self._data_table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.Stretch
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

        header = QHBoxLayout()
        header.setSpacing(12)

        icon = QLabel("\u2696")
        icon.setObjectName("settingsCardIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(scaled(40), scaled(40))
        icon.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        header.addWidget(icon)

        title = QLabel("Fan Content Policy")
        title.setObjectName("settingsCardTitle")
        header.addWidget(title)
        header.addStretch()
        lay.addLayout(header)

        self._disclaimer_label = QLabel()
        self._disclaimer_label.setObjectName("settingsSupportingText")
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
        icon.setFixedSize(scaled(40), scaled(40))
        icon.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        header.addWidget(icon)

        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        lbl = QLabel("Application Version")
        lbl.setObjectName("settingsCardTitle")
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
        self.set_ui_options(vm.current_theme, vm.current_font_size_label)

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
        self._data_table.setSortingEnabled(False)
        self._data_table.setRowCount(len(rows))

        for row_idx, row in enumerate(rows):
            thumb = _SettingsDataThumb(
                row.monster_name,
                row.image_path,
                monster_type=row.monster_type,
                is_placeholder=row.is_placeholder,
            )
            # Hidden sort item so column 0 participates in sorting
            sort_item = QTableWidgetItem(row.monster_name)
            sort_item.setForeground(QColor(0, 0, 0, 0))
            self._data_table.setItem(row_idx, 0, sort_item)
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

            from app.ui.themes import THEMES, get_active_theme
            t = THEMES[get_active_theme()]
            name_item.setForeground(QColor(t["text1"]))
            eggs_item.setForeground(QColor(t["text2"]))
            duration_item.setForeground(QColor(t["text2"]))
            type_item.setForeground(_TYPE_COLORS.get(row.monster_type, QColor(t["text2"])))

            self._data_table.setItem(row_idx, 1, name_item)
            self._data_table.setItem(row_idx, 2, type_item)
            self._data_table.setItem(row_idx, 3, eggs_item)
            self._data_table.setItem(row_idx, 4, duration_item)

        self._data_table.setSortingEnabled(True)


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
        label.setFixedSize(scaled(36), scaled(36))

        pix = QPixmap(image_path) if image_path else QPixmap()
        if is_placeholder or pix.isNull():
            label.setObjectName("settingsDataThumbFallback")
            label.setText(monster_name[:2].upper())
            bg, border, fg = placeholder_tones_3(monster_type)
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

