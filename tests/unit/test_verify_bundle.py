"""Tests for the bundle verification script.

Verifies that verify_bundle.py correctly detects missing or incomplete bundles.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from verify_bundle import _check_db_referenced_assets, main  # noqa: E402


@pytest.fixture()
def bundle_root(tmp_path):
    """Create a minimal valid bundle structure."""
    db_dir = tmp_path / "resources" / "db"
    db_dir.mkdir(parents=True)
    (tmp_path / "resources" / "images" / "ui").mkdir(parents=True)
    (tmp_path / "resources" / "images" / "eggs").mkdir(parents=True)
    (tmp_path / "resources" / "images" / "monsters").mkdir(parents=True)
    (tmp_path / "resources" / "audio").mkdir(parents=True)

    (tmp_path / "resources" / "images" / "ui" / "placeholder.png").write_bytes(b"png")
    (tmp_path / "resources" / "images" / "ui" / "app_icon.ico").write_bytes(b"ico")
    (tmp_path / "resources" / "audio" / "ding.wav").write_bytes(b"wav")

    db_path = db_dir / "content.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys=ON")

    ROOT_APP = Path(__file__).resolve().parent.parent.parent
    sys.path.insert(0, str(ROOT_APP))
    from app.db.migrations import run_migrations

    run_migrations(conn, "content")

    conn.execute(
        "INSERT INTO egg_types(name, breeding_time_seconds, breeding_time_display, egg_image_path) "
        "VALUES('TestEgg', 100, '1m 40s', 'images/eggs/testegg.png')"
    )
    conn.execute(
        "INSERT INTO monsters(name, monster_type, image_path, wiki_slug) "
        "VALUES('TestMon', 'wublin', 'images/monsters/testmon.png', 'TestMon')"
    )
    conn.execute("UPDATE update_metadata SET value='1.0.0' WHERE key='content_version'")
    conn.execute("UPDATE update_metadata SET value='2026-01-01T00:00:00Z' WHERE key='last_updated_utc'")
    conn.execute("UPDATE update_metadata SET value='test' WHERE key='source'")
    conn.commit()
    conn.close()

    return tmp_path / "resources"


class TestCheckDbReferencedAssets:
    def test_missing_monster_image_detected(self, bundle_root):
        (bundle_root / "images" / "eggs" / "testegg.png").write_bytes(b"png")
        conn = sqlite3.connect(str(bundle_root / "db" / "content.db"))
        with mock.patch("verify_bundle.RESOURCES", bundle_root):
            errors = _check_db_referenced_assets(conn)
        conn.close()
        assert any("testmon.png" in e for e in errors)

    def test_missing_egg_image_detected(self, bundle_root):
        (bundle_root / "images" / "monsters" / "testmon.png").write_bytes(b"png")
        conn = sqlite3.connect(str(bundle_root / "db" / "content.db"))
        with mock.patch("verify_bundle.RESOURCES", bundle_root):
            errors = _check_db_referenced_assets(conn)
        conn.close()
        assert any("testegg.png" in e for e in errors)

    def test_complete_bundle_passes(self, bundle_root):
        (bundle_root / "images" / "eggs" / "testegg.png").write_bytes(b"png")
        (bundle_root / "images" / "monsters" / "testmon.png").write_bytes(b"png")
        conn = sqlite3.connect(str(bundle_root / "db" / "content.db"))
        with mock.patch("verify_bundle.RESOURCES", bundle_root):
            errors = _check_db_referenced_assets(conn)
        conn.close()
        assert errors == []

    def test_missing_placeholder_fails_main(self, bundle_root):
        (bundle_root / "images" / "ui" / "placeholder.png").unlink()
        (bundle_root / "images" / "eggs" / "testegg.png").write_bytes(b"png")
        (bundle_root / "images" / "monsters" / "testmon.png").write_bytes(b"png")

        with mock.patch("verify_bundle.RESOURCES", bundle_root):
            with mock.patch("verify_bundle.ROOT", bundle_root.parent):
                result = main()
        assert result == 1
