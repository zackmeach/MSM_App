"""GUI tests for the Settings page skeleton and update-state rendering."""

from __future__ import annotations

import sqlite3

import pytest
from PySide6.QtWidgets import QApplication

from app.db.migrations import run_migrations
from app.services.app_service import AppService
from app.ui.settings_panel import SettingsPanel
from app.ui.viewmodels import (
    BBB_DISCLAIMER,
    SettingsDataRowViewModel,
    SettingsUpdateState,
    SettingsViewModel,
    UpdateStatus,
)


@pytest.fixture
def panel(qtbot):
    p = SettingsPanel()
    qtbot.addWidget(p)
    yield p
    p.close()


class TestSettingsPanelStructure:
    """The page skeleton contains the expected major sections."""

    def test_has_update_button(self, panel):
        assert panel._update_btn is not None
        assert panel._update_btn.text() == "Check for Updates"

    def test_has_db_info_rows(self, panel):
        assert panel._row_version is not None
        assert panel._row_schema is not None
        assert panel._row_updated is not None

    def test_has_disclaimer_label(self, panel):
        assert panel._disclaimer_label is not None

    def test_has_app_version_label(self, panel):
        assert panel._app_version_label is not None

    def test_has_data_table(self, panel):
        assert panel._data_table is not None


class TestSettingsPanelRefresh:
    """refresh() populates all metadata from a SettingsViewModel."""

    def test_metadata_populated(self, panel):
        vm = SettingsViewModel(
            content_version="1.2.0",
            schema_version="4",
            last_updated_display="2026-01-15T00:00:00Z",
            app_version="1.0.0",
            disclaimer_text="Test disclaimer",
            data_rows=[
                SettingsDataRowViewModel(
                    monster_id=1,
                    monster_name="Zynth",
                    monster_type="wublin",
                    monster_type_label="Wublin",
                    image_path="",
                    is_placeholder=True,
                    eggs_required_display="6 Eggs",
                    duration_display="N/A",
                )
            ],
        )
        panel.refresh(vm)

        assert panel._row_version._value.text() == "1.2.0"
        assert panel._row_schema._value.text() == "4"
        assert "2026" in panel._row_updated._value.text()
        assert panel._app_version_label.text() == "1.0.0"
        assert panel._disclaimer_label.text() == "Test disclaimer"
        assert panel._data_table.rowCount() == 1
        assert panel._data_table.item(0, 1).text() == "Zynth"

    def test_refresh_sets_idle_update_state(self, panel):
        vm = SettingsViewModel()
        panel.refresh(vm)
        assert panel._update_btn.isEnabled() is True
        assert panel._update_btn.text() == "Check for Updates"


class TestSettingsUpdateStateRendering:
    """set_update_state() drives the update card UI declaratively."""

    def test_idle_state(self, panel):
        panel.set_update_state(SettingsUpdateState.idle())
        assert panel._update_btn.isEnabled() is True
        assert panel._is_install_action is False

    def test_checking_disables_button(self, panel):
        panel.set_update_state(SettingsUpdateState.checking())
        assert panel._update_btn.isEnabled() is False

    def test_available_enables_install(self, panel):
        panel.set_update_state(SettingsUpdateState.available("3.0.0"))
        assert panel._update_btn.isEnabled() is True
        assert panel._is_install_action is True
        assert "3.0.0" in panel._update_btn.text()

    def test_no_update(self, panel):
        panel.set_update_state(SettingsUpdateState.no_update())
        assert panel._update_btn.isEnabled() is True
        assert panel._is_install_action is False
        assert "up to date" in panel._status_headline.text().lower()

    def test_staging_disables_button(self, panel):
        panel.set_update_state(SettingsUpdateState.staging("Downloading\u2026"))
        assert panel._update_btn.isEnabled() is False

    def test_success_shows_version(self, panel):
        panel.set_update_state(SettingsUpdateState.success("2.5.0"))
        assert panel._update_btn.isEnabled() is True
        assert "2.5.0" in panel._status_headline.text()

    def test_error_shows_detail(self, panel):
        panel.set_update_state(SettingsUpdateState.error("Network failure"))
        assert panel._update_btn.isEnabled() is True
        assert not panel._status_detail.isHidden()
        assert "Network failure" in panel._status_detail.text()

    def test_error_button_says_retry(self, panel):
        panel.set_update_state(SettingsUpdateState.error("fail"))
        assert "Retry" in panel._update_btn.text()


class TestSettingsSignals:
    """Button click emits the correct signal based on update state."""

    def test_check_signal_on_idle(self, qtbot, panel):
        panel.set_update_state(SettingsUpdateState.idle())
        with qtbot.waitSignal(panel.check_update_requested, timeout=1000):
            panel._update_btn.click()

    def test_apply_signal_when_available(self, qtbot, panel):
        panel.set_update_state(SettingsUpdateState.available("2.0.0"))
        with qtbot.waitSignal(panel.apply_update_requested, timeout=1000):
            panel._update_btn.click()

    def test_check_signal_after_error_retry(self, qtbot, panel):
        panel.set_update_state(SettingsUpdateState.error("fail"))
        with qtbot.waitSignal(panel.check_update_requested, timeout=1000):
            panel._update_btn.click()


class TestSettingsNavigationRefresh:
    """Simulates what MainWindow does on navigate-to-Settings."""

    def test_full_refresh_from_app_service(self, content_conn, userstate_conn):
        content_conn.execute(
            "UPDATE update_metadata SET value='1.8.0' WHERE key='content_version'"
        )
        content_conn.execute(
            "UPDATE update_metadata SET value='2026-10-01T12:00:00Z' WHERE key='last_updated_utc'"
        )
        content_conn.commit()

        svc = AppService(content_conn, userstate_conn)
        vm = svc.get_settings_viewmodel()

        panel = SettingsPanel()
        panel.refresh(vm)

        assert panel._row_version._value.text() == "1.8.0"
        assert panel._row_schema._value.text() == "2"
        assert "2026" in panel._row_updated._value.text()
        assert BBB_DISCLAIMER in panel._disclaimer_label.text()
        assert panel._data_table.rowCount() > 0
        panel.close()
