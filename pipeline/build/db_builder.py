"""Deterministic content DB builder.

Builds a release ``content.db`` from normalized content records,
optionally preserving numeric IDs from a baseline release for
operational stability.
"""

from __future__ import annotations

import sqlite3
import logging
from pathlib import Path

from dataclasses import dataclass

from app.db.migrations import run_migrations

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent.parent / "app" / "db" / "migrations" / "content"


@dataclass
class BuildResult:
    db_path: Path
    monster_count: int
    egg_count: int
    requirement_count: int
    id_preserved: int
    id_reassigned: int
    element_count: int = 0


def build_content_db(
    output_path: Path,
    monsters: list[dict],
    eggs: list[dict],
    requirements: list[dict],
    *,
    content_version: str = "0.0.0-dev",
    baseline_db_path: Path | None = None,
    egg_elements: dict[str, list[str]] | None = None,
) -> BuildResult:
    """Build a deterministic content.db from normalized records.

    If ``baseline_db_path`` is provided, the builder attempts to preserve
    numeric IDs for unchanged ``content_key`` rows.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    conn = sqlite3.connect(str(output_path))
    conn.execute("PRAGMA foreign_keys=ON")
    run_migrations(conn, "content", migrations_dir=MIGRATIONS_DIR)

    baseline_monster_ids: dict[str, int] = {}
    baseline_egg_ids: dict[str, int] = {}
    if baseline_db_path and baseline_db_path.exists():
        baseline_monster_ids, baseline_egg_ids = _load_baseline_ids(baseline_db_path)

    id_preserved = 0
    id_reassigned = 0

    egg_key_to_id: dict[str, int] = {}
    for egg in eggs:
        key = egg["content_key"]
        base_id = baseline_egg_ids.get(key)
        assigned_id = _insert_egg(conn, egg, preferred_id=base_id)
        egg_key_to_id[key] = assigned_id
        if base_id is not None and assigned_id == base_id:
            id_preserved += 1
        elif base_id is not None:
            id_reassigned += 1

    mon_key_to_id: dict[str, int] = {}
    for mon in monsters:
        key = mon["content_key"]
        base_id = baseline_monster_ids.get(key)
        assigned_id = _insert_monster(conn, mon, preferred_id=base_id)
        mon_key_to_id[key] = assigned_id
        if base_id is not None and assigned_id == base_id:
            id_preserved += 1
        elif base_id is not None:
            id_reassigned += 1

    req_count = 0
    for req in requirements:
        mid = mon_key_to_id.get(req["monster_key"])
        eid = egg_key_to_id.get(req["egg_key"])
        if mid is None or eid is None:
            logger.warning(
                "Skipping requirement: monster_key=%s egg_key=%s — ID not found",
                req["monster_key"], req["egg_key"],
            )
            continue
        conn.execute(
            "INSERT INTO monster_requirements(monster_id, egg_type_id, quantity) VALUES(?, ?, ?)",
            (mid, eid, req["quantity"]),
        )
        req_count += 1

    element_count = 0
    if egg_elements:
        element_rows = []
        for egg_key, elements in egg_elements.items():
            eid = egg_key_to_id.get(egg_key)
            if eid is None:
                continue
            for position, element_key in enumerate(elements):
                element_rows.append((eid, element_key, position))
        if element_rows:
            conn.executemany(
                "INSERT INTO egg_type_elements(egg_type_id, element_key, position) "
                "VALUES(?, ?, ?)",
                element_rows,
            )
            element_count = len(element_rows)

    conn.execute("UPDATE update_metadata SET value = ? WHERE key = 'content_version'", (content_version,))
    conn.commit()
    conn.close()

    return BuildResult(
        db_path=output_path,
        monster_count=len(monsters),
        egg_count=len(eggs),
        requirement_count=req_count,
        id_preserved=id_preserved,
        id_reassigned=id_reassigned,
        element_count=element_count,
    )


def _insert_monster(conn: sqlite3.Connection, mon: dict, *, preferred_id: int | None = None) -> int:
    if preferred_id is not None:
        try:
            conn.execute(
                "INSERT INTO monsters"
                "(id, name, monster_type, image_path, wiki_slug, is_placeholder, content_key, "
                "source_fingerprint, asset_source, asset_sha256, is_deprecated, "
                "deprecated_at_utc, deprecation_reason) "
                "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    preferred_id,
                    mon["display_name"],
                    mon["monster_type"],
                    mon["image_path"],
                    mon.get("wiki_slug", ""),
                    1 if mon.get("is_placeholder", True) else 0,
                    mon["content_key"],
                    mon.get("source_fingerprint", ""),
                    mon.get("asset_source", "generated_placeholder"),
                    mon.get("asset_sha256", ""),
                    1 if mon.get("is_deprecated", False) else 0,
                    mon.get("deprecated_at_utc"),
                    mon.get("deprecation_reason"),
                ),
            )
            return preferred_id
        except sqlite3.IntegrityError:
            logger.debug("Could not preserve ID %d for %s, using autoincrement", preferred_id, mon["content_key"])

    cur = conn.execute(
        "INSERT INTO monsters"
        "(name, monster_type, image_path, wiki_slug, is_placeholder, content_key, "
        "source_fingerprint, asset_source, asset_sha256, is_deprecated, "
        "deprecated_at_utc, deprecation_reason) "
        "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            mon["display_name"],
            mon["monster_type"],
            mon["image_path"],
            mon.get("wiki_slug", ""),
            1 if mon.get("is_placeholder", True) else 0,
            mon["content_key"],
            mon.get("source_fingerprint", ""),
            mon.get("asset_source", "generated_placeholder"),
            mon.get("asset_sha256", ""),
            1 if mon.get("is_deprecated", False) else 0,
            mon.get("deprecated_at_utc"),
            mon.get("deprecation_reason"),
        ),
    )
    return cur.lastrowid  # type: ignore[return-value]


def _insert_egg(conn: sqlite3.Connection, egg: dict, *, preferred_id: int | None = None) -> int:
    if preferred_id is not None:
        try:
            conn.execute(
                "INSERT INTO egg_types"
                "(id, name, breeding_time_seconds, breeding_time_display, egg_image_path, "
                "is_placeholder, content_key, source_fingerprint, asset_source, asset_sha256, "
                "is_deprecated, deprecated_at_utc, deprecation_reason) "
                "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    preferred_id,
                    egg["display_name"],
                    egg["breeding_time_seconds"],
                    egg["breeding_time_display"],
                    egg["egg_image_path"],
                    1 if egg.get("is_placeholder", True) else 0,
                    egg["content_key"],
                    egg.get("source_fingerprint", ""),
                    egg.get("asset_source", "generated_placeholder"),
                    egg.get("asset_sha256", ""),
                    1 if egg.get("is_deprecated", False) else 0,
                    egg.get("deprecated_at_utc"),
                    egg.get("deprecation_reason"),
                ),
            )
            return preferred_id
        except sqlite3.IntegrityError:
            logger.debug("Could not preserve ID %d for %s, using autoincrement", preferred_id, egg["content_key"])

    cur = conn.execute(
        "INSERT INTO egg_types"
        "(name, breeding_time_seconds, breeding_time_display, egg_image_path, "
        "is_placeholder, content_key, source_fingerprint, asset_source, asset_sha256, "
        "is_deprecated, deprecated_at_utc, deprecation_reason) "
        "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            egg["display_name"],
            egg["breeding_time_seconds"],
            egg["breeding_time_display"],
            egg["egg_image_path"],
            1 if egg.get("is_placeholder", True) else 0,
            egg["content_key"],
            egg.get("source_fingerprint", ""),
            egg.get("asset_source", "generated_placeholder"),
            egg.get("asset_sha256", ""),
            1 if egg.get("is_deprecated", False) else 0,
            egg.get("deprecated_at_utc"),
            egg.get("deprecation_reason"),
        ),
    )
    return cur.lastrowid  # type: ignore[return-value]


def _load_baseline_ids(db_path: Path) -> tuple[dict[str, int], dict[str, int]]:
    conn = sqlite3.connect(str(db_path))
    monster_ids: dict[str, int] = {}
    egg_ids: dict[str, int] = {}
    try:
        for row in conn.execute("SELECT id, content_key FROM monsters").fetchall():
            if row[1]:
                monster_ids[row[1]] = row[0]
        for row in conn.execute("SELECT id, content_key FROM egg_types").fetchall():
            if row[1]:
                egg_ids[row[1]] = row[0]
    except sqlite3.OperationalError:
        logger.warning("Baseline DB missing content_key columns — no ID preservation")
    finally:
        conn.close()
    return monster_ids, egg_ids
