"""Tests for the atomicity of AppService.reconcile_after_content_update.

The reconciliation pass touches multiple userstate.db rows across multiple
targets. If any write fails mid-pass the previous writes must roll back so
userstate.db is never left half-reconciled.

These tests exercise the explicit transaction discipline by switching the
userstate connection to autocommit mode (``isolation_level = None``). In
autocommit mode Python's ``with conn:`` block becomes a no-op, so the
implementation must own its own ``BEGIN``/``COMMIT``/``ROLLBACK`` (the
canonical ``transaction(conn)`` helper from ``app/db/connection.py``).
This exposes the bug described in W0.7 of the improvement plan.
"""

from __future__ import annotations

import sqlite3

import pytest

from app.bootstrap import open_content_db
from app.db.migrations import run_migrations
from app.domain.models import egg_content_key, monster_content_key
from app.repositories import settings_repo, target_repo
from app.services.app_service import AppService


# ── Fixture builders ────────────────────────────────────────────────


def _seed_content_db(path, *, version: str = "1.0.0") -> None:
    """Build a minimal content DB with one Wublin (Zynth) needing 3 Mammott eggs."""
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys=ON")
    run_migrations(conn, "content")
    conn.execute(
        "INSERT INTO egg_types("
        "name, breeding_time_seconds, breeding_time_display, egg_image_path, content_key"
        ") VALUES('Mammott', 5, '5s', 'images/eggs/mammott_egg.png', ?)",
        (egg_content_key("Mammott"),),
    )
    conn.execute(
        "INSERT INTO egg_types("
        "name, breeding_time_seconds, breeding_time_display, egg_image_path, content_key"
        ") VALUES('Noggin', 5, '5s', 'images/eggs/noggin_egg.png', ?)",
        (egg_content_key("Noggin"),),
    )
    conn.execute(
        "INSERT INTO monsters(name, monster_type, image_path, wiki_slug, content_key) "
        "VALUES('Zynth', 'wublin', 'images/monsters/zynth.png', 'Zynth', ?)",
        (monster_content_key("wublin", "Zynth"),),
    )
    egg_id = conn.execute("SELECT id FROM egg_types WHERE name='Mammott'").fetchone()[0]
    mon_id = conn.execute("SELECT id FROM monsters WHERE name='Zynth'").fetchone()[0]
    conn.execute(
        "INSERT INTO monster_requirements(monster_id, egg_type_id, quantity) VALUES(?, ?, 3)",
        (mon_id, egg_id),
    )
    conn.execute(
        f"UPDATE update_metadata SET value='{version}' WHERE key='content_version'"
    )
    conn.execute(
        "UPDATE update_metadata SET value='2026-01-01T00:00:00Z' WHERE key='last_updated_utc'"
    )
    conn.execute("UPDATE update_metadata SET value='test' WHERE key='source'")
    conn.commit()
    conn.close()


def _seed_v2_content_db(path, *, version: str = "2.0.0") -> None:
    """Build a v2 content DB whose monster/egg numeric ids will differ from v1.

    Forces the reconcile loop into the identity-rebind code path that performs
    multiple writes per target.
    """
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys=ON")
    run_migrations(conn, "content")
    # Insert in reverse order so Mammott gets a different numeric id than v1.
    conn.execute(
        "INSERT INTO egg_types("
        "name, breeding_time_seconds, breeding_time_display, egg_image_path, content_key"
        ") VALUES('Noggin', 5, '5s', 'images/eggs/noggin_egg.png', ?)",
        (egg_content_key("Noggin"),),
    )
    conn.execute(
        "INSERT INTO egg_types("
        "name, breeding_time_seconds, breeding_time_display, egg_image_path, content_key"
        ") VALUES('Mammott', 5, '5s', 'images/eggs/mammott_egg.png', ?)",
        (egg_content_key("Mammott"),),
    )
    # Insert a filler monster first so Zynth gets a higher numeric id than v1.
    conn.execute(
        "INSERT INTO monsters(name, monster_type, image_path, wiki_slug, content_key) "
        "VALUES('Filler', 'wublin', 'images/monsters/filler.png', 'Filler', ?)",
        (monster_content_key("wublin", "Filler"),),
    )
    conn.execute(
        "INSERT INTO monsters(name, monster_type, image_path, wiki_slug, content_key) "
        "VALUES('Zynth', 'wublin', 'images/monsters/zynth.png', 'Zynth', ?)",
        (monster_content_key("wublin", "Zynth"),),
    )
    new_egg_id = conn.execute(
        "SELECT id FROM egg_types WHERE name='Mammott'"
    ).fetchone()[0]
    new_mon_id = conn.execute(
        "SELECT id FROM monsters WHERE name='Zynth'"
    ).fetchone()[0]
    # Quantity drops 3 -> 2 to also exercise the clip branch.
    conn.execute(
        "INSERT INTO monster_requirements(monster_id, egg_type_id, quantity) VALUES(?, ?, 2)",
        (new_mon_id, new_egg_id),
    )
    conn.execute(
        f"UPDATE update_metadata SET value='{version}' WHERE key='content_version'"
    )
    conn.execute(
        "UPDATE update_metadata SET value='2026-02-01T00:00:00Z' WHERE key='last_updated_utc'"
    )
    conn.execute("UPDATE update_metadata SET value='test' WHERE key='source'")
    conn.commit()
    conn.close()


