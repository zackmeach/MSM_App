"""Main application window — navigation, keyboard shortcuts, and panel wiring."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

import logging

from app.assets import resolver
from app.services.app_service import AppService
from app.services.audio_player import AudioPlayer
from app.ui.catalog_view import CatalogView
from app.ui.home_view import HomeView
from app.ui.settings_panel import SettingsPanel
from app.ui.viewmodels import AppStateViewModel, SettingsUpdateState
from app.updater.update_service import UpdateService

if TYPE_CHECKING:
    from app.bootstrap import AppContext
    from app.updater.update_service import UpdateApplyResult, UpdateCheckResult

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self._ctx = context
        self.setWindowTitle("MSM Awakening Tracker")
        self.setMinimumSize(900, 600)

        resolver.configure(
            bundle_dir=context.bundle_dir,
            cache_dir=context.data_dir / "assets",
        )

        self._service = AppService(context.conn_content, context.conn_userstate)
        self._audio = AudioPlayer(context.bundle_dir / "audio" / "ding.wav")
        self._updater = UpdateService(context.data_dir, context.conn_content)
        self._update_state = SettingsUpdateState.idle()
        self._build_ui()
        self._connect_signals()
        self._initial_load()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Nav bar ──
        nav = QWidget()
        nav.setObjectName("navBar")
        nav_l = QHBoxLayout(nav)
        nav_l.setContentsMargins(24, 0, 24, 0)
        nav_l.setSpacing(0)

        title = QLabel("MSM Awakening Tracker")
        title.setObjectName("appTitle")
        nav_l.addWidget(title)
        nav_l.addSpacing(32)

        self._btn_home = QPushButton("Home")
        self._btn_catalog = QPushButton("Catalog")
        self._btn_settings = QPushButton("Settings")
        self._nav_btns = [self._btn_home, self._btn_catalog, self._btn_settings]
        for btn in self._nav_btns:
            btn.setObjectName("navBtn")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFocusPolicy(Qt.FocusPolicy.TabFocus)
            nav_l.addWidget(btn)

        nav_l.addStretch()

        self._btn_undo = QPushButton("Undo")
        self._btn_undo.setEnabled(False)
        self._btn_undo.setObjectName("utilityBtn")
        self._btn_undo.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self._btn_undo.setToolTip("Ctrl+Z")
        nav_l.addWidget(self._btn_undo)
        nav_l.addSpacing(4)

        self._btn_redo = QPushButton("Redo")
        self._btn_redo.setEnabled(False)
        self._btn_redo.setObjectName("utilityBtn")
        self._btn_redo.setFocusPolicy(Qt.FocusPolicy.TabFocus)
        self._btn_redo.setToolTip("Ctrl+Y")
        nav_l.addWidget(self._btn_redo)

        root.addWidget(nav)

        # ── Pages ──
        self._stack = QStackedWidget()
        self._stack.setObjectName("pageStack")
        self._home = HomeView()
        self._catalog = CatalogView()
        self._settings = SettingsPanel()

        self._stack.addWidget(self._home)
        self._stack.addWidget(self._catalog)
        self._stack.addWidget(self._settings)
        root.addWidget(self._stack, stretch=1)

        # ── Nav wiring ──
        self._btn_home.clicked.connect(lambda: self._navigate_to(0))
        self._btn_catalog.clicked.connect(lambda: self._navigate_to(1))
        self._btn_settings.clicked.connect(lambda: self._navigate_to(2))

        # ── Undo/redo wiring ──
        self._btn_undo.clicked.connect(self._service.undo)
        self._btn_redo.clicked.connect(self._service.redo)
        QShortcut(QKeySequence("Ctrl+Z"), self).activated.connect(self._service.undo)
        QShortcut(QKeySequence("Ctrl+Y"), self).activated.connect(self._service.redo)
        QShortcut(QKeySequence("Ctrl+Shift+Z"), self).activated.connect(self._service.redo)

        self._apply_stylesheet()
        self._navigate_to(0)

    def _connect_signals(self) -> None:
        self._service.state_changed.connect(self._on_state_changed)
        self._service.completion_event.connect(self._on_completion)
        self._service.error_occurred.connect(self._on_error)

        self._home.breed_list_panel.increment_requested.connect(
            self._service.handle_increment_egg
        )
        self._home.breed_list_panel.sort_changed.connect(
            self._service.handle_sort_change
        )
        self._home.inwork_panel.close_out_requested.connect(
            self._service.handle_close_out
        )
        self._catalog.add_target_requested.connect(
            self._service.handle_add_target
        )
        self._catalog.close_out_requested.connect(
            self._service.handle_close_out
        )
        self._home.breed_list_panel.navigate_to_catalog.connect(
            lambda: self._navigate_to(1)
        )

        self._settings.check_update_requested.connect(self._on_check_update)
        self._settings.apply_update_requested.connect(self._on_apply_update)
        self._updater.check_result.connect(self._on_update_check_result)
        self._updater.apply_result.connect(self._on_update_apply_result)
        self._updater.status_message.connect(self._on_updater_progress)

    def _initial_load(self) -> None:
        self._catalog.load_catalog(self._service.get_catalog_items())
        state = self._service.get_app_state()
        self._on_state_changed(state)
        self._home.breed_list_panel.set_sort_order(state.sort_order)

    def _on_state_changed(self, state: AppStateViewModel) -> None:
        self._home.breed_list_panel.refresh(state.breed_list_rows)
        self._home.inwork_panel.refresh(state.inwork_by_type)
        self._catalog.refresh_active(state.inwork_by_type)
        self._btn_undo.setEnabled(state.can_undo)
        self._btn_redo.setEnabled(state.can_redo)

    def _on_completion(self, egg_type_id: int) -> None:
        self._audio.play_ding()
        self._home.breed_list_panel.on_completion(egg_type_id)

    def _navigate_to(self, index: int) -> None:
        if index == 2:
            self._settings.refresh(self._service.get_settings_viewmodel())
            self._settings.set_update_state(self._update_state)
        self._stack.setCurrentIndex(index)
        for i, btn in enumerate(self._nav_btns):
            btn.setProperty("active", i == index)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _on_error(self, msg: str) -> None:
        QMessageBox.warning(self, "Error", msg)

    # ── Update flow ──

    def _set_update_state(self, state: SettingsUpdateState) -> None:
        """Single point of truth for update-card state changes."""
        self._update_state = state
        self._settings.set_update_state(state)

    def _on_updater_progress(self, text: str) -> None:
        """Forward transient progress text from the updater worker thread."""
        self._settings.set_status(text)

    def _on_check_update(self) -> None:
        self._set_update_state(SettingsUpdateState.checking())
        self._updater.check_for_update()

    def _on_apply_update(self) -> None:
        self._set_update_state(SettingsUpdateState.staging())
        self._updater.apply_update()

    def _on_update_check_result(self, result: UpdateCheckResult) -> None:
        if result.error:
            self._set_update_state(SettingsUpdateState.error(result.error))
        elif result.update_available:
            self._set_update_state(SettingsUpdateState.available(result.remote_version))
        else:
            self._set_update_state(SettingsUpdateState.no_update())

    def _on_update_apply_result(self, result: UpdateApplyResult) -> None:
        if not result.success:
            self._set_update_state(SettingsUpdateState.error(result.error))
            return

        self._set_update_state(SettingsUpdateState.finalizing())
        self._finalize_content_update(result.new_version)

    # ── Post-update finalization (FR-704) ──

    def _finalize_content_update(self, new_version: str) -> None:
        """Replace content.db, rebind services, reconcile, refresh all UI.

        Owns the complete FR-704 obligation so the steps are never scattered.
        """
        try:
            new_conn = self._updater.finalize_update(self._ctx.conn_content)
        except Exception as exc:
            logger.error("Finalization failed, rolling back: %s", exc, exc_info=True)
            self._rollback_content_update(str(exc))
            return

        self._ctx.conn_content = new_conn
        self._service.rebind_content(new_conn)
        self._updater.rebind_content(new_conn)

        self._run_post_update_reconciliation(new_conn)

        self._service.clear_undo_redo()

        self._catalog.load_catalog(self._service.get_catalog_items())
        self._settings.refresh(self._service.get_settings_viewmodel())
        self._set_update_state(SettingsUpdateState.success(new_version))

        self._updater.cleanup_staging_files()

    def _rollback_content_update(self, error_detail: str) -> None:
        """Restore the prior content.db and report the failure."""
        restored = self._updater.rollback_update()
        if restored:
            self._ctx.conn_content = restored
            self._service.rebind_content(restored)
            self._updater.rebind_content(restored)
        self._set_update_state(
            SettingsUpdateState.error(f"Update failed during apply: {error_detail}")
        )

    def _run_post_update_reconciliation(self, conn_content: 'sqlite3.Connection') -> None:
        """Clip/purge userstate progress that exceeds updated requirements."""
        from app.domain.reconciliation import reconcile
        from app.repositories import monster_repo, target_repo

        targets = target_repo.fetch_all_targets(self._ctx.conn_userstate)

        deprecated_ids = []
        for t in targets:
            if not monster_repo.monster_exists_and_active(conn_content, t.monster_id):
                deprecated_ids.append(t.id)

        if deprecated_ids:
            for tid in deprecated_ids:
                target_repo.delete_progress_for_target(self._ctx.conn_userstate, tid)
                target_repo.delete_target(self._ctx.conn_userstate, tid)
            self._ctx.conn_userstate.commit()

        progress = target_repo.fetch_all_progress(self._ctx.conn_userstate)
        clips = reconcile(progress)
        if clips:
            for target_id, egg_type_id, clipped_val in clips:
                target_repo.set_progress(
                    self._ctx.conn_userstate, target_id, egg_type_id, clipped_val
                )
            self._ctx.conn_userstate.commit()

    def _apply_stylesheet(self) -> None:
        self.setStyleSheet("""
            /* ── Base surfaces ── */
            QMainWindow { background-color: #121317; }
            QWidget {
                color: #e3e2e7;
                font-family: "Segoe UI", "Inter", sans-serif;
                font-size: 13px;
            }
            #pageStack, #pageCanvas, #catalogBrowserPanel, #activeRailPanel,
            #settingsScrollContent, #activeRailContent, #catalogGridContainer,
            #breedListContainer {
                background-color: #121317;
            }
            #pageScrollViewport, #activeRailViewport, #catalogGridViewport,
            #breedListViewport {
                background-color: #121317;
            }

            /* ── Navigation bar ── */
            #navBar {
                background-color: #121317;
                border-bottom: 1px solid #1f1f24;
                min-height: 56px;
                max-height: 56px;
            }
            #appTitle {
                font-size: 16px;
                font-weight: 700;
                color: #e3e2e7;
                padding: 0 4px;
                letter-spacing: -0.3px;
            }
            #navBtn {
                background: transparent;
                color: #939099;
                border: none;
                border-bottom: 2px solid transparent;
                border-radius: 0;
                padding: 18px 12px 16px 12px;
                font-size: 13px;
                font-weight: 600;
            }
            #navBtn:hover {
                color: #e3e2e7;
                background: transparent;
            }
            #navBtn[active="true"] {
                color: #d0bcff;
                border-bottom: 2px solid #d0bcff;
            }
            #navBtn:focus {
                color: #d0bcff;
            }

            /* ── Utility buttons (undo / redo) ── */
            #utilityBtn {
                background-color: transparent;
                color: #958ea0;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 12px;
            }
            #utilityBtn:hover {
                background-color: #292a2e;
                color: #cbc3d7;
            }
            #utilityBtn:disabled {
                color: #494454;
                background: transparent;
            }
            #utilityBtn:focus { border: 1px solid #d0bcff; }

            /* ── Panel titles ── */
            #panelTitle {
                font-size: 22px;
                font-weight: 800;
                color: #e3e2e7;
                letter-spacing: -0.3px;
            }
            #activeBadge {
                background-color: #1a1b20;
                color: #958ea0;
                border: 1px solid #252530;
                border-radius: 12px;
                padding: 4px 12px;
                font-size: 12px;
            }

            /* ── Breed List: empty state ── */
            #emptyStateContainer {
                background: qradialgradient(
                    cx:0.5, cy:0.5, radius:0.7, fx:0.5, fy:0.5,
                    stop:0 #1e1a28, stop:1 #1a1b20);
                border: none;
                border-radius: 12px;
            }
            #emptyStateIcon {
                background-color: #292a2e;
                border: 1px solid #3a3548;
                border-radius: 40px;
                color: #bca8f5;
                font-size: 28px;
            }
            #emptyStateTitle {
                font-size: 20px;
                font-weight: 700;
                color: #e3e2e7;
            }
            #emptyStateSubtitle {
                font-size: 14px;
                color: #cbc3d7;
            }

            /* ── Primary CTA button ── */
            #primaryBtn {
                background-color: qlineargradient(
                    spread:pad, x1:0, y1:0, x2:1, y2:1,
                    stop:0 #d0bcff, stop:1 #9f78ff);
                color: #330080;
                border: none;
                border-radius: 12px;
                padding: 12px 28px;
                font-size: 14px;
                font-weight: 700;
            }
            #primaryBtn:hover {
                background-color: qlineargradient(
                    spread:pad, x1:0, y1:0, x2:1, y2:1,
                    stop:0 #ddd0ff, stop:1 #b08aff);
            }
            #primaryBtn:pressed {
                background-color: qlineargradient(
                    spread:pad, x1:0, y1:0, x2:1, y2:1,
                    stop:0 #bfa8ee, stop:1 #8a6ae8);
            }
            #primaryBtn:focus { border: 2px solid #e9ddff; }

            /* ── In-Work section cards ── */
            #sectionCard {
                background-color: #1f1f24;
                border: 1px solid #252530;
                border-radius: 12px;
            }
            #sectionIcon {
                background-color: #343439;
                border-radius: 8px;
                font-size: 16px;
                min-width: 40px; max-width: 40px;
                min-height: 40px; max-height: 40px;
            }
            #sectionLabel {
                font-size: 16px;
                font-weight: 700;
                color: #e3e2e7;
            }
            #sectionBadge {
                color: #958ea0;
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 2px;
            }
            #sectionBody {
                background-color: #0d0e12;
                border: 1px dashed #2d2a38;
                border-radius: 12px;
                min-height: 96px;
            }
            #sectionEmptyText {
                color: #958ea0;
                font-size: 13px;
                font-style: italic;
                padding: 4px 0;
            }

            /* ── Getting Started card ── */
            #gettingStartedCard {
                background-color: rgba(52, 52, 57, 0.82);
                border: 1px solid #2d2842;
                border-radius: 12px;
            }
            #gettingStartedIcon {
                background: transparent;
                font-size: 20px;
                min-width: 24px; max-width: 24px;
                min-height: 24px; max-height: 24px;
            }
            #gettingStartedTitle {
                font-size: 13px;
                font-weight: 700;
                color: #e3e2e7;
            }
            #gettingStartedText {
                font-size: 12px;
                color: #cbc3d7;
            }

            /* ── Egg row (Breed List) ── */
            #eggRow {
                background-color: #1f1f24;
                border: 1px solid #252530;
                border-radius: 10px;
            }
            #eggIconContainer {
                background-color: #343439;
                border-radius: 8px;
            }
            #eggName {
                font-weight: 600;
                font-size: 14px;
                color: #e3e2e7;
            }
            #eggTime { color: #cbc3d7; font-size: 12px; }
            #eggCounter {
                font-size: 13px;
                color: #d0bcff;
                font-weight: 500;
            }

            /* ── In-work entry ── */
            #inworkEntry {
                background-color: transparent;
                border-radius: 8px;
            }
            #inworkEntry:hover { background-color: #292a2e; }
            #inworkEntryName {
                font-size: 13px;
                color: #e3e2e7;
            }

            /* ── Standard buttons ── */
            QPushButton {
                background-color: #292a2e;
                color: #e3e2e7;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #343439; }
            QPushButton:pressed { background-color: #494454; }
            QPushButton:focus { border: 1px solid #d0bcff; }
            QPushButton:disabled {
                background-color: #1a1b20;
                color: #494454;
            }

            /* ── Form controls ── */
            QComboBox {
                background-color: #292a2e;
                color: #e3e2e7;
                border: 1px solid #343439;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QComboBox:focus { border: 1px solid #d0bcff; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #292a2e;
                color: #e3e2e7;
                selection-background-color: #343439;
            }

            QLineEdit {
                background-color: #292a2e;
                color: #e3e2e7;
                border: 1px solid #343439;
                border-radius: 4px;
                padding: 6px 10px;
            }
            QLineEdit:focus { border: 1px solid #d0bcff; }

            /* ── Scroll area ── */
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(208, 188, 255, 51);
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(208, 188, 255, 80);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }

            /* ── Catalog: subtitle ── */
            #catalogSubtitle {
                color: #cbc3d7;
                font-size: 13px;
            }

            /* ── Catalog: search ── */
            #catalogSearchRow {
                background-color: #1f1f24;
                border: 1px solid #252530;
                border-radius: 12px;
                min-height: 46px;
            }
            #catalogSearchIcon {
                color: #958ea0;
                font-size: 16px;
                min-width: 18px;
            }
            #catalogSearch {
                background-color: transparent;
                border: none;
                padding: 10px 0;
                font-size: 13px;
                color: #e3e2e7;
            }
            #catalogSearchRow:focus-within {
                border: 1px solid rgba(208, 188, 255, 0.4);
            }

            /* ── Catalog: tab buttons ── */
            #catalogTabBtn {
                background: transparent;
                color: #939099;
                border: none;
                border-bottom: 2px solid transparent;
                border-radius: 0;
                padding: 8px 18px 8px 2px;
                font-size: 13px;
                font-weight: 700;
            }
            #catalogTabBtn:hover {
                color: #e3e2e7;
                background: transparent;
            }
            #catalogTabBtn[active="true"] {
                color: #d0bcff;
                border-bottom: 2px solid #d0bcff;
            }

            /* ── Catalog: monster card ── */
            #catalogCard {
                background-color: #1f1f24;
                border: 1px solid #252530;
                border-radius: 12px;
            }
            #catalogCard:hover {
                background-color: #292a2e;
                border: 1px solid #3d3a4a;
            }
            #catalogCardImage {
                background-color: #0d0e12;
                border-radius: 12px;
            }
            #catalogCardName {
                font-size: 15px;
                font-weight: 700;
                color: #e3e2e7;
            }

            /* ── Catalog: no-results ── */
            #catalogNoResults {
                color: #958ea0;
                font-size: 14px;
                padding: 48px 0;
            }

            /* ── Progress bar ── */
            QProgressBar {
                background-color: #292a2e;
                border: none;
                border-radius: 3px;
                max-height: 6px;
                min-height: 6px;
            }
            QProgressBar::chunk {
                background-color: #a6e3a1;
                border-radius: 3px;
            }

            /* ── Tooltip ── */
            QToolTip {
                background-color: #292a2e;
                color: #e3e2e7;
                border: 1px solid #343439;
                padding: 4px 8px;
            }

            /* ── Settings: page subtitle ── */
            #settingsSubtitle {
                color: #cbc3d7;
                font-size: 13px;
            }

            /* ── Settings: card surfaces ── */
            #settingsCard {
                background-color: #1f1f24;
                border: 1px solid #252530;
                border-radius: 12px;
            }
            #settingsCardLow {
                background-color: #1a1b20;
                border: 1px solid #252530;
                border-radius: 12px;
            }
            #settingsCardIcon {
                background-color: #343439;
                border-radius: 8px;
                font-size: 18px;
                min-width: 40px; max-width: 40px;
                min-height: 40px; max-height: 40px;
            }
            #settingsCardTitle {
                font-size: 16px;
                font-weight: 700;
                color: #e3e2e7;
            }
            #settingsSupportingText {
                color: #cbc3d7;
                font-size: 13px;
            }

            /* ── Settings: info rows ── */
            #settingsInfoLabel {
                color: #cbc3d7;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 1px;
            }
            #settingsInfoValue {
                font-size: 14px;
                font-weight: 700;
                color: #d0bcff;
            }
            #settingsInfoDivider {
                background-color: #252530;
                max-height: 1px;
                min-height: 1px;
            }

            /* ── Settings: status strip ── */
            #settingsStatusStrip {
                background-color: #0d0e12;
                border: 1px solid #252530;
                border-radius: 12px;
            }
            #settingsStatusBadge {
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 2px;
            }
            #settingsStatusBadge[tone="neutral"] { color: #958ea0; }
            #settingsStatusBadge[tone="accent"]  { color: #d0bcff; }
            #settingsStatusBadge[tone="success"] { color: #a6e3a1; }
            #settingsStatusBadge[tone="error"]   { color: #ffb4ab; }

            #settingsStatusDot {
                border-radius: 4px;
            }
            #settingsStatusDot[tone="neutral"] { background-color: #958ea0; }
            #settingsStatusDot[tone="accent"]  { background-color: #d0bcff; }
            #settingsStatusDot[tone="success"] { background-color: #a6e3a1; }
            #settingsStatusDot[tone="error"]   { background-color: #ffb4ab; }

            /* ── Settings: disclaimer ── */
            #settingsDisclaimerText {
                color: #cbc3d7;
                font-size: 11px;
                line-height: 1.6;
            }

            /* ── Settings: data table ── */
            #settingsDataCard {
                background-color: #1f1f24;
                border: 1px solid #252530;
                border-radius: 12px;
            }
            #settingsDataTable {
                background-color: transparent;
                border: none;
                gridline-color: transparent;
                outline: 0;
            }
            #settingsDataTable::item {
                border-bottom: 1px solid #252530;
                padding: 10px 12px;
            }
            #settingsDataTable QTableCornerButton::section {
                background-color: #292a2e;
                border: none;
            }
            #settingsDataTable QHeaderView::section {
                background-color: #292a2e;
                color: #958ea0;
                border: none;
                border-bottom: 1px solid #252530;
                padding: 10px 12px;
                font-size: 10px;
                font-weight: 700;
            }
            #settingsDataThumbFallback {
                background-color: #262332;
                border: 1px solid #343046;
                border-radius: 8px;
                color: #d0bcff;
                font-size: 12px;
                font-weight: 700;
            }
        """)
