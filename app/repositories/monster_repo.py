"""Read-only repository for monsters, egg types, and requirements from content.db."""

from __future__ import annotations

import sqlite3

from app.domain.models import EggType, Monster, MonsterRequirement, MonsterType


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


def monster_exists_and_active(conn: sqlite3.Connection, monster_id: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM monsters WHERE id = ? AND is_deprecated = 0", (monster_id,)
    ).fetchone()
    return row is not None


def fetch_all_egg_types(conn: sqlite3.Connection) -> list[EggType]:
    rows = conn.execute("SELECT * FROM egg_types ORDER BY name").fetchall()
    return [_egg_type_from_row(r) for r in rows]


def fetch_egg_types_map(conn: sqlite3.Connection) -> dict[int, EggType]:
    return {et.id: et for et in fetch_all_egg_types(conn)}


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
    return Monster(
        id=row[0],
        name=row[1],
        monster_type=MonsterType(row[2]),
        image_path=row[3],
        is_placeholder=bool(row[4]),
        wiki_slug=row[5],
        is_deprecated=bool(row[6]),
    )


def _egg_type_from_row(row: tuple) -> EggType:
    return EggType(
        id=row[0],
        name=row[1],
        breeding_time_seconds=row[2],
        breeding_time_display=row[3],
        egg_image_path=row[4],
        is_placeholder=bool(row[5]),
    )
