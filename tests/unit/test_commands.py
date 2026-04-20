"""Tests for all three command types and undo/redo correctness."""

from __future__ import annotations

import sqlite3

import pytest

from app.commands.add_target import AddTargetCommand
from app.commands.close_out_target import CloseOutTargetCommand
from app.commands.increment_egg import IncrementEggCommand
from app.repositories import monster_repo, target_repo


class TestAddTargetCommand:
    def test_execute_creates_target_and_progress(self, content_conn, userstate_conn, id_maps):
        reqs = monster_repo.fetch_all_requirements(content_conn)
        mid = id_maps["monsters"]["Zynth"]
        cmd = AddTargetCommand(mid, content_conn, userstate_conn, reqs)
        cmd.execute()

        targets = target_repo.fetch_all_targets(userstate_conn)
        assert len(targets) == 1
        assert targets[0].monster_id == mid
        assert targets[0].monster_key == "monster:wublin:zynth"

        progress = target_repo.fetch_all_progress(userstate_conn)
        assert len(progress) == 4  # Zynth needs 4 egg types
        assert all(row.egg_key for row in progress)

    def test_undo_removes_target_and_progress(self, content_conn, userstate_conn, id_maps):
        reqs = monster_repo.fetch_all_requirements(content_conn)
        mid = id_maps["monsters"]["Zynth"]
        cmd = AddTargetCommand(mid, content_conn, userstate_conn, reqs)
        cmd.execute()
        cmd.undo()

        assert target_repo.fetch_all_targets(userstate_conn) == []
        assert target_repo.fetch_all_progress(userstate_conn) == []

    def test_duplicate_targets_allowed(self, content_conn, userstate_conn, id_maps):
        reqs = monster_repo.fetch_all_requirements(content_conn)
        mid = id_maps["monsters"]["Dwumrohl"]
        cmd1 = AddTargetCommand(mid, content_conn, userstate_conn, reqs)
        cmd2 = AddTargetCommand(mid, content_conn, userstate_conn, reqs)
        cmd1.execute()
        cmd2.execute()

        targets = target_repo.fetch_all_targets(userstate_conn)
        assert len(targets) == 2

        progress = target_repo.fetch_all_progress(userstate_conn)
        # 4 egg types * 2 targets = 8 rows
        assert len(progress) == 8

    def test_reintroduced_egg_starts_fresh(self, content_conn, userstate_conn, id_maps):
        """FR-410: after completion, a new target requiring the same egg starts at bred=0."""
        reqs = monster_repo.fetch_all_requirements(content_conn)
        mid = id_maps["monsters"]["Dwumrohl"]

        cmd1 = AddTargetCommand(mid, content_conn, userstate_conn, reqs)
        cmd1.execute()

        # Satisfy all Mammott for target 1
        mammott_id = id_maps["eggs"]["Mammott"]
        rows = target_repo.fetch_progress_for_egg(userstate_conn, mammott_id)
        for r in rows:
            target_repo.set_progress(
                userstate_conn, r.active_target_id, mammott_id, r.required_count
            )
            userstate_conn.commit()

        # Close out the target
        target = target_repo.fetch_all_targets(userstate_conn)[0]
        close_cmd = CloseOutTargetCommand(target.id, userstate_conn)
        close_cmd.execute()

        # Add a new target that also needs Mammott
        cmd2 = AddTargetCommand(id_maps["monsters"]["Galvana"], content_conn, userstate_conn, reqs)
        cmd2.execute()

        # Mammott progress for new target should be 0
        new_rows = target_repo.fetch_progress_for_egg(userstate_conn, mammott_id)
        for r in new_rows:
            assert r.satisfied_count == 0


