"""Main application window — navigation, keyboard shortcuts, and panel wiring."""

from __future__ import annotations

from typing import TYPE_CHECKING

import sqlite3

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
from app.ui import themes
from app.ui.viewmodels import AppStateViewModel, SettingsUpdateState
from app.ui.widgets.toast_widget import ToastWidget
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
        self._audio = AudioPlayer(context.bundle_dir / "audio")
        self._updater = UpdateService(context.data_dir, context.conn_content)
        self._update_state = SettingsUpdateState.idle()
        self._load_ui_prefs()
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

        # Inject audio so egg-row clicks and close-outs play sfx.
        self._home.breed_list_panel.set_audio(self._audio)

        self._toast = ToastWidget(central)

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
        self._service.target_added.connect(self._on_target_added)
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
        self._settings.ui_options_apply_requested.connect(self._on_ui_options_apply)
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
        # Update catalog badge counts from in-work data
        badge_counts: dict[int, int] = {}
        for monsters in state.inwork_by_type.values():
            for m in monsters:
                badge_counts[m.monster_id] = m.count
        self._catalog.update_active_counts(badge_counts)
        self._btn_undo.setEnabled(state.can_undo)
        self._btn_redo.setEnabled(state.can_redo)

    def _on_completion(self, egg_type_id: int) -> None:
        # The row's own animation plays the closeout sound at the start of its
        # grow/collapse sequence — no separate ding here, since both firing at
        # the same instant overlap and muddy the audio cue.
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

    def _on_target_added(self, name: str) -> None:
        self._toast.show_message(f"Added {name} to tracker")

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

        self._service.reconcile_after_content_update()

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

    def _apply_stylesheet(self) -> None:
        self.setStyleSheet(themes.build_stylesheet())

    # ── UI preferences ──

    def _load_ui_prefs(self) -> None:
        """Load saved theme/font preferences and activate them."""
        saved_theme = self._service.get_ui_pref("ui_theme", themes.DEFAULT_THEME)
        saved_font = self._service.get_ui_pref("ui_font_size", "Default")
        font_offset = 0
        for label, offset in themes.FONT_SIZE_OPTIONS:
            if label == saved_font:
                font_offset = offset
                break
        themes.set_active(saved_theme, font_offset)

    def _on_ui_options_apply(self, theme_name: str, font_size_label: str) -> None:
        """Persist UI prefs and reapply the stylesheet."""
        font_offset = 0
        for label, offset in themes.FONT_SIZE_OPTIONS:
            if label == font_size_label:
                font_offset = offset
                break

        themes.set_active(theme_name, font_offset)

        self._service.set_ui_pref("ui_theme", theme_name)
        self._service.set_ui_pref("ui_font_size", font_size_label)

        self._apply_stylesheet()

        # Refresh UI so widgets pick up new theme colours
        self._catalog.load_catalog(self._service.get_catalog_items())
        state = self._service.get_app_state()
        self._on_state_changed(state)
        self._settings.refresh(self._service.get_settings_viewmodel())
