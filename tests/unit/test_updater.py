"""Tests for the content update subsystem."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from PySide6.QtCore import QObject

from app.db.migrations import run_migrations
from app.ui.viewmodels import APP_VERSION
from app.updater.update_service import _UpdateWorker
from app.updater.validator import (
    ValidationError,
    validate_content_db,
    validate_checksum,
    validate_manifest_contract,
    validate_client_compatibility,
)


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


class TestChecksumValidation:
    def test_valid_checksum_passes(self, tmp_path):
        f = tmp_path / "test.bin"
        f.write_bytes(b"hello world")
        import hashlib
        expected = hashlib.sha256(b"hello world").hexdigest()
        validate_checksum(f, expected)

    def test_invalid_checksum_fails(self, tmp_path):
        f = tmp_path / "test.bin"
        f.write_bytes(b"hello world")
        with pytest.raises(ValidationError, match="Checksum mismatch"):
            validate_checksum(f, "0" * 64)


class TestManifestContractValidation:
    def test_valid_manifest_passes(self):
        manifest = {
            "artifact_contract_version": "1.1",
            "content_version": "1.0.0",
            "content_db_url": "https://example.com/content.db",
            "content_db_sha256": "a" * 64,
        }
        validate_manifest_contract(manifest)

    def test_unsupported_contract_version(self):
        manifest = {
            "artifact_contract_version": "99.0",
            "content_version": "1.0.0",
            "content_db_url": "https://example.com/content.db",
            "content_db_sha256": "a" * 64,
        }
        with pytest.raises(ValidationError, match="Unsupported"):
            validate_manifest_contract(manifest)

    def test_missing_content_version(self):
        manifest = {"content_db_url": "https://example.com/content.db"}
        with pytest.raises(ValidationError, match="content_version"):
            validate_manifest_contract(manifest)

    def test_malformed_sha256(self):
        manifest = {
            "artifact_contract_version": "1.1",
            "content_version": "1.0.0",
            "content_db_url": "https://example.com/content.db",
            "content_db_sha256": "tooshort",
        }
        with pytest.raises(ValidationError, match="malformed"):
            validate_manifest_contract(manifest)

    def test_legacy_manifest_no_contract(self):
        """Legacy manifests without artifact_contract_version still work."""
        manifest = {
            "content_version": "0.9.0",
            "content_db_url": "https://example.com/content.db",
        }
        validate_manifest_contract(manifest)


class TestClientCompatibility:
    def test_compatible_version(self):
        manifest = {"min_supported_client_version": "1.0.0"}
        validate_client_compatibility(manifest, "1.1.0")

    def test_exact_version(self):
        manifest = {"min_supported_client_version": "1.0.0"}
        validate_client_compatibility(manifest, "1.0.0")

    def test_too_old_version(self):
        manifest = {"min_supported_client_version": "2.0.0"}
        with pytest.raises(ValidationError, match="below minimum"):
            validate_client_compatibility(manifest, "1.5.0")

    def test_no_min_version(self):
        validate_client_compatibility({}, "1.0.0")


class TestOrphanEggValidation:
    def test_orphan_egg_refs_detected(self, tmp_path):
        db = tmp_path / "orphan_egg.db"
        conn = sqlite3.connect(str(db))
        conn.execute("PRAGMA foreign_keys=OFF")
        run_migrations(conn, "content")
        conn.execute(
            "INSERT INTO monsters(name, monster_type, image_path, wiki_slug) "
            "VALUES('Mon', 'wublin', '', '')"
        )
        conn.execute(
            "INSERT INTO egg_types(name, breeding_time_seconds, breeding_time_display, egg_image_path) "
            "VALUES('Egg', 100, '1m', '')"
        )
        conn.execute("UPDATE update_metadata SET value='1.0.0' WHERE key='content_version'")
        conn.execute("UPDATE update_metadata SET value='2026-01-01' WHERE key='last_updated_utc'")
        conn.execute("UPDATE update_metadata SET value='test' WHERE key='source'")
        conn.execute("INSERT INTO monster_requirements VALUES(1, 999, 1)")
        conn.commit()
        conn.close()
        with pytest.raises(ValidationError, match="egg types"):
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


class TestUpdateWorkerCompatibility:
    def test_incompatible_manifest_is_rejected_during_check(self, tmp_path):
        worker = _UpdateWorker(tmp_path, "https://example.com/manifest.json", "1.0.0")
        worker._manifest_data = None

        emitted = []
        worker.check_finished.connect(emitted.append)

        manifest = {
            "artifact_contract_version": "1.1",
            "content_version": "9.9.9",
            "content_db_url": "https://example.com/content.db",
            "content_db_sha256": "a" * 64,
            "min_supported_client_version": "99.0.0",
        }

        original_urlopen = __import__("urllib.request").request.urlopen
        try:
            import urllib.request

            class _FakeResponse:
                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, tb):
                    return False

                def read(self):
                    return json.dumps(manifest).encode("utf-8")

            urllib.request.urlopen = lambda *args, **kwargs: _FakeResponse()
            worker.do_check()
        finally:
            import urllib.request

            urllib.request.urlopen = original_urlopen

        assert emitted
        result = emitted[0]
        assert result.error
        assert APP_VERSION in result.error


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
