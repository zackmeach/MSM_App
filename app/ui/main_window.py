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

from app.assets import resolver
from app.services.app_service import AppService
from app.services.audio_player import AudioPlayer
from app.ui.catalog_panel import CatalogPanel
from app.ui.home_view import HomeView
from app.ui.settings_panel import SettingsPanel
from app.ui.viewmodels import AppStateViewModel

if TYPE_CHECKING:
    from app.bootstrap import AppContext


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
        nav_l.setContentsMargins(12, 6, 12, 6)

        self._btn_home = QPushButton("Home")
        self._btn_catalog = QPushButton("Catalog")
        self._btn_settings = QPushButton("Settings")
        for btn in (self._btn_home, self._btn_catalog, self._btn_settings):
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            nav_l.addWidget(btn)
        nav_l.addStretch()
        title = QLabel("MSM Awakening Tracker")
        title.setObjectName("appTitle")
        nav_l.addWidget(title)
        root.addWidget(nav)

        # ── Pages ──
        self._stack = QStackedWidget()
        self._home = HomeView()
        self._catalog = CatalogPanel()
        self._settings = SettingsPanel()

        self._stack.addWidget(self._home)
        self._stack.addWidget(self._catalog)
        self._stack.addWidget(self._settings)
        root.addWidget(self._stack, stretch=1)

        # ── Nav wiring ──
        self._btn_home.clicked.connect(lambda: self._stack.setCurrentIndex(0))
        self._btn_catalog.clicked.connect(lambda: self._stack.setCurrentIndex(1))
        self._btn_settings.clicked.connect(lambda: self._show_settings())

        # ── Keyboard shortcuts ──
        QShortcut(QKeySequence("Ctrl+Z"), self).activated.connect(self._service.undo)
        QShortcut(QKeySequence("Ctrl+Y"), self).activated.connect(self._service.redo)
        QShortcut(QKeySequence("Ctrl+Shift+Z"), self).activated.connect(self._service.redo)

        self._apply_stylesheet()

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

    def _initial_load(self) -> None:
        self._catalog.load_catalog(self._service.get_catalog_items())
        state = self._service.get_app_state()
        self._on_state_changed(state)
        self._home.breed_list_panel.set_sort_order(state.sort_order)

    def _on_state_changed(self, state: AppStateViewModel) -> None:
        self._home.breed_list_panel.refresh(state.breed_list_rows)
        self._home.inwork_panel.refresh(state.inwork_by_type)

    def _on_completion(self, egg_type_id: int) -> None:
        self._audio.play_ding()
        self._home.breed_list_panel.on_completion(egg_type_id)

    def _show_settings(self) -> None:
        self._settings.refresh(self._service.get_settings_viewmodel())
        self._stack.setCurrentIndex(2)

    def _on_error(self, msg: str) -> None:
        QMessageBox.warning(self, "Error", msg)

    def _apply_stylesheet(self) -> None:
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e2e; }
            QWidget { color: #cdd6f4; font-family: "Segoe UI", sans-serif; font-size: 13px; }
            #navBar { background-color: #181825; border-bottom: 1px solid #313244; }
            #appTitle { font-size: 15px; font-weight: bold; color: #89b4fa; }
            #panelTitle { font-size: 16px; font-weight: bold; color: #cdd6f4; margin-bottom: 4px; }
            #sectionLabel { font-size: 13px; font-weight: bold; color: #a6adc8; margin-top: 8px; }
            #emptyHint { color: #6c7086; font-size: 13px; padding: 24px; }
            #disclaimerText { color: #a6adc8; font-size: 12px; }
            QPushButton {
                background-color: #313244; color: #cdd6f4; border: none;
                border-radius: 6px; padding: 6px 16px; font-size: 13px;
            }
            QPushButton:hover { background-color: #45475a; }
            QPushButton:pressed { background-color: #585b70; }
            QComboBox {
                background-color: #313244; color: #cdd6f4; border: 1px solid #45475a;
                border-radius: 4px; padding: 4px 8px;
            }
            QLineEdit {
                background-color: #313244; color: #cdd6f4; border: 1px solid #45475a;
                border-radius: 4px; padding: 6px 10px;
            }
            QScrollArea { border: none; background: transparent; }
            QTabWidget::pane { border: none; }
            QTabBar::tab {
                background-color: #313244; color: #a6adc8; padding: 6px 14px;
                border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 2px;
            }
            QTabBar::tab:selected { background-color: #45475a; color: #cdd6f4; }
            QProgressBar { background-color: #45475a; border-radius: 4px; max-height: 8px; }
            QProgressBar::chunk { background-color: #a6e3a1; border-radius: 4px; }
        """)
