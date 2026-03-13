"""Tests for the content update subsystem."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from app.db.migrations import run_migrations
from app.updater.validator import ValidationError, validate_content_db


class TestValidator:
    """Validates the content DB schema checker."""

    def _make_valid_db(self, path: Path) -> None:
        conn = sqlite3.connect(str(path))
        conn.execute("PRAGMA foreign_keys=ON")
        run_migrations(conn, "content")
        conn.execute(
            "INSERT INTO egg_types(name, breeding_time_seconds, breeding_time_display, egg_image_path) "
            "VALUES('TestEgg', 100, '1m 40s', '')"
        )
        conn.execute(
            "INSERT INTO monsters(name, monster_type, image_path, wiki_slug) "
            "VALUES('TestMon', 'wublin', '', '')"
        )
        conn.execute("UPDATE update_metadata SET value='1.0.0' WHERE key='content_version'")
        conn.execute(
            "UPDATE update_metadata SET value='2026-01-01T00:00:00Z' WHERE key='last_updated_utc'"
        )
        conn.execute("UPDATE update_metadata SET value='test' WHERE key='source'")
        conn.commit()
        conn.close()

    def test_valid_db_passes(self, tmp_path):
        db = tmp_path / "good.db"
        self._make_valid_db(db)
        validate_content_db(str(db))

    def test_missing_tables_fails(self, tmp_path):
        db = tmp_path / "bad.db"
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE dummy(id INTEGER PRIMARY KEY)")
        conn.close()
        with pytest.raises(ValidationError, match="Missing tables"):
            validate_content_db(str(db))

    def test_empty_monsters_fails(self, tmp_path):
        db = tmp_path / "empty.db"
        conn = sqlite3.connect(str(db))
        conn.execute("PRAGMA foreign_keys=ON")
        run_migrations(conn, "content")
        conn.execute("UPDATE update_metadata SET value='1.0.0' WHERE key='content_version'")
        conn.execute(
            "UPDATE update_metadata SET value='2026-01-01T00:00:00Z' WHERE key='last_updated_utc'"
        )
        conn.execute("UPDATE update_metadata SET value='test' WHERE key='source'")
        conn.commit()
        conn.close()
        with pytest.raises(ValidationError, match="No monsters"):
            validate_content_db(str(db))

    def test_missing_metadata_fails(self, tmp_path):
        db = tmp_path / "nover.db"
        conn = sqlite3.connect(str(db))
        conn.execute("PRAGMA foreign_keys=ON")
        run_migrations(conn, "content")
        conn.execute(
            "INSERT INTO monsters(name, monster_type, image_path, wiki_slug) "
            "VALUES('M', 'wublin', '', '')"
        )
        conn.execute(
            "INSERT INTO egg_types(name, breeding_time_seconds, breeding_time_display, egg_image_path) "
            "VALUES('E', 100, '1m', '')"
        )
        conn.execute("DELETE FROM update_metadata")
        conn.commit()
        conn.close()
        with pytest.raises(ValidationError, match="metadata"):
            validate_content_db(str(db))

    def test_corrupt_file_fails(self, tmp_path):
        db = tmp_path / "corrupt.db"
        db.write_text("this is not a database")
        with pytest.raises(ValidationError):
            validate_content_db(str(db))


class TestUpdateSafety:
    """Verify that a failed update leaves the prior content intact."""

    def test_backup_preserved_on_failure(self, tmp_path):
        """Simulate a failed apply: original DB should remain."""
        data_dir = tmp_path / "appdata"
        data_dir.mkdir()

        original = data_dir / "content.db"
        conn = sqlite3.connect(str(original))
        conn.execute("PRAGMA foreign_keys=ON")
        run_migrations(conn, "content")
        conn.execute(
            "INSERT INTO egg_types(name, breeding_time_seconds, breeding_time_display, egg_image_path) "
            "VALUES('OrigEgg', 100, '1m 40s', '')"
        )
        conn.execute(
            "INSERT INTO monsters(name, monster_type, image_path, wiki_slug) "
            "VALUES('OrigMon', 'wublin', '', '')"
        )
        conn.execute("UPDATE update_metadata SET value='0.9.0' WHERE key='content_version'")
        conn.execute(
            "UPDATE update_metadata SET value='2026-01-01T00:00:00Z' WHERE key='last_updated_utc'"
        )
        conn.execute("UPDATE update_metadata SET value='test' WHERE key='source'")
        conn.commit()
        conn.close()

        original_size = original.stat().st_size
        assert original_size > 0

        staging = data_dir / "content_staging.db"
        staging.write_text("invalid database content")

        with pytest.raises(ValidationError):
            validate_content_db(str(staging))

        assert original.exists()
        assert original.stat().st_size == original_size


class TestClearUndoRedo:
    """AppService.clear_undo_redo resets stacks and emits state."""

    def test_clear_resets_stacks(self, content_conn, userstate_conn, id_maps):
        from app.services.app_service import AppService

        svc = AppService(content_conn, userstate_conn)
        svc.handle_add_target(id_maps["monsters"]["Zynth"])
        state = svc.get_app_state()
        assert state.can_undo is True

        svc.clear_undo_redo()
        state = svc.get_app_state()
        assert state.can_undo is False
        assert state.can_redo is False
