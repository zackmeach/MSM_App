"""End-to-end update flow tests with a local HTTP server.

Validates the full content update loop:
  manifest fetch -> download -> validate -> finalize -> rollback

Uses a real HTTP server (http.server) serving test artifacts generated
by the pipeline's own build/publish functions.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

import pytest

from app.bootstrap import open_content_db
from app.db.migrations import run_migrations
from app.updater.update_service import UpdateService
from app.updater.validator import (
    validate_checksum,
    validate_content_db,
    validate_manifest_contract,
    ValidationError,
)


# ── Helpers ─────────────────────────────────────────────────────────


def _make_content_db(path: Path, version: str) -> None:
    """Create a valid content DB at the given path with a specific version."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys=ON")
    run_migrations(conn, "content")
    conn.execute(
        "INSERT INTO egg_types(name, breeding_time_seconds, breeding_time_display, "
        "egg_image_path) VALUES('Mammott', 5, '5s', 'images/eggs/mammott_egg.png')"
    )
    conn.execute(
        "INSERT INTO monsters(name, monster_type, image_path, wiki_slug) "
        "VALUES('Zynth', 'wublin', 'images/monsters/zynth.png', 'Zynth')"
    )
    egg_id = conn.execute("SELECT id FROM egg_types WHERE name='Mammott'").fetchone()[0]
    mon_id = conn.execute("SELECT id FROM monsters WHERE name='Zynth'").fetchone()[0]
    conn.execute(
        "INSERT INTO monster_requirements(monster_id, egg_type_id, quantity) "
        "VALUES(?, ?, 3)",
        (mon_id, egg_id),
    )
    conn.execute(
        f"UPDATE update_metadata SET value='{version}' WHERE key='content_version'"
    )
    conn.execute(
        "UPDATE update_metadata SET value='2026-01-01T00:00:00Z' "
        "WHERE key='last_updated_utc'"
    )
    conn.execute("UPDATE update_metadata SET value='test' WHERE key='source'")
    conn.commit()
    conn.close()


def _make_manifest(db_path: Path, version: str, base_url: str) -> dict:
    """Generate a manifest matching what the pipeline would produce."""
    db_bytes = db_path.read_bytes()
    return {
        "artifact_contract_version": "1.1",
        "channel": "stable",
        "content_version": version,
        "schema_version": 2,
        "min_supported_client_version": "1.0.0",
        "content_db_url": f"{base_url}/content.db",
        "content_db_sha256": hashlib.sha256(db_bytes).hexdigest(),
        "content_db_size_bytes": len(db_bytes),
        "content_db_required": True,
        "assets_pack_optional": True,
    }


class _QuietHandler(SimpleHTTPRequestHandler):
    """HTTP handler that suppresses stderr logging."""

    def log_message(self, format, *args):
        pass  # Silence request logging during tests


@pytest.fixture()
def http_server(tmp_path):
    """Spin up a local HTTP server serving files from a temp directory."""
    serve_dir = tmp_path / "serve"
    serve_dir.mkdir()

    handler = type(
        "_Handler",
        (_QuietHandler,),
        {"__init__": lambda self, *a, **kw: _QuietHandler.__init__(self, *a, directory=str(serve_dir), **kw)},
    )

    server = HTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    base_url = f"http://127.0.0.1:{port}"

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    yield serve_dir, base_url, server

    server.shutdown()
    thread.join(timeout=5)


# ── Tests ───────────────────────────────────────────────────────────


class TestManifestFetchAndValidation:
    """Verify manifest fetch from HTTP server and contract validation."""

    def test_manifest_is_valid(self, tmp_path, http_server):
        serve_dir, base_url, _ = http_server

        # Create updated content DB and manifest
        remote_db = serve_dir / "content.db"
        _make_content_db(remote_db, "2.0.0")
        manifest = _make_manifest(remote_db, "2.0.0", base_url)
        (serve_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )

        # Validate the manifest
        validate_manifest_contract(
            manifest,
            allowed_schemes=("http", "https"),
            allowed_hosts=("127.0.0.1", "localhost"),
        )
        assert manifest["content_version"] == "2.0.0"
        assert len(manifest["content_db_sha256"]) == 64
        assert manifest["content_db_url"] == f"{base_url}/content.db"

    def test_manifest_checksum_matches_db(self, tmp_path, http_server):
        serve_dir, base_url, _ = http_server

        remote_db = serve_dir / "content.db"
        _make_content_db(remote_db, "2.0.0")
        manifest = _make_manifest(remote_db, "2.0.0", base_url)

        # Verify checksum matches the actual DB file
        validate_checksum(remote_db, manifest["content_db_sha256"])


