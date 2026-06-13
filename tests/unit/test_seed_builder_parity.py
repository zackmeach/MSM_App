"""Parity guard: the bundled-DB seeder and the publish DB builder must produce
identical content from the same normalized data.

``scripts/seed_content_db`` builds the *bundled* ``resources/db/content.db``;
``pipeline/build/db_builder`` builds the *published-update* content.db. They are
two implementations of the same job and currently produce byte-equivalent rows.
This test fails if they ever drift, so an edit to one cannot silently diverge
from the other on the release-artifact path — the low-risk alternative to
consolidating the two builders.
"""

from __future__ import annotations

import sqlite3

import pytest

from app.db.migrations import run_migrations
from pipeline.build.db_builder import build_content_db
from scripts.seed_content_db import (
    _load_egg_elements,
    _load_normalized,
    _populate_egg_elements,
    _seed_from_normalized,
)

_MON_COLS = (
    "content_key, name, monster_type, image_path, wiki_slug, is_placeholder, "
    "is_deprecated, deprecated_at_utc, deprecation_reason, source_fingerprint, "
    "asset_source, asset_sha256"
)
_EGG_COLS = (
    "content_key, name, breeding_time_seconds, breeding_time_display, egg_image_path, "
    "is_placeholder, is_deprecated, deprecated_at_utc, deprecation_reason, "
    "source_fingerprint, asset_source, asset_sha256"
)


def _rows_by_key(conn: sqlite3.Connection, table: str, cols: str) -> dict:
    return {r[0]: r for r in conn.execute(f"SELECT {cols} FROM {table}")}  # noqa: S608


def _req_edges(conn: sqlite3.Connection) -> list:
    """Requirement edges keyed by content_key, so numeric-id order is irrelevant."""
    mk = {r[0]: r[1] for r in conn.execute("SELECT id, content_key FROM monsters")}
    ek = {r[0]: r[1] for r in conn.execute("SELECT id, content_key FROM egg_types")}
    return sorted(
        (mk[m], ek[e], q)
        for m, e, q in conn.execute(
            "SELECT monster_id, egg_type_id, quantity FROM monster_requirements"
        )
    )


def _elem_edges(conn: sqlite3.Connection) -> list:
    ek = {r[0]: r[1] for r in conn.execute("SELECT id, content_key FROM egg_types")}
    return sorted(
        (ek[e], el, pos)
        for e, el, pos in conn.execute(
            "SELECT egg_type_id, element_key, position FROM egg_type_elements"
        )
    )


def test_seed_and_db_builder_produce_equivalent_content(tmp_path):
    normalized = _load_normalized()
    if normalized is None:
        pytest.skip("no normalized baseline present")
    monsters, eggs, requirements = normalized
    egg_elements = _load_egg_elements()

    # ── Bundled seeder path ──
    seed_path = tmp_path / "seed.db"
    conn_seed = sqlite3.connect(str(seed_path))
    conn_seed.execute("PRAGMA foreign_keys=ON")
    run_migrations(conn_seed, "content")
    _seed_from_normalized(conn_seed, monsters, eggs, requirements)
    egg_key_to_id = {
        r[1]: r[0] for r in conn_seed.execute("SELECT id, content_key FROM egg_types")
    }
    _populate_egg_elements(conn_seed, egg_key_to_id, egg_elements)
    conn_seed.commit()

    # ── Publish builder path ──
    build_path = tmp_path / "build.db"
    build_content_db(build_path, monsters, eggs, requirements, egg_elements=egg_elements)
    conn_build = sqlite3.connect(str(build_path))

    try:
        assert _rows_by_key(conn_seed, "monsters", _MON_COLS) == _rows_by_key(
            conn_build, "monsters", _MON_COLS
        )
        assert _rows_by_key(conn_seed, "egg_types", _EGG_COLS) == _rows_by_key(
            conn_build, "egg_types", _EGG_COLS
        )
        assert _req_edges(conn_seed) == _req_edges(conn_build)
        assert _elem_edges(conn_seed) == _elem_edges(conn_build)
    finally:
        conn_seed.close()
        conn_build.close()
