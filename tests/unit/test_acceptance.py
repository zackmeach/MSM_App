"""SRS acceptance criteria scenarios (AC-R01 through AC-R06) adapted for
the satisfaction-aware state model.
"""

from __future__ import annotations

import pytest

from app.commands.add_target import AddTargetCommand
from app.commands.close_out_target import CloseOutTargetCommand
from app.commands.increment_egg import IncrementEggCommand
from app.domain.breed_list import derive_breed_list
from app.domain.models import SortOrder
from app.repositories import monster_repo, target_repo


def _derive(userstate_conn, content_conn):
    progress = target_repo.fetch_all_progress(userstate_conn)
    egg_map = monster_repo.fetch_egg_types_map(content_conn)
    return derive_breed_list(progress, egg_map, SortOrder.TIME_DESC)


class TestAC_R01_CloseOutRemovesOrphanedRows:
    """Two targets both require Mammott. Only target A requires Tweedle.
    Close out A → Mammott stays, Tweedle row disappears."""

    def test(self, content_conn, userstate_conn, id_maps):
        reqs = monster_repo.fetch_all_requirements(content_conn)
        # Dwumrohl needs: 2 Mammott, 2 Noggin, 2 Potbelly, 2 Toe Jammer
        # Galvana needs: 2 Bowgart, 4 Mammott, 2 Tweedle, 1 Furcorn
        add_a = AddTargetCommand(id_maps["monsters"]["Galvana"], content_conn, userstate_conn, reqs)
        add_b = AddTargetCommand(id_maps["monsters"]["Dwumrohl"], content_conn, userstate_conn, reqs)
        add_a.execute()
        add_b.execute()

        rows_before = _derive(userstate_conn, content_conn)
        egg_names_before = {r.name for r in rows_before}
        assert "Mammott" in egg_names_before
        assert "Tweedle" in egg_names_before

        # Close out Galvana (target A)
        targets = target_repo.fetch_all_targets(userstate_conn)
        galvana_t = next(t for t in targets if t.monster_id == id_maps["monsters"]["Galvana"])
        close_cmd = CloseOutTargetCommand(galvana_t.id, userstate_conn)
        close_cmd.execute()

        rows_after = _derive(userstate_conn, content_conn)
        egg_names_after = {r.name for r in rows_after}
        # Mammott still needed by Dwumrohl
        assert "Mammott" in egg_names_after
        # Tweedle was only needed by Galvana — should be gone
        assert "Tweedle" not in egg_names_after
        # Bowgart and Furcorn also only Galvana — gone
        assert "Bowgart" not in egg_names_after
        assert "Furcorn" not in egg_names_after


class TestAC_R02_NoOrphanedRowsAfterCloseOut:
    """After any close-out, every remaining row is required by at least one target."""

    def test(self, content_conn, userstate_conn, id_maps):
        reqs = monster_repo.fetch_all_requirements(content_conn)
        for name in ["Zynth", "Galvana", "Attmoz"]:
            AddTargetCommand(id_maps["monsters"][name], content_conn, userstate_conn, reqs).execute()

        targets = target_repo.fetch_all_targets(userstate_conn)
        # Close out each target one by one
        for t in targets:
            CloseOutTargetCommand(t.id, userstate_conn).execute()

        rows = _derive(userstate_conn, content_conn)
        assert rows == []
        assert target_repo.fetch_all_progress(userstate_conn) == []


class TestAC_R04_UndoRestoresCompletePriorState:
    """Close out a target, then Ctrl+Z → prior state restored atomically."""

    def test(self, content_conn, userstate_conn, id_maps):
        reqs = monster_repo.fetch_all_requirements(content_conn)
        add_cmd = AddTargetCommand(id_maps["monsters"]["Galvana"], content_conn, userstate_conn, reqs)
        add_cmd.execute()

        # Increment Mammott twice
        mammott_id = id_maps["eggs"]["Mammott"]
        inc1 = IncrementEggCommand(mammott_id, userstate_conn)
        inc2 = IncrementEggCommand(mammott_id, userstate_conn)
        inc1.execute()
        inc2.execute()

        rows_before = _derive(userstate_conn, content_conn)

        # Close out
        target = target_repo.fetch_all_targets(userstate_conn)[0]
        close_cmd = CloseOutTargetCommand(target.id, userstate_conn)
        close_cmd.execute()

        # Undo
        close_cmd.undo()

        rows_after = _derive(userstate_conn, content_conn)
        assert len(rows_before) == len(rows_after)

        for rb, ra in zip(
            sorted(rows_before, key=lambda r: r.egg_type_id),
            sorted(rows_after, key=lambda r: r.egg_type_id),
        ):
            assert rb.egg_type_id == ra.egg_type_id
            assert rb.bred_count == ra.bred_count
            assert rb.total_needed == ra.total_needed


