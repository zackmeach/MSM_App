"""Repository for active_targets and target_requirement_progress in userstate.db."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from app.domain.models import ActiveTarget, MonsterRequirement, TargetRequirementProgress


# ── Active Targets ───────────────────────────────────────────────────

def insert_target(conn: sqlite3.Connection, monster_id: int) -> int:
    """Insert a new active target and return its id."""
    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        "INSERT INTO active_targets(monster_id, added_at) VALUES(?, ?)",
        (monster_id, now),
    )
    return cur.lastrowid  # type: ignore[return-value]


def insert_target_with_id(
    conn: sqlite3.Connection, target_id: int, monster_id: int, added_at: str
) -> None:
    """Re-insert a target preserving its original id (for undo)."""
    conn.execute(
        "INSERT INTO active_targets(id, monster_id, added_at) VALUES(?, ?, ?)",
        (target_id, monster_id, added_at),
    )


def delete_target(conn: sqlite3.Connection, target_id: int) -> None:
    conn.execute("DELETE FROM active_targets WHERE id = ?", (target_id,))


def fetch_target_by_id(conn: sqlite3.Connection, target_id: int) -> ActiveTarget | None:
    row = conn.execute("SELECT id, monster_id, added_at FROM active_targets WHERE id = ?", (target_id,)).fetchone()
    return ActiveTarget(id=row[0], monster_id=row[1], added_at=row[2]) if row else None


def fetch_all_targets(conn: sqlite3.Connection) -> list[ActiveTarget]:
    rows = conn.execute("SELECT id, monster_id, added_at FROM active_targets ORDER BY added_at, id").fetchall()
    return [ActiveTarget(id=r[0], monster_id=r[1], added_at=r[2]) for r in rows]


def fetch_newest_target_for_monster(conn: sqlite3.Connection, monster_id: int) -> ActiveTarget | None:
    """Return the most recently added active target for a monster (for close-out)."""
    row = conn.execute(
        "SELECT id, monster_id, added_at FROM active_targets WHERE monster_id = ? ORDER BY id DESC LIMIT 1",
        (monster_id,),
    ).fetchone()
    return ActiveTarget(id=row[0], monster_id=row[1], added_at=row[2]) if row else None


# ── Target Requirement Progress ──────────────────────────────────────

def materialize_progress(
    conn: sqlite3.Connection,
    target_id: int,
    requirements: list[MonsterRequirement],
) -> None:
    """Create target_requirement_progress rows for a newly added target."""
    conn.executemany(
        "INSERT INTO target_requirement_progress(active_target_id, egg_type_id, required_count, satisfied_count) VALUES(?, ?, ?, 0)",
        [(target_id, r.egg_type_id, r.quantity) for r in requirements],
    )


def delete_progress_for_target(conn: sqlite3.Connection, target_id: int) -> list[TargetRequirementProgress]:
    """Delete all progress rows for a target. Returns the deleted rows for undo snapshot."""
    rows = conn.execute(
        "SELECT active_target_id, egg_type_id, required_count, satisfied_count "
        "FROM target_requirement_progress WHERE active_target_id = ?",
        (target_id,),
    ).fetchall()
    snapshot = [TargetRequirementProgress(r[0], r[1], r[2], r[3]) for r in rows]
    conn.execute("DELETE FROM target_requirement_progress WHERE active_target_id = ?", (target_id,))
    return snapshot


def restore_progress_rows(conn: sqlite3.Connection, rows: list[TargetRequirementProgress]) -> None:
    """Re-insert previously deleted progress rows (for undo)."""
    conn.executemany(
        "INSERT INTO target_requirement_progress(active_target_id, egg_type_id, required_count, satisfied_count) VALUES(?, ?, ?, ?)",
        [(r.active_target_id, r.egg_type_id, r.required_count, r.satisfied_count) for r in rows],
    )


def fetch_all_progress(conn: sqlite3.Connection) -> list[TargetRequirementProgress]:
    rows = conn.execute(
        "SELECT active_target_id, egg_type_id, required_count, satisfied_count "
        "FROM target_requirement_progress"
    ).fetchall()
    return [TargetRequirementProgress(r[0], r[1], r[2], r[3]) for r in rows]


def fetch_progress_for_egg(conn: sqlite3.Connection, egg_type_id: int) -> list[TargetRequirementProgress]:
    """All progress rows for a given egg type, ordered oldest-target-first."""
    rows = conn.execute(
        "SELECT trp.active_target_id, trp.egg_type_id, trp.required_count, trp.satisfied_count "
        "FROM target_requirement_progress trp "
        "JOIN active_targets at ON trp.active_target_id = at.id "
        "WHERE trp.egg_type_id = ? "
        "ORDER BY at.added_at ASC, at.id ASC",
        (egg_type_id,),
    ).fetchall()
    return [TargetRequirementProgress(r[0], r[1], r[2], r[3]) for r in rows]


def increment_progress(conn: sqlite3.Connection, target_id: int, egg_type_id: int) -> int:
    """Increment satisfied_count by 1. Returns the new satisfied_count."""
    conn.execute(
        "UPDATE target_requirement_progress SET satisfied_count = satisfied_count + 1 "
        "WHERE active_target_id = ? AND egg_type_id = ?",
        (target_id, egg_type_id),
    )
    row = conn.execute(
        "SELECT satisfied_count FROM target_requirement_progress WHERE active_target_id = ? AND egg_type_id = ?",
        (target_id, egg_type_id),
    ).fetchone()
    return row[0] if row else 0


def set_progress(conn: sqlite3.Connection, target_id: int, egg_type_id: int, satisfied_count: int) -> None:
    """Set satisfied_count to an exact value (for undo)."""
    conn.execute(
        "UPDATE target_requirement_progress SET satisfied_count = ? "
        "WHERE active_target_id = ? AND egg_type_id = ?",
        (satisfied_count, target_id, egg_type_id),
    )