class TestCloseOutTargetCommand:
    def test_execute_removes_target_and_progress(self, content_conn, userstate_conn, id_maps):
        reqs = monster_repo.fetch_all_requirements(content_conn)
        mid = id_maps["monsters"]["Zynth"]
        add_cmd = AddTargetCommand(mid, content_conn, userstate_conn, reqs)
        add_cmd.execute()

        target = target_repo.fetch_all_targets(userstate_conn)[0]
        close_cmd = CloseOutTargetCommand(target.id, userstate_conn)
        close_cmd.execute()

        assert target_repo.fetch_all_targets(userstate_conn) == []
        assert target_repo.fetch_all_progress(userstate_conn) == []

    def test_undo_restores_target_and_progress(self, content_conn, userstate_conn, id_maps):
        reqs = monster_repo.fetch_all_requirements(content_conn)
        mid = id_maps["monsters"]["Galvana"]
        add_cmd = AddTargetCommand(mid, content_conn, userstate_conn, reqs)
        add_cmd.execute()

        # Increment some progress
        mammott_id = id_maps["eggs"]["Mammott"]
        inc_cmd = IncrementEggCommand(mammott_id, userstate_conn)
        inc_cmd.execute()

        target = target_repo.fetch_all_targets(userstate_conn)[0]
        close_cmd = CloseOutTargetCommand(target.id, userstate_conn)
        close_cmd.execute()

        # Undo the close-out
        close_cmd.undo()

        targets = target_repo.fetch_all_targets(userstate_conn)
        assert len(targets) == 1
        assert targets[0].monster_id == mid
        assert targets[0].monster_key == "monster:celestial:galvana"

        # Progress should be restored including the increment
        mammott_rows = target_repo.fetch_progress_for_egg(userstate_conn, mammott_id)
        assert any(r.satisfied_count == 1 for r in mammott_rows)
        assert all(r.egg_key for r in mammott_rows)

    def test_close_out_does_not_affect_other_targets(self, content_conn, userstate_conn, id_maps):
        reqs = monster_repo.fetch_all_requirements(content_conn)
        # Add Dwumrohl and Galvana — both need Mammott
        add1 = AddTargetCommand(id_maps["monsters"]["Dwumrohl"], content_conn, userstate_conn, reqs)
        add2 = AddTargetCommand(id_maps["monsters"]["Galvana"], content_conn, userstate_conn, reqs)
        add1.execute()
        add2.execute()

        # Increment Mammott once (goes to Dwumrohl, oldest)
        mammott_id = id_maps["eggs"]["Mammott"]
        inc = IncrementEggCommand(mammott_id, userstate_conn)
        inc.execute()

        # Close out Galvana
        targets = target_repo.fetch_all_targets(userstate_conn)
        galvana_target = next(t for t in targets if t.monster_id == id_maps["monsters"]["Galvana"])
        close_cmd = CloseOutTargetCommand(galvana_target.id, userstate_conn)
        close_cmd.execute()

        # Dwumrohl's Mammott progress should be preserved
        remaining_progress = target_repo.fetch_progress_for_egg(userstate_conn, mammott_id)
        assert len(remaining_progress) == 1
        assert remaining_progress[0].satisfied_count == 1