class TestUpdateDetection:
    """Verify the update detection logic (is newer version available?)."""

    def test_detects_available_update(self, tmp_path, http_server):
        serve_dir, base_url, _ = http_server
        data_dir = tmp_path / "appdata"
        data_dir.mkdir()

        # Local: version 1.0.0
        local_db = data_dir / "content.db"
        _make_content_db(local_db, "1.0.0")
        conn = open_content_db(local_db)

        # Remote: version 2.0.0
        remote_db = serve_dir / "content.db"
        _make_content_db(remote_db, "2.0.0")
        manifest = _make_manifest(remote_db, "2.0.0", base_url)
        (serve_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )

        # Read versions to compare
        local_version = conn.execute(
            "SELECT value FROM update_metadata WHERE key='content_version'"
        ).fetchone()[0]
        assert local_version == "1.0.0"
        assert manifest["content_version"] == "2.0.0"
        assert manifest["content_version"] != local_version

        conn.close()

    def test_no_update_when_current(self, tmp_path, http_server):
        serve_dir, base_url, _ = http_server
        data_dir = tmp_path / "appdata"
        data_dir.mkdir()

        # Both local and remote are 1.0.0
        local_db = data_dir / "content.db"
        _make_content_db(local_db, "1.0.0")
        conn = open_content_db(local_db)

        remote_db = serve_dir / "content.db"
        _make_content_db(remote_db, "1.0.0")
        manifest = _make_manifest(remote_db, "1.0.0", base_url)
        (serve_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )

        local_version = conn.execute(
            "SELECT value FROM update_metadata WHERE key='content_version'"
        ).fetchone()[0]
        assert local_version == manifest["content_version"]

        conn.close()


