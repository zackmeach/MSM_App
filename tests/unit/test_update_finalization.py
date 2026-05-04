"""Tests for the content update finalization flow.

Covers:
- Successful finalize produces a new connection to the updated DB
- Rollback restores the prior DB and returns a working connection
- AppService rebind picks up new content version and requirements
- Post-update reconciliation clips over-satisfied progress
"""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from app.bootstrap import open_content_db
from app.domain.models import egg_content_key, monster_content_key
from app.db.migrations import run_migrations
from app.domain.reconciliation import reconcile
from app.repositories import monster_repo, target_repo
from app.services.app_service import AppService
from app.ui.main_window import MainWindow
from app.services.viewmodels import SettingsUpdateState
from app.updater.update_service import UpdateService, _remove_wal_sidecars


def _make_content_db(path: Path, version: str = "1.0.0") -> None:
    """Create a valid content DB at the given path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
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
    conn.execute(f"UPDATE update_metadata SET value='{version}' WHERE key='content_version'")
    conn.execute("UPDATE update_metadata SET value='2026-01-01T00:00:00Z' WHERE key='last_updated_utc'")
    conn.execute("UPDATE update_metadata SET value='test' WHERE key='source'")
    conn.commit()
    conn.close()


def _make_updated_content_db(path: Path, version: str = "2.0.0") -> None:
    """Create an updated content DB with changed requirements."""
    _make_content_db(path, version)
    conn = sqlite3.connect(str(path))
    egg_id = conn.execute("SELECT id FROM egg_types WHERE name='Mammott'").fetchone()[0]
    mon_id = conn.execute("SELECT id FROM monsters WHERE name='Zynth'").fetchone()[0]
    conn.execute(
        "UPDATE monster_requirements SET quantity = 2 WHERE monster_id = ? AND egg_type_id = ?",
        (mon_id, egg_id),
    )
    conn.commit()
    conn.close()


class TestFinalizeUpdate:
    """Verify finalize_update replaces the DB and returns a new connection."""

    def test_finalize_returns_new_connection_with_new_version(self, tmp_path):
        data_dir = tmp_path / "appdata"
        data_dir.mkdir()

        _make_content_db(data_dir / "content.db", "1.0.0")
        _make_updated_content_db(data_dir / "content_staging.db", "2.0.0")

        conn_old = open_content_db(data_dir / "content.db")
        updater = UpdateService(data_dir, conn_old)

        new_conn = updater.finalize_update(conn_old)

        row = new_conn.execute(
            "SELECT value FROM update_metadata WHERE key='content_version'"
        ).fetchone()
        assert row[0] == "2.0.0"
        new_conn.close()

    def test_finalize_creates_backup(self, tmp_path):
        data_dir = tmp_path / "appdata"
        data_dir.mkdir()

        _make_content_db(data_dir / "content.db", "1.0.0")
        _make_updated_content_db(data_dir / "content_staging.db", "2.0.0")

        conn_old = open_content_db(data_dir / "content.db")
        updater = UpdateService(data_dir, conn_old)
        new_conn = updater.finalize_update(conn_old)
        new_conn.close()

        assert (data_dir / "content_backup.db").exists()

    def test_staging_file_consumed(self, tmp_path):
        data_dir = tmp_path / "appdata"
        data_dir.mkdir()

        _make_content_db(data_dir / "content.db", "1.0.0")
        _make_updated_content_db(data_dir / "content_staging.db", "2.0.0")

        conn_old = open_content_db(data_dir / "content.db")
        updater = UpdateService(data_dir, conn_old)
        new_conn = updater.finalize_update(conn_old)
        new_conn.close()

        assert not (data_dir / "content_staging.db").exists()


class TestRollbackUpdate:
    """Verify rollback restores the prior DB version."""

    def test_rollback_restores_prior_version(self, tmp_path):
        data_dir = tmp_path / "appdata"
        data_dir.mkdir()

        _make_content_db(data_dir / "content.db", "1.0.0")
        _make_updated_content_db(data_dir / "content_staging.db", "2.0.0")

        conn_old = open_content_db(data_dir / "content.db")
        updater = UpdateService(data_dir, conn_old)
        new_conn = updater.finalize_update(conn_old)
        new_conn.close()

        restored = updater.rollback_update()
        assert restored is not None
        row = restored.execute(
            "SELECT value FROM update_metadata WHERE key='content_version'"
        ).fetchone()
        assert row[0] == "1.0.0"
        restored.close()

    def test_rollback_returns_none_without_backup(self, tmp_path):
        data_dir = tmp_path / "appdata"
        data_dir.mkdir()
        _make_content_db(data_dir / "content.db", "1.0.0")

        conn = open_content_db(data_dir / "content.db")
        updater = UpdateService(data_dir, conn)
        conn.close()

        result = updater.rollback_update()
        assert result is None


class TestAppServiceRebind:
    """Verify AppService picks up new content after rebind."""

    def test_rebind_refreshes_version_and_requirements(self, tmp_path):
        data_dir = tmp_path / "appdata"
        data_dir.mkdir()

        _make_content_db(data_dir / "content.db", "1.0.0")
        conn_content = open_content_db(data_dir / "content.db")

        us_path = data_dir / "userstate.db"
        conn_us = sqlite3.connect(str(us_path))
        conn_us.execute("PRAGMA foreign_keys=ON")
        run_migrations(conn_us, "userstate")

        svc = AppService(conn_content, conn_us)

        vm_before = svc.get_settings_viewmodel()
        assert vm_before.content_version == "1.0.0"

        _make_updated_content_db(data_dir / "content_v2.db", "2.0.0")
        conn_v2 = open_content_db(data_dir / "content_v2.db")

        svc.rebind_content(conn_v2)

        vm_after = svc.get_settings_viewmodel()
        assert vm_after.content_version == "2.0.0"

        mon_id = conn_v2.execute("SELECT id FROM monsters WHERE name='Zynth'").fetchone()[0]
        reqs = svc._requirements_cache.get(mon_id, [])
        assert len(reqs) > 0
        assert reqs[0].quantity == 2

        conn_content.close()
        conn_v2.close()
        conn_us.close()


class TestPostUpdateReconciliation:
    """Verify reconciliation clips progress after content requirements shrink."""

    def test_clip_over_satisfied_progress(self, tmp_path):
        """Simulate a content update where required_count drops below
        satisfied_count, then verify reconcile() detects and clips it."""
        data_dir = tmp_path / "appdata"
        data_dir.mkdir()

        _make_content_db(data_dir / "content.db", "1.0.0")
        conn_content = open_content_db(data_dir / "content.db")

        us_path = data_dir / "userstate.db"
        conn_us = sqlite3.connect(str(us_path))
        conn_us.execute("PRAGMA foreign_keys=ON")
        run_migrations(conn_us, "userstate")

        mon_id = conn_content.execute("SELECT id FROM monsters WHERE name='Zynth'").fetchone()[0]
        egg_id = conn_content.execute("SELECT id FROM egg_types WHERE name='Mammott'").fetchone()[0]

        from app.commands.add_target import AddTargetCommand

        reqs = monster_repo.fetch_all_requirements(conn_content)
        add_cmd = AddTargetCommand(mon_id, conn_content, conn_us, reqs)
        add_cmd.execute()

        target = target_repo.fetch_all_targets(conn_us)[0]
        target_repo.set_progress(conn_us, target.id, egg_id, 3)
        conn_us.commit()

        conn_us.execute(
            "UPDATE target_requirement_progress SET required_count = 2 "
            "WHERE active_target_id = ? AND egg_type_id = ?",
            (target.id, egg_id),
        )
        conn_us.commit()

        progress = target_repo.fetch_all_progress(conn_us)
        clips = reconcile(progress)
        assert len(clips) == 1
        assert clips[0] == (target.id, egg_id, 2)

        for tid, eid, clipped in clips:
            target_repo.set_progress(conn_us, tid, eid, clipped)
        conn_us.commit()

        updated_progress = target_repo.fetch_progress_for_egg(conn_us, egg_id)
        assert updated_progress[0].satisfied_count == 2

        conn_content.close()
        conn_us.close()

    def test_reconciliation_uses_stable_keys_and_updates_requirements(self, qtbot, tmp_path):
        data_dir = tmp_path / "appdata"
        bundle_dir = tmp_path / "bundle"
        data_dir.mkdir()
        bundle_dir.mkdir()

        _make_content_db(data_dir / "content.db", "1.0.0")
        conn_content = open_content_db(data_dir / "content.db")

        us_path = data_dir / "userstate.db"
        conn_us = sqlite3.connect(str(us_path))
        conn_us.execute("PRAGMA foreign_keys=ON")
        run_migrations(conn_us, "userstate")

        svc = AppService(conn_content, conn_us)
        zynth_id = conn_content.execute(
            "SELECT id FROM monsters WHERE name='Zynth'"
        ).fetchone()[0]
        mammott_id = conn_content.execute(
            "SELECT id FROM egg_types WHERE name='Mammott'"
        ).fetchone()[0]
        svc.handle_add_target(zynth_id)

        target = target_repo.fetch_all_targets(conn_us)[0]
        target_repo.set_progress(conn_us, target.id, mammott_id, 3)
        conn_us.commit()

        updated_path = data_dir / "content_v2.db"
        conn_v2 = sqlite3.connect(str(updated_path))
        conn_v2.execute("PRAGMA foreign_keys=ON")
        run_migrations(conn_v2, "content")
        conn_v2.execute(
            "INSERT INTO egg_types("
            "name, breeding_time_seconds, breeding_time_display, egg_image_path, content_key"
            ") VALUES('Noggin', 5, '5s', 'images/eggs/noggin_egg.png', ?)",
            (egg_content_key("Noggin"),),
        )
        conn_v2.execute(
            "INSERT INTO egg_types("
            "name, breeding_time_seconds, breeding_time_display, egg_image_path, content_key"
            ") VALUES('Mammott', 5, '5s', 'images/eggs/mammott_egg.png', ?)",
            (egg_content_key("Mammott"),),
        )
        conn_v2.execute(
            "INSERT INTO monsters(name, monster_type, image_path, wiki_slug, content_key) "
            "VALUES('Zynth', 'wublin', 'images/monsters/zynth.png', 'Zynth', ?)",
            (monster_content_key("wublin", "Zynth"),),
        )
        new_mammott_id = conn_v2.execute(
            "SELECT id FROM egg_types WHERE name='Mammott'"
        ).fetchone()[0]
        new_zynth_id = conn_v2.execute(
            "SELECT id FROM monsters WHERE name='Zynth'"
        ).fetchone()[0]
        conn_v2.execute(
            "INSERT INTO monster_requirements(monster_id, egg_type_id, quantity) VALUES(?, ?, 2)",
            (new_zynth_id, new_mammott_id),
        )
        conn_v2.execute("UPDATE update_metadata SET value='2.0.0' WHERE key='content_version'")
        conn_v2.execute(
            "UPDATE update_metadata SET value='2026-01-01T00:00:00Z' WHERE key='last_updated_utc'"
        )
        conn_v2.execute("UPDATE update_metadata SET value='test' WHERE key='source'")
        conn_v2.commit()

        from app.bootstrap import AppContext

        window = MainWindow(
            AppContext(
                data_dir=data_dir,
                bundle_dir=bundle_dir,
                conn_content=conn_content,
                conn_userstate=conn_us,
            )
        )
        qtbot.addWidget(window)

        # Reconciliation now lives on AppService; rebind first so caches use the new content DB.
        window._service.rebind_content(conn_v2)
        window._service.reconcile_after_content_update()

        updated_target = target_repo.fetch_all_targets(conn_us)[0]
        assert updated_target.monster_id == new_zynth_id
        assert updated_target.monster_key == "monster:wublin:zynth"

        updated_rows = target_repo.fetch_progress_for_target(conn_us, updated_target.id)
        assert len(updated_rows) == 1
        assert updated_rows[0].egg_type_id == new_mammott_id
        assert updated_rows[0].egg_key == "egg:mammott"
        assert updated_rows[0].required_count == 2
        assert updated_rows[0].satisfied_count == 2

        window.close()
        conn_v2.close()
        conn_content.close()
        conn_us.close()


class TestRemoveWalSidecars:
    """Verify WAL/SHM sidecar cleanup."""

    def test_removes_existing_sidecars(self, tmp_path):
        db = tmp_path / "test.db"
        db.write_bytes(b"db")
        (tmp_path / "test.db-wal").write_bytes(b"wal")
        (tmp_path / "test.db-shm").write_bytes(b"shm")

        _remove_wal_sidecars(db)

        assert not (tmp_path / "test.db-wal").exists()
        assert not (tmp_path / "test.db-shm").exists()
        assert db.exists()

    def test_no_error_when_sidecars_missing(self, tmp_path):
        db = tmp_path / "test.db"
        db.write_bytes(b"db")
        _remove_wal_sidecars(db)
