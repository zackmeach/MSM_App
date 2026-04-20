"""Tests for new UI features — toast widget, catalog badges, settings Apply."""

from __future__ import annotations

import sqlite3

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from app.db.migrations import run_migrations
from app.services.app_service import AppService
from app.ui.widgets.catalog_monster_card import CatalogMonsterCard
from app.ui.widgets.toast_widget import ToastWidget


# ── Toast Widget ───────────────────────────────────────────────────────


class TestToastWidget:
    """ToastWidget constructs and shows messages without crashing."""

    def test_construction(self, qtbot):
        parent = QWidget()
        qtbot.addWidget(parent)
        toast = ToastWidget(parent)
        assert toast.objectName() == "toast"
        assert not toast.isVisible()
        parent.close()

    def test_show_message_makes_visible(self, qtbot):
        parent = QWidget()
        parent.resize(400, 300)
        qtbot.addWidget(parent)
        parent.show()
        toast = ToastWidget(parent)
        toast.show_message("Test notification")
        assert toast.isVisible()
        assert toast.text() == "Test notification"
        parent.close()

    def test_minimum_width(self, qtbot):
        parent = QWidget()
        parent.resize(400, 300)
        qtbot.addWidget(parent)
        parent.show()
        toast = ToastWidget(parent)
        toast.show_message("Hi")
        assert toast.width() >= 200
        parent.close()


# ── Catalog Badge ──────────────────────────────────────────────────────


class TestCatalogMonsterCardBadge:
    """set_active_count shows/hides the iOS-style badge."""

    def test_badge_hidden_by_default(self, qtbot):
        card = CatalogMonsterCard(1, "Test Monster", "", monster_type="wublin")
        qtbot.addWidget(card)
        assert not card._badge.isVisible()
        card.close()

    def test_badge_shown_with_count(self, qtbot):
        card = CatalogMonsterCard(1, "Test Monster", "", monster_type="wublin")
        qtbot.addWidget(card)
        card.set_active_count(3)
        # Use isHidden() — isVisible() requires the parent chain to be shown
        assert not card._badge.isHidden()
        assert card._badge.text() == "3"
        card.close()

    def test_badge_hidden_when_zero(self, qtbot):
        card = CatalogMonsterCard(1, "Test Monster", "", monster_type="wublin")
        qtbot.addWidget(card)
        card.set_active_count(3)
        card.set_active_count(0)
        assert card._badge.isHidden()
        card.close()

    def test_monster_id_property(self, qtbot):
        card = CatalogMonsterCard(42, "Test", "", monster_type="celestial")
        qtbot.addWidget(card)
        assert card.monster_id == 42
        card.close()


# ── Catalog Badge Count Updates ────────────────────────────────────────


class TestCatalogBadgeUpdates:
    """AppService populates active_count in catalog items."""

    def test_catalog_items_have_zero_count_initially(self, content_conn, userstate_conn):
        svc = AppService(content_conn, userstate_conn)
        items = svc.get_catalog_items()
        assert all(it.active_count == 0 for it in items)

    def test_catalog_items_reflect_active_targets(self, content_conn, userstate_conn, id_maps):
        svc = AppService(content_conn, userstate_conn)
        svc.handle_add_target(id_maps["monsters"]["Zynth"])
        items = svc.get_catalog_items()
        zynth_item = next(it for it in items if it.name == "Zynth")
        assert zynth_item.active_count == 1

    def test_catalog_items_count_multiple_targets(self, content_conn, userstate_conn, id_maps):
        svc = AppService(content_conn, userstate_conn)
        svc.handle_add_target(id_maps["monsters"]["Zynth"])
        svc.handle_add_target(id_maps["monsters"]["Zynth"])
        items = svc.get_catalog_items()
        zynth_item = next(it for it in items if it.name == "Zynth")
        assert zynth_item.active_count == 2


# ── Catalog Browser Badge Pass-through ─────────────────────────────────