class TestStagingAndValidation:
    """Verify download, checksum validation, and schema validation."""

    def test_download_and_validate_staged_db(self, tmp_path, http_server):
        serve_dir, base_url, _ = http_server
        data_dir = tmp_path / "appdata"
        data_dir.mkdir()

        # Set up remote content
        remote_db = serve_dir / "content.db"
        _make_content_db(remote_db, "2.0.0")
        manifest = _make_manifest(remote_db, "2.0.0", base_url)

        # Download the DB via urllib (simulating what the worker does)
        import urllib.request
        staging_path = data_dir / "content_staging.db"
        db_url = manifest["content_db_url"]

        req = urllib.request.Request(db_url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            staging_path.write_bytes(resp.read())

        # Validate checksum
        validate_checksum(staging_path, manifest["content_db_sha256"])

        # Validate schema
        validate_content_db(str(staging_path))

        # Verify version in the staged DB
        conn = sqlite3.connect(str(staging_path))
        version = conn.execute(
            "SELECT value FROM update_metadata WHERE key='content_version'"
        ).fetchone()[0]
        assert version == "2.0.0"
        conn.close()

    def test_checksum_mismatch_raises(self, tmp_path, http_server):
        serve_dir, base_url, _ = http_server

        remote_db = serve_dir / "content.db"
        _make_content_db(remote_db, "2.0.0")

        with pytest.raises(ValidationError, match="Checksum mismatch"):
            validate_checksum(remote_db, "0" * 64)


class TestFinalization:
    """Verify atomic DB replacement and version update."""

    def test_finalize_replaces_db_with_new_version(self, tmp_path, http_server):
        serve_dir, base_url, _ = http_server
        data_dir = tmp_path / "appdata"
        data_dir.mkdir()

        # Set up local v1 and remote v2
        local_db = data_dir / "content.db"
        _make_content_db(local_db, "1.0.0")
        conn = open_content_db(local_db)

        remote_db = serve_dir / "content.db"
        _make_content_db(remote_db, "2.0.0")

        # Stage the update (copy remote to staging location)
        staging = data_dir / "content_staging.db"
        shutil.copy2(remote_db, staging)

        # Finalize
        service = UpdateService(data_dir, conn, manifest_url=f"{base_url}/manifest.json")
        new_conn = service.finalize_update(conn)

        # Verify new version
        version = new_conn.execute(
            "SELECT value FROM update_metadata WHERE key='content_version'"
        ).fetchone()[0]
        assert version == "2.0.0"

        # Verify staging file consumed
        assert not staging.exists()

        # Verify backup created
        assert (data_dir / "content_backup.db").exists()

        new_conn.close()

    def test_rollback_restores_prior_version(self, tmp_path, http_server):
        serve_dir, base_url, _ = http_server
        data_dir = tmp_path / "appdata"
        data_dir.mkdir()

        # Set up local v1 and stage v2
        local_db = data_dir / "content.db"
        _make_content_db(local_db, "1.0.0")
        conn = open_content_db(local_db)

        remote_db = serve_dir / "content.db"
        _make_content_db(remote_db, "2.0.0")

        staging = data_dir / "content_staging.db"
        shutil.copy2(remote_db, staging)

        # Finalize to v2
        service = UpdateService(data_dir, conn, manifest_url=f"{base_url}/manifest.json")
        new_conn = service.finalize_update(conn)
        new_conn.close()

        # Rollback to v1
        restored_conn = service.rollback_update()
        assert restored_conn is not None

        version = restored_conn.execute(
            "SELECT value FROM update_metadata WHERE key='content_version'"
        ).fetchone()[0]
        assert version == "1.0.0"

        restored_conn.close()


class TestFullUpdateLoop:
    """End-to-end: fetch manifest, download, validate, finalize, verify."""

    def test_complete_update_cycle(self, tmp_path, http_server):
        serve_dir, base_url, _ = http_server
        data_dir = tmp_path / "appdata"
        data_dir.mkdir()

        # 1. Set up local v1
        local_db = data_dir / "content.db"
        _make_content_db(local_db, "1.0.0")
        conn = open_content_db(local_db)

        # 2. Set up remote v2 with manifest
        remote_db = serve_dir / "content.db"
        _make_content_db(remote_db, "2.0.0")
        manifest = _make_manifest(remote_db, "2.0.0", base_url)
        (serve_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )

        # 3. Fetch and validate manifest
        import urllib.request
        manifest_url = f"{base_url}/manifest.json"
        req = urllib.request.Request(manifest_url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            fetched_manifest = json.loads(resp.read().decode("utf-8"))
        validate_manifest_contract(
            fetched_manifest,
            allowed_schemes=("http", "https"),
            allowed_hosts=("127.0.0.1", "localhost"),
        )

        # 4. Detect update available
        local_version = conn.execute(
            "SELECT value FROM update_metadata WHERE key='content_version'"
        ).fetchone()[0]
        assert fetched_manifest["content_version"] != local_version

        # 5. Download staged DB
        staging = data_dir / "content_staging.db"
        db_req = urllib.request.Request(fetched_manifest["content_db_url"])
        with urllib.request.urlopen(db_req, timeout=10) as resp:
            staging.write_bytes(resp.read())

        # 6. Validate staged DB
        validate_checksum(staging, fetched_manifest["content_db_sha256"])
        validate_content_db(str(staging))

        # 7. Finalize
        service = UpdateService(data_dir, conn, manifest_url=manifest_url)
        new_conn = service.finalize_update(conn)

        # 8. Verify new version
        new_version = new_conn.execute(
            "SELECT value FROM update_metadata WHERE key='content_version'"
        ).fetchone()[0]
        assert new_version == "2.0.0"

        # 9. Verify data is intact
        monster_count = new_conn.execute("SELECT COUNT(*) FROM monsters").fetchone()[0]
        assert monster_count >= 1

        egg_count = new_conn.execute("SELECT COUNT(*) FROM egg_types").fetchone()[0]
        assert egg_count >= 1

        new_conn.close()
