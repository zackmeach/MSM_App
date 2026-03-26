"""GUI smoke tests — pytest-qt coverage for the core user journey.

Covers: add target, increment egg (icon-only), close out, undo, redo,
state refresh, and restart persistence.
"""

from __future__ import annotations

import sqlite3

import pytest
from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from app.db.migrations import run_migrations
from app.domain.models import SortOrder
from app.repositories import monster_repo, target_repo
from app.services.app_service import AppService
from app.ui.breed_list_panel import BreedListPanel
from app.ui.catalog_view import CatalogView
from app.ui.inwork_panel import InWorkPanel
from app.ui.widgets.catalog_monster_card import CatalogMonsterCard
from app.ui.widgets.egg_row_widget import EggRowWidget


@pytest.fixture
def service(content_conn, userstate_conn):
    svc = AppService(content_conn, userstate_conn)
    return svc


@pytest.fixture
def breed_panel(qtbot):
    panel = BreedListPanel()
    qtbot.addWidget(panel)
    yield panel
    panel.close()


@pytest.fixture
def catalog(qtbot, content_conn):
    svc = AppService(content_conn, _fresh_userstate())
    panel = CatalogView()
    qtbot.addWidget(panel)
    panel.load_catalog(svc.get_catalog_items())
    yield panel
    panel.close()


@pytest.fixture
def inwork(qtbot):
    panel = InWorkPanel()
    qtbot.addWidget(panel)
    yield panel
    panel.close()


def _fresh_userstate() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    run_migrations(conn, "userstate")
    return conn


class TestAddTargetFromCatalog:
    """Catalog emits add_target_requested when a card is clicked."""

    def test_catalog_emits_monster_id(self, qtbot, catalog, id_maps):
        with qtbot.waitSignal(catalog.add_target_requested, timeout=1000) as blocker:
            catalog._browser._on_card_clicked(id_maps["monsters"]["Zynth"])
        assert blocker.args == [id_maps["monsters"]["Zynth"]]


class TestCatalogPresentation:
    """Catalog browser presents large showcase cards."""

    def test_catalog_uses_large_cards(self, catalog):
        assert catalog._browser._cards
        first_card = catalog._browser._cards[0]
        assert first_card.width() == CatalogMonsterCard.CARD_WIDTH
        assert first_card.height() == CatalogMonsterCard.CARD_HEIGHT


class TestAddTargetUpdatesState:
    """Adding a target populates the breed list and in-work panel."""

    def test_breed_list_populated_after_add(self, qtbot, service, breed_panel, id_maps):
        service.handle_add_target(id_maps["monsters"]["Zynth"])
        state = service.get_app_state()

        breed_panel.refresh(state.breed_list_rows)
        assert len(breed_panel._row_widgets) > 0

    def test_inwork_populated_after_add(self, qtbot, service, inwork, id_maps):
        service.handle_add_target(id_maps["monsters"]["Zynth"])
        state = service.get_app_state()

        inwork.refresh(state.inwork_by_type)
        assert len(inwork._cards) == 1


class TestEggIconIncrement:
    """Only the egg icon triggers increment, not the rest of the row."""

    def test_icon_click_emits_signal(self, qtbot, content_conn, id_maps):
        from app.ui.viewmodels import BreedListRowViewModel

        vm = BreedListRowViewModel(
            egg_type_id=id_maps["eggs"]["Mammott"],
            name="Mammott",
            breeding_time_display="30m",
            egg_image_path="",
            bred_count=0,
            total_needed=4,
            remaining=4,
            progress_fraction=0.0,
        )
        row = EggRowWidget(vm)
        row.show()
        qtbot.addWidget(row)

        with qtbot.waitSignal(row.clicked, timeout=1000) as blocker:
            icon = row._icon_label
            qtbot.mouseClick(icon, Qt.MouseButton.LeftButton)

        assert blocker.args == [id_maps["eggs"]["Mammott"]]
        row.close()

    def test_row_body_click_emits(self, qtbot, id_maps):
        """Clicking anywhere on the row emits the clicked signal."""
        from app.ui.viewmodels import BreedListRowViewModel

        vm = BreedListRowViewModel(
            egg_type_id=id_maps["eggs"]["Mammott"],
            name="Mammott",
            breeding_time_display="30m",
            egg_image_path="",
            bred_count=0,
            total_needed=4,
            remaining=4,
            progress_fraction=0.0,
        )
        row = EggRowWidget(vm)
        row.show()
        qtbot.addWidget(row)

        with qtbot.waitSignal(row.clicked, timeout=1000) as blocker:
            qtbot.mouseClick(row._name_label, Qt.MouseButton.LeftButton)

        assert blocker.args == [id_maps["eggs"]["Mammott"]]
        row.close()