class TestCatalogBrowserBadgePassthrough:
    """CatalogBrowserPanel.update_active_counts updates card badges."""

    def test_update_active_counts(self, qtbot, content_conn):
        from app.ui.catalog_browser_panel import CatalogBrowserPanel

        svc = AppService(content_conn, _fresh_userstate())
        panel = CatalogBrowserPanel()
        qtbot.addWidget(panel)
        panel.load_catalog(svc.get_catalog_items())

        # All badges should be hidden initially
        for card in panel._cards:
            assert card._badge.isHidden()

        # Set a count for the first visible card
        if panel._cards:
            mid = panel._cards[0].monster_id
            panel.update_active_counts({mid: 2})
            assert not panel._cards[0]._badge.isHidden()
            assert panel._cards[0]._badge.text() == "2"

        panel.close()


# ── Settings Apply Button ──────────────────────────────────────────────


class TestSettingsApplyButton:
    """Settings panel Apply button emits signal and shows feedback."""

    def test_apply_emits_signal(self, qtbot, content_conn, userstate_conn):
        from app.ui.settings_panel import SettingsPanel

        svc = AppService(content_conn, userstate_conn)
        panel = SettingsPanel()
        qtbot.addWidget(panel)
        panel.refresh(svc.get_settings_viewmodel())

        with qtbot.waitSignal(
            panel.ui_options_apply_requested, timeout=1000
        ) as blocker:
            panel._on_ui_apply()

        assert len(blocker.args) == 2  # theme, font_label
        panel.close()

    def test_apply_shows_feedback_text(self, qtbot, content_conn, userstate_conn):
        from app.ui.settings_panel import SettingsPanel

        svc = AppService(content_conn, userstate_conn)
        panel = SettingsPanel()
        qtbot.addWidget(panel)
        panel.refresh(svc.get_settings_viewmodel())

        panel._on_ui_apply()
        assert "Applied" in panel._ui_apply_btn.text()
        assert not panel._ui_apply_btn.isEnabled()
        panel.close()


# ── Settings set_ui_options Fallback ───────────────────────────────────


class TestSettingsSetUiOptions:
    """set_ui_options falls back to index 0 for unknown values."""

    def test_set_ui_options_valid_theme(self, qtbot, content_conn, userstate_conn):
        from app.ui.settings_panel import SettingsPanel

        svc = AppService(content_conn, userstate_conn)
        panel = SettingsPanel()
        qtbot.addWidget(panel)
        panel.refresh(svc.get_settings_viewmodel())

        panel.set_ui_options("Classic Dark", "Default")
        assert panel._theme_combo.currentData() == "Classic Dark"
        panel.close()

    def test_set_ui_options_invalid_theme_falls_back(self, qtbot, content_conn, userstate_conn):
        from app.ui.settings_panel import SettingsPanel

        svc = AppService(content_conn, userstate_conn)
        panel = SettingsPanel()
        qtbot.addWidget(panel)
        panel.refresh(svc.get_settings_viewmodel())

        panel.set_ui_options("Nonexistent Theme", "Default")
        # Falls back to index 0
        assert panel._theme_combo.currentIndex() == 0
        panel.close()


class TestTargetAddedSignal:
    def test_add_failure_does_not_emit_success_signal(self, content_conn, userstate_conn):
        content_conn.execute(
            "INSERT INTO monsters(name, monster_type, image_path, wiki_slug, is_placeholder, content_key) "
            "VALUES('BrokenMon', 'wublin', '', 'BrokenMon', 1, 'monster:wublin:brokenmon')"
        )
        content_conn.commit()
        monster_id = content_conn.execute(
            "SELECT id FROM monsters WHERE name = 'BrokenMon'"
        ).fetchone()[0]

        svc = AppService(content_conn, userstate_conn)
        added = []
        errors = []
        svc.target_added.connect(added.append)
        svc.error_occurred.connect(errors.append)

        svc.handle_add_target(monster_id)

        assert added == []
        assert errors


def _fresh_userstate() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    run_migrations(conn, "userstate")
    return conn
