"""Application bootstrap: path detection, DB init, logging, service wiring."""

from __future__ import annotations

import logging
import logging.handlers
import shutil
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def _detect_bundle_dir() -> Path:
    if getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS) / "resources"
    return Path(__file__).resolve().parent.parent / "resources"


def _detect_data_dir() -> Path:
    import os

    appdata = os.environ.get("APPDATA")
    if appdata:
        d = Path(appdata) / "MSMAwakeningTracker"
    else:
        d = Path.home() / ".msm_awakening_tracker"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _setup_logging(data_dir: Path) -> None:
    log_dir = data_dir / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "msm_tracker.log"

    handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s")
    )

    root = logging.getLogger()
    root.setLevel(logging.DEBUG if "--debug" in sys.argv else logging.INFO)
    root.addHandler(handler)

    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    root.addHandler(console)


def open_content_db(db_path: Path) -> sqlite3.Connection:
    """Open (or reopen) a content.db file with standard pragmas."""
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _init_content_db(data_dir: Path, bundle_dir: Path) -> sqlite3.Connection:
    db_path = data_dir / "content.db"
    bundled = bundle_dir / "db" / "content.db"

    if not db_path.exists():
        if bundled.exists():
            shutil.copy2(bundled, db_path)
            logger.info("Copied bundled content.db to %s", db_path)
        else:
            logger.warning(
                "No bundled content.db found at %s — creating empty", bundled
            )

    return open_content_db(db_path)


def _init_userstate_db(data_dir: Path) -> sqlite3.Connection:
    db_path = data_dir / "userstate.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@dataclass
class AppContext:
    """Holds wired-up connections, paths, and service references."""

    data_dir: Path
    bundle_dir: Path
    conn_content: sqlite3.Connection
    conn_userstate: sqlite3.Connection


def bootstrap() -> AppContext:
    bundle_dir = _detect_bundle_dir()
    data_dir = _detect_data_dir()
    _setup_logging(data_dir)

    logger.info("MSM Awakening Tracker starting")
    logger.info("Bundle dir: %s", bundle_dir)
    logger.info("Data dir:   %s", data_dir)

    conn_content = _init_content_db(data_dir, bundle_dir)
    conn_userstate = _init_userstate_db(data_dir)

    from app.db.migrations import run_migrations

    run_migrations(conn_content, "content", bundle_dir=bundle_dir)
    run_migrations(conn_userstate, "userstate", bundle_dir=bundle_dir)

    _seed_userstate_defaults(conn_userstate)
    backfill_stable_keys(conn_content, conn_userstate)

    return AppContext(
        data_dir=data_dir,
        bundle_dir=bundle_dir,
        conn_content=conn_content,
        conn_userstate=conn_userstate,
    )


def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cols = conn.execute(f"PRAGMA table_info({table})").fetchall()  # noqa: S608
    return any(c[1] == column for c in cols)


def backfill_stable_keys(
    conn_content: sqlite3.Connection,
    conn_userstate: sqlite3.Connection,
) -> None:
    """Populate empty content_key / monster_key / egg_key after migration.

    Safe to call multiple times; only touches rows where the key is still
    the default empty string.
    """
    from app.domain.models import egg_content_key, monster_content_key

    # ── Content DB: backfill content_key on monsters ─────────────────
    if _has_column(conn_content, "monsters", "content_key"):
        rows = conn_content.execute(
            "SELECT id, name, monster_type FROM monsters WHERE content_key = ''"
        ).fetchall()
        if rows:
            conn_content.executemany(
                "UPDATE monsters SET content_key = ? WHERE id = ?",
                [(monster_content_key(r[2], r[1]), r[0]) for r in rows],
            )
            logger.info("Backfilled content_key for %d monster(s)", len(rows))

        # Backfill wiki_slug as source_slug stand-in (source_fingerprint stays empty for seed data).
        conn_content.execute(
            "UPDATE monsters SET source_fingerprint = '' WHERE source_fingerprint = ''"
        )

    # ── Content DB: backfill content_key on egg_types ────────────────
    if _has_column(conn_content, "egg_types", "content_key"):
        rows = conn_content.execute(
            "SELECT id, name FROM egg_types WHERE content_key = ''"
        ).fetchall()
        if rows:
            conn_content.executemany(
                "UPDATE egg_types SET content_key = ? WHERE id = ?",
                [(egg_content_key(r[1]), r[0]) for r in rows],
            )
            logger.info("Backfilled content_key for %d egg type(s)", len(rows))

    conn_content.commit()

    # ── Userstate DB: backfill monster_key on active_targets ─────────
    if not _has_column(conn_userstate, "active_targets", "monster_key"):
        return

    targets = conn_userstate.execute(
        "SELECT id, monster_id FROM active_targets WHERE monster_key = ''"
    ).fetchall()
    if targets:
        key_map: dict[int, str] = {}
        if _has_column(conn_content, "monsters", "content_key"):
            for row in conn_content.execute("SELECT id, content_key FROM monsters").fetchall():
                key_map[row[0]] = row[1]

        for tid, mid in targets:
            key = key_map.get(mid, "")
            if key:
                conn_userstate.execute(
                    "UPDATE active_targets SET monster_key = ? WHERE id = ?",
                    (key, tid),
                )
        logger.info("Backfilled monster_key for %d active target(s)", len(targets))

    # ── Userstate DB: backfill egg_key on progress rows ──────────────
    if not _has_column(conn_userstate, "target_requirement_progress", "egg_key"):
        conn_userstate.commit()
        return

    progress = conn_userstate.execute(
        "SELECT active_target_id, egg_type_id FROM target_requirement_progress WHERE egg_key = ''"
    ).fetchall()
    if progress:
        egg_key_map: dict[int, str] = {}
        if _has_column(conn_content, "egg_types", "content_key"):
            for row in conn_content.execute("SELECT id, content_key FROM egg_types").fetchall():
                egg_key_map[row[0]] = row[1]

        for atid, eid in progress:
            key = egg_key_map.get(eid, "")
            if key:
                conn_userstate.execute(
                    "UPDATE target_requirement_progress SET egg_key = ? "
                    "WHERE active_target_id = ? AND egg_type_id = ?",
                    (key, atid, eid),
                )
        logger.info("Backfilled egg_key for %d progress row(s)", len(progress))

    conn_userstate.commit()


def _seed_userstate_defaults(conn: sqlite3.Connection) -> None:
    """Insert default app_settings rows if the table exists but is empty."""
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM app_settings WHERE key='breed_list_sort_order'"
        ).fetchone()
        if row and row[0] == 0:
            conn.execute(
                "INSERT INTO app_settings(key, value) VALUES('breed_list_sort_order', 'time_desc')"
            )
            conn.commit()
            logger.info("Seeded default app_settings")
    except sqlite3.OperationalError:
        pass
