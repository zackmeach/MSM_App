"""Verify that the resource bundle contains all expected files.

Checks:
- Core resources (content.db, placeholder, icon, ding audio)
- Every image path referenced in content.db exists under resources/
- Row count assertions match seeded expectations

Run:  python scripts/verify_bundle.py
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESOURCES = ROOT / "resources"


def main() -> int:
    errors: list[str] = []

    db_path = RESOURCES / "db" / "content.db"
    if not db_path.exists():
        print(f"FAIL  {db_path}")
        return 1

    print(f"  OK  {db_path.relative_to(ROOT)}")

    core_files = [
        RESOURCES / "images" / "ui" / "placeholder.png",
        RESOURCES / "images" / "ui" / "app_icon.ico",
        RESOURCES / "audio" / "ding.wav",
    ]
    for f in core_files:
        if not f.exists():
            errors.append(f"MISSING: {f.relative_to(ROOT)}")
        else:
            print(f"  OK  {f.relative_to(ROOT)}")

    conn = sqlite3.connect(str(db_path))

    monster_count = conn.execute("SELECT COUNT(*) FROM monsters").fetchone()[0]
    egg_count = conn.execute("SELECT COUNT(*) FROM egg_types").fetchone()[0]
    req_count = conn.execute("SELECT COUNT(*) FROM monster_requirements").fetchone()[0]

    for label, expected_min, actual in [
        ("Monsters", 39, monster_count),
        ("Egg types", 38, egg_count),
        ("Requirements", 450, req_count),
    ]:
        if actual < expected_min:
            errors.append(f"{label}: expected >= {expected_min}, got {actual}")
        else:
            print(f"  OK  {label}: {actual}")

    types = conn.execute(
        "SELECT monster_type, COUNT(*) FROM monsters GROUP BY monster_type"
    ).fetchall()
    type_map = dict(types)

    for mtype, expected in [("wublin", 19), ("celestial", 12), ("amber", 8)]:
        actual = type_map.get(mtype, 0)
        if actual < expected:
            errors.append(f"{mtype}: expected >= {expected}, got {actual}")
        else:
            print(f"  OK  {mtype}: {actual}")

    orphans = conn.execute(
        "SELECT mr.monster_id, mr.egg_type_id FROM monster_requirements mr "
        "LEFT JOIN monsters m ON mr.monster_id = m.id "
        "LEFT JOIN egg_types e ON mr.egg_type_id = e.id "
        "WHERE m.id IS NULL OR e.id IS NULL"
    ).fetchall()
    if orphans:
        errors.append(f"Orphaned requirement rows: {orphans}")
    else:
        print("  OK  No orphaned requirements")

    missing_assets = _check_db_referenced_assets(conn)
    errors.extend(missing_assets)
    if not missing_assets:
        print("  OK  All DB-referenced asset paths exist in bundle")

    conn.close()

    if errors:
        print()
        for e in errors:
            print(f"FAIL  {e}")
        return 1

    print("\nBundle verification passed.")
    return 0


def _check_db_referenced_assets(conn: sqlite3.Connection) -> list[str]:
    """Verify every image path in the DB exists under RESOURCES."""
    errors: list[str] = []

    for row in conn.execute(
        "SELECT name, image_path FROM monsters WHERE image_path != ''"
    ):
        name, rel_path = row
        full = RESOURCES / rel_path
        if not full.exists():
            errors.append(f"MISSING monster asset: {rel_path} (monster: {name})")

    for row in conn.execute(
        "SELECT name, egg_image_path FROM egg_types WHERE egg_image_path != ''"
    ):
        name, rel_path = row
        full = RESOURCES / rel_path
        if not full.exists():
            errors.append(f"MISSING egg asset: {rel_path} (egg: {name})")

    return errors


if __name__ == "__main__":
    sys.exit(main())
