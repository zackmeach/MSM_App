"""Verify that the resource bundle contains all expected files.

Run:  python scripts/verify_bundle.py
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESOURCES = ROOT / "resources"


def main() -> int:
    ok = True
    errors: list[str] = []

    db_path = RESOURCES / "db" / "content.db"
    if not db_path.exists():
        errors.append(f"MISSING: {db_path}")
        print(f"FAIL  {db_path}")
        return 1

    placeholder = RESOURCES / "images" / "ui" / "placeholder.png"
    if not placeholder.exists():
        errors.append(f"MISSING: {placeholder}")
    else:
        print(f"  OK  {placeholder.relative_to(ROOT)}")

    ding = RESOURCES / "audio" / "ding.wav"
    if not ding.exists():
        errors.append(f"MISSING: {ding}")
    else:
        print(f"  OK  {ding.relative_to(ROOT)}")

    conn = sqlite3.connect(str(db_path))

    monster_count = conn.execute("SELECT COUNT(*) FROM monsters").fetchone()[0]
    egg_count = conn.execute("SELECT COUNT(*) FROM egg_types").fetchone()[0]
    req_count = conn.execute("SELECT COUNT(*) FROM monster_requirements").fetchone()[0]

    for label, expected_min, actual in [
        ("Monsters", 30, monster_count),
        ("Egg types", 30, egg_count),
        ("Requirements", 200, req_count),
    ]:
        if actual < expected_min:
            errors.append(f"{label}: expected >= {expected_min}, got {actual}")
        else:
            print(f"  OK  {label}: {actual}")

    types = conn.execute(
        "SELECT monster_type, COUNT(*) FROM monsters GROUP BY monster_type"
    ).fetchall()
    type_map = dict(types)

    for mtype, min_count in [("wublin", 19), ("celestial", 12), ("amber", 3)]:
        actual = type_map.get(mtype, 0)
        if actual < min_count:
            errors.append(f"{mtype}: expected >= {min_count}, got {actual}")
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

    conn.close()

    if errors:
        print()
        for e in errors:
            print(f"FAIL  {e}")
        return 1

    print("\nBundle verification passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