class TestAC_R05_BredCountNeverExceedsTotal:
    """Invariant: bred_count <= total_needed after every operation."""

    def _check_invariant(self, userstate_conn, content_conn):
        progress = target_repo.fetch_all_progress(userstate_conn)
        for p in progress:
            assert p.satisfied_count <= p.required_count, (
                f"Invariant violated: target={p.active_target_id} egg={p.egg_type_id} "
                f"satisfied={p.satisfied_count} required={p.required_count}"
            )

    def test(self, content_conn, userstate_conn, id_maps):
        reqs = monster_repo.fetch_all_requirements(content_conn)
        add1 = AddTargetCommand(id_maps["monsters"]["Dwumrohl"], content_conn, userstate_conn, reqs)
        add1.execute()
        self._check_invariant(userstate_conn, content_conn)

        mammott_id = id_maps["eggs"]["Mammott"]
        for _ in range(2):
            IncrementEggCommand(mammott_id, userstate_conn).execute()
            self._check_invariant(userstate_conn, content_conn)

        add2 = AddTargetCommand(id_maps["monsters"]["Galvana"], content_conn, userstate_conn, reqs)
        add2.execute()
        self._check_invariant(userstate_conn, content_conn)

        target = target_repo.fetch_all_targets(userstate_conn)[0]
        CloseOutTargetCommand(target.id, userstate_conn).execute()
        self._check_invariant(userstate_conn, content_conn)


class TestRedoStackClearedOnNewAction:
    """FR-507: performing a new action clears the redo stack."""

    def test(self, content_conn, userstate_conn, id_maps):
        reqs = monster_repo.fetch_all_requirements(content_conn)

        add1 = AddTargetCommand(id_maps["monsters"]["Dwumrohl"], content_conn, userstate_conn, reqs)
        add1.execute()

        mammott_id = id_maps["eggs"]["Mammott"]
        inc1 = IncrementEggCommand(mammott_id, userstate_conn)
        inc1.execute()

        # Undo the increment
        inc1.undo()

        # Now do a different action instead of redo
        inc2 = IncrementEggCommand(id_maps["eggs"]["Noggin"], userstate_conn)
        inc2.execute()

        # The redo of inc1 should no longer be valid in a real AppService;
        # here we verify the data state is consistent
        rows = target_repo.fetch_progress_for_egg(userstate_conn, mammott_id)
        assert all(r.satisfied_count == 0 for r in rows)
        noggin_rows = target_repo.fetch_progress_for_egg(userstate_conn, id_maps["eggs"]["Noggin"])
        assert any(r.satisfied_count == 1 for r in noggin_rows)


class TestPersistenceAcrossRestart:
    """State survives when connections are closed and re-opened."""

    def test(self, content_conn, id_maps, tmp_path):
        import sqlite3
        from app.db.migrations import run_migrations

        db_path = tmp_path / "userstate.db"
        conn1 = sqlite3.connect(str(db_path))
        conn1.execute("PRAGMA foreign_keys=ON")
        run_migrations(conn1, "userstate")

        reqs = monster_repo.fetch_all_requirements(content_conn)
        add_cmd = AddTargetCommand(id_maps["monsters"]["Galvana"], content_conn, conn1, reqs)
        add_cmd.execute()

        mammott_id = id_maps["eggs"]["Mammott"]
        IncrementEggCommand(mammott_id, conn1).execute()
        conn1.close()

        # "Restart" — open a fresh connection
        conn2 = sqlite3.connect(str(db_path))
        conn2.execute("PRAGMA foreign_keys=ON")

        targets = target_repo.fetch_all_targets(conn2)
        assert len(targets) == 1

        progress = target_repo.fetch_progress_for_egg(conn2, mammott_id)
        assert any(r.satisfied_count == 1 for r in progress)
        conn2.close()
