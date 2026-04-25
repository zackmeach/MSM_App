"""Tests for the Settings view-model and update-state dataclasses."""

from __future__ import annotations

from app.ui.viewmodels import (
    APP_VERSION,
    BBB_DISCLAIMER,
    SettingsDataRowViewModel,
    SettingsUpdateState,
    SettingsViewModel,
    UpdateStatus,
)


class TestSettingsUpdateStateFactories:
    """Each factory method should produce consistent, complete state objects."""

    def test_idle_defaults(self):
        s = SettingsUpdateState.idle()
        assert s.status == UpdateStatus.IDLE
        assert s.button_enabled is True
        assert s.is_install_action is False
        assert s.tone == "neutral"

    def test_checking(self):
        s = SettingsUpdateState.checking()
        assert s.status == UpdateStatus.CHECKING
        assert s.button_enabled is False
        assert "Checking" in s.button_label

    def test_available(self):
        s = SettingsUpdateState.available("2.0.0")
        assert s.status == UpdateStatus.UPDATE_AVAILABLE
        assert s.button_enabled is True
        assert s.is_install_action is True
        assert "2.0.0" in s.button_label
        assert s.remote_version == "2.0.0"
        assert s.tone == "accent"

    def test_no_update(self):
        s = SettingsUpdateState.no_update()
        assert s.status == UpdateStatus.NO_UPDATE
        assert s.button_enabled is True
        assert s.is_install_action is False
        assert s.tone == "success"
        assert "up to date" in s.status_headline.lower()

    def test_staging(self):
        s = SettingsUpdateState.staging("Downloading\u2026")
        assert s.status == UpdateStatus.STAGING
        assert s.button_enabled is False
        assert "Downloading" in s.status_headline

    def test_staging_default_detail(self):
        s = SettingsUpdateState.staging()
        assert s.status == UpdateStatus.STAGING
        assert s.status_headline  # non-empty default

    def test_finalizing(self):
        s = SettingsUpdateState.finalizing()
        assert s.status == UpdateStatus.FINALIZING
        assert s.button_enabled is False

    def test_success(self):
        s = SettingsUpdateState.success("2.0.0")
        assert s.status == UpdateStatus.SUCCESS
        assert s.button_enabled is True
        assert s.tone == "success"
        assert "2.0.0" in s.status_headline

    def test_error(self):
        s = SettingsUpdateState.error("Network timeout")
        assert s.status == UpdateStatus.ERROR
        assert s.button_enabled is True
        assert s.tone == "error"
        assert "Retry" in s.button_label
        assert "Network timeout" in s.status_detail


class TestSettingsViewModel:
    """SettingsViewModel carries metadata + update state together."""

    def test_defaults(self):
        vm = SettingsViewModel()
        assert vm.app_version == APP_VERSION
        assert vm.disclaimer_text == BBB_DISCLAIMER
        assert vm.update_state.status == UpdateStatus.IDLE

    def test_metadata_fields(self):
        vm = SettingsViewModel(
            content_version="1.2.0",
            schema_version="4",
            last_updated_display="2026-03-01T00:00:00Z",
        )
        assert vm.content_version == "1.2.0"
        assert vm.schema_version == "4"
        assert "2026" in vm.last_updated_display

    def test_data_rows(self):
        vm = SettingsViewModel(
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
            ]
        )
        assert len(vm.data_rows) == 1
        assert vm.data_rows[0].monster_name == "Zynth"

    def test_frozen(self):
        vm = SettingsViewModel()
        try:
            vm.content_version = "changed"  # type: ignore[misc]
            assert False, "should be frozen"
        except AttributeError:
            pass


class TestSettingsViewModelFromAppService:
    """AppService.get_settings_viewmodel() builds the VM from content DB metadata."""

    def test_metadata_from_content_db(self, content_conn, userstate_conn):
        content_conn.execute(
            "UPDATE update_metadata SET value='1.5.0' WHERE key='content_version'"
        )
        content_conn.execute(
            "UPDATE update_metadata SET value='2026-06-15T12:00:00Z' WHERE key='last_updated_utc'"
        )
        content_conn.commit()

        from app.services.app_service import AppService

        svc = AppService(content_conn, userstate_conn)
        vm = svc.get_settings_viewmodel()
        assert vm.content_version == "1.5.0"
        assert vm.schema_version == "3"
        assert "2026-06-15" in vm.last_updated_display
        assert len(vm.data_rows) > 0
        assert vm.update_state.status == UpdateStatus.IDLE
