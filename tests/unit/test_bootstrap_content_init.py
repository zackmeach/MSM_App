"""Tests for bootstrap content.db initialization and version-based replacement.

The in-app updater writes a fresh content.db to the user's data dir.
A naive `installed != bundled` check would silently revert user-applied
updates on every relaunch — these tests pin the strict-greater behavior.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.bootstrap import _init_content_db, _parse_version


def _write_content_db(path: Path, version: str | None) -> None:
    """Create a minimal content.db with an optional content_version row."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS update_metadata (key TEXT PRIMARY KEY, value TEXT)"
    )
    if version is not None:
        conn.execute(
            "INSERT INTO update_metadata(key, value) VALUES('content_version', ?)",
            (version,),
        )
    conn.commit()
    conn.close()


def _content_version_of(path: Path) -> str:
    conn = sqlite3.connect(str(path))
    try:
        row = conn.execute(
            "SELECT value FROM update_metadata WHERE key='content_version'"
        ).fetchone()
        return row[0] if row else ""
    finally:
        conn.close()


@pytest.fixture
def dirs(tmp_path: Path) -> tuple[Path, Path]:
    data_dir = tmp_path / "data"
    bundle_dir = tmp_path / "bundle"
    data_dir.mkdir()
    (bundle_dir / "db").mkdir(parents=True)
    return data_dir, bundle_dir


def test_parse_version_handles_empty_and_garbage():
    assert _parse_version("") is None
    assert _parse_version("not-a-version") is None
    assert _parse_version("1.2.3") == (1, 2, 3)
    assert _parse_version("2.0") == (2, 0)


def test_copies_bundle_when_installed_missing(dirs: tuple[Path, Path]) -> None:
    data_dir, bundle_dir = dirs
    bundled = bundle_dir / "db" / "content.db"
    _write_content_db(bundled, "1.1.1")

    conn = _init_content_db(data_dir, bundle_dir)
    conn.close()

    assert (data_dir / "content.db").exists()
    assert _content_version_of(data_dir / "content.db") == "1.1.1"


def test_replaces_when_bundle_strictly_newer(dirs: tuple[Path, Path]) -> None:
    data_dir, bundle_dir = dirs
    installed = data_dir / "content.db"
    bundled = bundle_dir / "db" / "content.db"
    _write_content_db(installed, "1.0.0")
    _write_content_db(bundled, "1.1.0")

    conn = _init_content_db(data_dir, bundle_dir)
    conn.close()

    assert _content_version_of(installed) == "1.1.0"


def test_does_not_downgrade_when_installed_newer(dirs: tuple[Path, Path]) -> None:
    """The regression guard: user updated to 2.0.0 in-app; bundle is still 1.1.1."""
    data_dir, bundle_dir = dirs
    installed = data_dir / "content.db"
    bundled = bundle_dir / "db" / "content.db"
    _write_content_db(installed, "2.0.0")
    _write_content_db(bundled, "1.1.1")

    conn = _init_content_db(data_dir, bundle_dir)
    conn.close()

    assert _content_version_of(installed) == "2.0.0"


def test_no_swap_when_versions_equal(dirs: tuple[Path, Path]) -> None:
    data_dir, bundle_dir = dirs
    installed = data_dir / "content.db"
    bundled = bundle_dir / "db" / "content.db"
    _write_content_db(installed, "1.1.1")
    # Add a marker row to the installed copy that the bundled copy lacks,
    # so we can detect a silent swap by checking whether the marker survives.
    conn = sqlite3.connect(str(installed))
    conn.execute(
        "INSERT INTO update_metadata(key, value) VALUES('_marker', 'installed')"
    )
    conn.commit()
    conn.close()
    _write_content_db(bundled, "1.1.1")

    init_conn = _init_content_db(data_dir, bundle_dir)
    init_conn.close()

    check = sqlite3.connect(str(installed))
    row = check.execute(
        "SELECT value FROM update_metadata WHERE key='_marker'"
    ).fetchone()
    check.close()
    assert row is not None and row[0] == "installed"


def test_no_swap_when_installed_unparseable(dirs: tuple[Path, Path]) -> None:
    data_dir, bundle_dir = dirs
    installed = data_dir / "content.db"
    bundled = bundle_dir / "db" / "content.db"
    _write_content_db(installed, "garble")
    _write_content_db(bundled, "1.1.1")

    conn = _init_content_db(data_dir, bundle_dir)
    conn.close()

    assert _content_version_of(installed) == "garble"
