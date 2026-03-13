"""Validate that a downloaded content.db has the required schema shape."""

from __future__ import annotations

import sqlite3

REQUIRED_TABLES = {"monsters", "egg_types", "monster_requirements", "update_metadata"}
REQUIRED_METADATA_KEYS = {"content_version", "last_updated_utc", "source"}


class ValidationError(Exception):
    pass


def validate_content_db(db_path: str) -> None:
    """Raise ValidationError if the DB does not meet minimum content contract."""
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA integrity_check")
    except sqlite3.Error as exc:
        raise ValidationError(f"Cannot open database: {exc}") from exc

    try:
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        missing = REQUIRED_TABLES - tables
        if missing:
            raise ValidationError(f"Missing tables: {missing}")

        for key in REQUIRED_METADATA_KEYS:
            row = conn.execute(
                "SELECT value FROM update_metadata WHERE key = ?", (key,)
            ).fetchone()
            if not row or not row[0]:
                raise ValidationError(f"Missing or empty metadata key: {key}")

        monster_count = conn.execute("SELECT COUNT(*) FROM monsters").fetchone()[0]
        if monster_count < 1:
            raise ValidationError("No monsters in database")

        egg_count = conn.execute("SELECT COUNT(*) FROM egg_types").fetchone()[0]
        if egg_count < 1:
            raise ValidationError("No egg types in database")

        orphans = conn.execute(
            "SELECT COUNT(*) FROM monster_requirements mr "
            "LEFT JOIN monsters m ON mr.monster_id = m.id "
            "WHERE m.id IS NULL"
        ).fetchone()[0]
        if orphans > 0:
            raise ValidationError(f"{orphans} requirement rows reference nonexistent monsters")

    finally:
        conn.close()
