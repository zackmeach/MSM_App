"""Read-only repository for monsters, egg types, and requirements from content.db."""

from __future__ import annotations

import sqlite3

from app.domain.models import EggType, Monster, MonsterRequirement, MonsterType

# Column names used by SELECT * on the v2 schema.  The repo gracefully
# falls back when extra columns are absent (pre-migration DB).
_MONSTER_V2_COLS = 13  # id..deprecation_reason
_EGG_V2_COLS = 13      # id..asset_sha256


def fetch_all_monsters(conn: sqlite3.Connection, *, include_deprecated: bool = False) -> list[Monster]:
    sql = "SELECT * FROM monsters"
    if not include_deprecated:
        sql += " WHERE is_deprecated = 0"
    sql += " ORDER BY monster_type, name"
    rows = conn.execute(sql).fetchall()
    return [_monster_from_row(r) for r in rows]


def fetch_monsters_by_type(conn: sqlite3.Connection, monster_type: MonsterType) -> list[Monster]:
    rows = conn.execute(
        "SELECT * FROM monsters WHERE monster_type = ? AND is_deprecated = 0 ORDER BY name",
        (monster_type.value,),
    ).fetchall()
    return [_monster_from_row(r) for r in rows]


def fetch_monster_by_id(conn: sqlite3.Connection, monster_id: int) -> Monster | None:
    row = conn.execute("SELECT * FROM monsters WHERE id = ?", (monster_id,)).fetchone()
    return _monster_from_row(row) if row else None


def fetch_monster_by_key(conn: sqlite3.Connection, content_key: str) -> Monster | None:
    row = conn.execute(
        "SELECT * FROM monsters WHERE content_key = ?", (content_key,)
    ).fetchone()
    return _monster_from_row(row) if row else None


def monster_exists_and_active(conn: sqlite3.Connection, monster_id: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM monsters WHERE id = ? AND is_deprecated = 0", (monster_id,)
    ).fetchone()
    return row is not None


def fetch_all_egg_types(conn: sqlite3.Connection) -> list[EggType]:
    rows = conn.execute("SELECT * FROM egg_types ORDER BY name").fetchall()
    elements_by_id = _fetch_egg_elements(conn)
    return [_egg_type_from_row(r, elements_by_id.get(r[0], ())) for r in rows]


def fetch_egg_types_map(conn: sqlite3.Connection) -> dict[int, EggType]:
    return {et.id: et for et in fetch_all_egg_types(conn)}


def _fetch_egg_elements(conn: sqlite3.Connection) -> dict[int, tuple[str, ...]]:
    """Return {egg_type_id: (element_key, ...)} ordered by position.

    Returns empty dict if the table is missing (pre-migration DB) so callers
    can JOIN unconditionally without breaking on older schemas.
    """
    try:
        rows = conn.execute(
            "SELECT egg_type_id, element_key FROM egg_type_elements "
            "ORDER BY egg_type_id, position"
        ).fetchall()
    except sqlite3.OperationalError:
        return {}
    out: dict[int, list[str]] = {}
    for eid, key in rows:
        out.setdefault(eid, []).append(key)
    return {eid: tuple(keys) for eid, keys in out.items()}


def fetch_egg_type_by_key(conn: sqlite3.Connection, content_key: str) -> EggType | None:
    row = conn.execute(
        "SELECT * FROM egg_types WHERE content_key = ?", (content_key,)
    ).fetchone()
    if not row:
        return None
    elements = _fetch_egg_elements(conn).get(row[0], ())
    return _egg_type_from_row(row, elements)


def fetch_requirements_for_monster(conn: sqlite3.Connection, monster_id: int) -> list[MonsterRequirement]:
    rows = conn.execute(
        "SELECT monster_id, egg_type_id, quantity FROM monster_requirements WHERE monster_id = ?",
        (monster_id,),
    ).fetchall()
    return [MonsterRequirement(monster_id=r[0], egg_type_id=r[1], quantity=r[2]) for r in rows]


def fetch_all_requirements(conn: sqlite3.Connection) -> dict[int, list[MonsterRequirement]]:
    rows = conn.execute("SELECT monster_id, egg_type_id, quantity FROM monster_requirements").fetchall()
    result: dict[int, list[MonsterRequirement]] = {}
    for r in rows:
        req = MonsterRequirement(monster_id=r[0], egg_type_id=r[1], quantity=r[2])
        result.setdefault(req.monster_id, []).append(req)
    return result


def fetch_update_metadata(conn: sqlite3.Connection) -> dict[str, str]:
    rows = conn.execute("SELECT key, value FROM update_metadata").fetchall()
    return {r[0]: r[1] for r in rows}


def _monster_from_row(row: tuple) -> Monster:
    has_v2 = len(row) >= _MONSTER_V2_COLS
    return Monster(
        id=row[0],
        name=row[1],
        monster_type=MonsterType(row[2]),
        image_path=row[3],
        is_placeholder=bool(row[4]),
        wiki_slug=row[5],
        is_deprecated=bool(row[6]),
        content_key=row[7] if has_v2 else "",
        source_fingerprint=row[8] if has_v2 else "",
        asset_source=row[9] if has_v2 else "generated_placeholder",
        asset_sha256=row[10] if has_v2 else "",
        deprecated_at_utc=row[11] if has_v2 else None,
        deprecation_reason=row[12] if has_v2 else None,
    )


def _egg_type_from_row(row: tuple, elements: tuple[str, ...] = ()) -> EggType:
    has_v2 = len(row) >= _EGG_V2_COLS
    return EggType(
        id=row[0],
        name=row[1],
        breeding_time_seconds=row[2],
        breeding_time_display=row[3],
        egg_image_path=row[4],
        is_placeholder=bool(row[5]),
        content_key=row[6] if has_v2 else "",
        is_deprecated=bool(row[7]) if has_v2 else False,
        deprecated_at_utc=row[8] if has_v2 else None,
        deprecation_reason=row[9] if has_v2 else None,
        source_fingerprint=row[10] if has_v2 else "",
        asset_source=row[11] if has_v2 else "generated_placeholder",
        asset_sha256=row[12] if has_v2 else "",
        elements=elements,
    )