class TestIncrementEggCommand:
    def test_basic_increment(self, content_conn, userstate_conn, id_maps):
        reqs = monster_repo.fetch_all_requirements(content_conn)
        mid = id_maps["monsters"]["Dwumrohl"]
        add_cmd = AddTargetCommand(mid, content_conn, userstate_conn, reqs)
        add_cmd.execute()

        mammott_id = id_maps["eggs"]["Mammott"]
        cmd = IncrementEggCommand(mammott_id, userstate_conn)
        cmd.execute()

        rows = target_repo.fetch_progress_for_egg(userstate_conn, mammott_id)
        total_satisfied = sum(r.satisfied_count for r in rows)
        assert total_satisfied == 1

    def test_oldest_target_first_allocation(self, content_conn, userstate_conn, id_maps):
        """Allocation rule: oldest unsatisfied target gets the egg."""
        reqs = monster_repo.fetch_all_requirements(content_conn)
        # Add Dwumrohl first (needs 2 Mammott), then Galvana (needs 4 Mammott)
        add1 = AddTargetCommand(id_maps["monsters"]["Dwumrohl"], content_conn, userstate_conn, reqs)
        add2 = AddTargetCommand(id_maps["monsters"]["Galvana"], content_conn, userstate_conn, reqs)
        add1.execute()
        add2.execute()

        mammott_id = id_maps["eggs"]["Mammott"]
        # First two increments should go to Dwumrohl
        for _ in range(2):
            IncrementEggCommand(mammott_id, userstate_conn).execute()

        rows = target_repo.fetch_progress_for_egg(userstate_conn, mammott_id)
        targets = target_repo.fetch_all_targets(userstate_conn)
        dwumrohl_target = next(t for t in targets if t.monster_id == id_maps["monsters"]["Dwumrohl"])
        galvana_target = next(t for t in targets if t.monster_id == id_maps["monsters"]["Galvana"])

        dwum_row = next(r for r in rows if r.active_target_id == dwumrohl_target.id)
        galv_row = next(r for r in rows if r.active_target_id == galvana_target.id)
        assert dwum_row.satisfied_count == 2  # fully satisfied for Dwumrohl
        assert galv_row.satisfied_count == 0  # not yet

        # Third increment should go to Galvana
        IncrementEggCommand(mammott_id, userstate_conn).execute()
        rows2 = target_repo.fetch_progress_for_egg(userstate_conn, mammott_id)
        galv_row2 = next(r for r in rows2 if r.active_target_id == galvana_target.id)
        assert galv_row2.satisfied_count == 1

    def test_completion_detection(self, content_conn, userstate_conn, id_maps):
        reqs = monster_repo.fetch_all_requirements(content_conn)
        add_cmd = AddTargetCommand(id_maps["monsters"]["Zynth"], content_conn, userstate_conn, reqs)
        add_cmd.execute()

        bowgart_id = id_maps["eggs"]["Bowgart"]
        cmd = IncrementEggCommand(bowgart_id, userstate_conn)
        cmd.execute()
        assert cmd.was_completion is True
        assert cmd.completed_egg_type_id == bowgart_id

    def test_no_over_increment(self, content_conn, userstate_conn, id_maps):
        reqs = monster_repo.fetch_all_requirements(content_conn)
        add_cmd = AddTargetCommand(id_maps["monsters"]["Zynth"], content_conn, userstate_conn, reqs)
        add_cmd.execute()

        bowgart_id = id_maps["eggs"]["Bowgart"]
        IncrementEggCommand(bowgart_id, userstate_conn).execute()

        with pytest.raises(RuntimeError, match="No unsatisfied target"):
            IncrementEggCommand(bowgart_id, userstate_conn).execute()

    def test_undo_restores_prior_count(self, content_conn, userstate_conn, id_maps):
        reqs = monster_repo.fetch_all_requirements(content_conn)
        add_cmd = AddTargetCommand(id_maps["monsters"]["Dwumrohl"], content_conn, userstate_conn, reqs)
        add_cmd.execute()

        mammott_id = id_maps["eggs"]["Mammott"]
        cmd = IncrementEggCommand(mammott_id, userstate_conn)
        cmd.execute()
        cmd.undo()

        rows = target_repo.fetch_progress_for_egg(userstate_conn, mammott_id)
        assert all(r.satisfied_count == 0 for r in rows)

    def test_undo_completion_restores_row(self, content_conn, userstate_conn, id_maps):
        """FR-506: undo of a completion restores the row to bred = total - 1."""
        reqs = monster_repo.fetch_all_requirements(content_conn)
        add_cmd = AddTargetCommand(id_maps["monsters"]["Zynth"], content_conn, userstate_conn, reqs)
        add_cmd.execute()

        bowgart_id = id_maps["eggs"]["Bowgart"]
        cmd = IncrementEggCommand(bowgart_id, userstate_conn)
        cmd.execute()
        assert cmd.was_completion is True

        cmd.undo()

        rows = target_repo.fetch_progress_for_egg(userstate_conn, bowgart_id)
        assert len(rows) == 1
        assert rows[0].satisfied_count == 0
        assert rows[0].required_count == 1