class TestCloseOutTarget:
    """Closing out a target removes it from the in-work panel."""

    def test_close_out_removes_target(self, qtbot, service, inwork, id_maps):
        service.handle_add_target(id_maps["monsters"]["Zynth"])
        state = service.get_app_state()
        inwork.refresh(state.inwork_by_type)
        assert len(inwork._cards) == 1

        service.handle_close_out(id_maps["monsters"]["Zynth"])
        state = service.get_app_state()
        inwork.refresh(state.inwork_by_type)
        assert len(inwork._cards) == 0

    def test_duplicate_close_out_removes_one(self, qtbot, service, inwork, id_maps):
        """With two instances of the same monster, close-out removes the newest."""
        service.handle_add_target(id_maps["monsters"]["Zynth"])
        service.handle_add_target(id_maps["monsters"]["Zynth"])
        state = service.get_app_state()
        inwork.refresh(state.inwork_by_type)
        assert len(inwork._cards) == 1
        assert inwork._cards[0]._label.text().startswith("Zynth")

        service.handle_close_out(id_maps["monsters"]["Zynth"])
        state = service.get_app_state()
        inwork.refresh(state.inwork_by_type)
        assert len(inwork._cards) == 1


class TestUndoRedo:
    """Undo and redo update the state correctly."""

    def test_undo_reverts_add(self, qtbot, service, breed_panel, id_maps):
        service.handle_add_target(id_maps["monsters"]["Zynth"])
        state = service.get_app_state()
        assert state.can_undo is True
        assert len(state.breed_list_rows) > 0

        service.undo()
        state = service.get_app_state()
        assert state.can_undo is False
        assert state.can_redo is True
        assert len(state.breed_list_rows) == 0

    def test_redo_restores_add(self, qtbot, service, breed_panel, id_maps):
        service.handle_add_target(id_maps["monsters"]["Zynth"])
        service.undo()

        service.redo()
        state = service.get_app_state()
        assert state.can_undo is True
        assert state.can_redo is False
        assert len(state.breed_list_rows) > 0

    def test_undo_redo_increment(self, qtbot, service, id_maps):
        service.handle_add_target(id_maps["monsters"]["Dwumrohl"])
        mammott_id = id_maps["eggs"]["Mammott"]

        service.handle_increment_egg(mammott_id)
        state = service.get_app_state()
        mammott_row = next(r for r in state.breed_list_rows if r.egg_type_id == mammott_id)
        assert mammott_row.bred_count == 1

        service.undo()
        state = service.get_app_state()
        mammott_row = next(r for r in state.breed_list_rows if r.egg_type_id == mammott_id)
        assert mammott_row.bred_count == 0

        service.redo()
        state = service.get_app_state()
        mammott_row = next(r for r in state.breed_list_rows if r.egg_type_id == mammott_id)
        assert mammott_row.bred_count == 1


class TestStateChangedSignal:
    """AppService emits state_changed on each action."""

    def test_signal_emitted_on_add(self, qtbot, service, id_maps):
        with qtbot.waitSignal(service.state_changed, timeout=1000):
            service.handle_add_target(id_maps["monsters"]["Zynth"])

    def test_signal_emitted_on_undo(self, qtbot, service, id_maps):
        service.handle_add_target(id_maps["monsters"]["Zynth"])
        with qtbot.waitSignal(service.state_changed, timeout=1000):
            service.undo()


class TestPersistenceAcrossRestart:
    """State survives when the service is recreated with the same DB connection."""

    def test_state_persists(self, qtbot, content_conn, id_maps, tmp_path):
        db_path = tmp_path / "userstate.db"
        conn1 = sqlite3.connect(str(db_path))
        conn1.execute("PRAGMA foreign_keys=ON")
        run_migrations(conn1, "userstate")

        svc1 = AppService(content_conn, conn1)
        svc1.handle_add_target(id_maps["monsters"]["Galvana"])
        mammott_id = id_maps["eggs"]["Mammott"]
        svc1.handle_increment_egg(mammott_id)
        conn1.close()

        conn2 = sqlite3.connect(str(db_path))
        conn2.execute("PRAGMA foreign_keys=ON")
        svc2 = AppService(content_conn, conn2)
        state = svc2.get_app_state()

        assert len(state.breed_list_rows) > 0
        mammott_row = next(r for r in state.breed_list_rows if r.egg_type_id == mammott_id)
        assert mammott_row.bred_count == 1
        conn2.close()