def _make_userstate(path):
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys=ON")
    run_migrations(conn, "userstate")
    return conn


def _snapshot_userstate(conn: sqlite3.Connection) -> dict:
    """Return a structural snapshot for change detection."""
    targets = sorted(
        conn.execute(
            "SELECT id, monster_id, monster_key FROM active_targets ORDER BY id"
        ).fetchall()
    )
    progress = sorted(
        conn.execute(
            "SELECT active_target_id, egg_type_id, required_count, "
            "satisfied_count, egg_key FROM target_requirement_progress "
            "ORDER BY active_target_id, egg_type_id"
        ).fetchall()
    )
    last_reconciled = settings_repo.get(conn, "last_reconciled_content_version", "")
    return {
        "active_targets": targets,
        "target_requirement_progress": progress,
        "last_reconciled_content_version": last_reconciled,
    }


# ── Tests ────────────────────────────────────────────────────────────


class TestReconcileAtomicity:
    """Verify reconcile_after_content_update is a single all-or-nothing transaction."""

    def test_failure_mid_pass_leaves_userstate_unchanged(
        self, qtbot, tmp_path, monkeypatch
    ):
        """If any repo call raises during reconciliation, every prior write
        in the same call must be rolled back; userstate.db must match its
        pre-call snapshot exactly."""
        from app.commands.add_target import AddTargetCommand
        from app.repositories import monster_repo

        data_dir = tmp_path / "appdata"
        data_dir.mkdir()
        _seed_content_db(data_dir / "content.db", version="1.0.0")
        conn_content = open_content_db(data_dir / "content.db")
        conn_us = _make_userstate(data_dir / "userstate.db")

        reqs = monster_repo.fetch_all_requirements(conn_content)
        zynth_v1 = conn_content.execute(
            "SELECT id FROM monsters WHERE name='Zynth'"
        ).fetchone()[0]
        mammott_v1 = conn_content.execute(
            "SELECT id FROM egg_types WHERE name='Mammott'"
        ).fetchone()[0]

        # Add two targets so reconciliation has two iterations.
        AddTargetCommand(zynth_v1, conn_content, conn_us, reqs).execute()
        AddTargetCommand(zynth_v1, conn_content, conn_us, reqs).execute()
        targets = target_repo.fetch_all_targets(conn_us)
        assert len(targets) == 2

        # Give each target some progress so a rollback is detectable.
        for t in targets:
            target_repo.set_progress(conn_us, t.id, mammott_v1, 1)
        conn_us.commit()

        pre_snapshot = _snapshot_userstate(conn_us)

        # Now rebind the service to a v2 content DB whose numeric ids differ,
        # so reconciliation walks the identity-rebind branch.
        _seed_v2_content_db(data_dir / "content_v2.db", version="2.0.0")
        conn_v2 = open_content_db(data_dir / "content_v2.db")

        # Switch the userstate connection to autocommit mode. This is the mode
        # under which Python's implicit ``with conn:`` rollback no longer
        # protects us — each statement commits as it runs unless the caller
        # owns ``BEGIN``/``COMMIT``/``ROLLBACK``. The W0.7 fix must work here.
        conn_us.commit()
        conn_us.isolation_level = None

        svc = AppService(conn_content, conn_us)
        svc.rebind_content(conn_v2)

        # Force the second loop iteration to fail. update_target_identity is
        # called once per target in this scenario.
        call_count = {"n": 0}
        original_update = target_repo.update_target_identity

        def flaky_update_target_identity(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] >= 2:
                raise RuntimeError("simulated mid-reconcile failure")
            return original_update(*args, **kwargs)

        monkeypatch.setattr(
            target_repo, "update_target_identity", flaky_update_target_identity
        )
        # AppService imports the symbol via `from app.repositories import target_repo`
        # so patching the module attribute is sufficient.

        with pytest.raises(RuntimeError, match="simulated mid-reconcile failure"):
            svc.reconcile_after_content_update()

        post_snapshot = _snapshot_userstate(conn_us)

        assert post_snapshot["active_targets"] == pre_snapshot["active_targets"], (
            "active_targets table mutated despite mid-pass failure"
        )
        assert (
            post_snapshot["target_requirement_progress"]
            == pre_snapshot["target_requirement_progress"]
        ), "target_requirement_progress mutated despite mid-pass failure"
        assert (
            post_snapshot["last_reconciled_content_version"]
            == pre_snapshot["last_reconciled_content_version"]
        ), "last_reconciled_content_version advanced despite mid-pass failure"

        conn_v2.close()
        conn_content.close()
        conn_us.close()
