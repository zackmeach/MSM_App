"""Simple numbered-SQL migration runner for both content and userstate DBs.

Migration .sql files must NOT contain their own BEGIN/COMMIT/ROLLBACK. The
runner wraps each file in an explicit transaction so partial failures roll
back fully — an inner COMMIT would close that transaction prematurely.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_ENSURE_META = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL,
    applied_at  TEXT    NOT NULL
);
"""


def run_migrations(
    conn: sqlite3.Connection,
    db_name: str,
    *,
    bundle_dir: Path | None = None,
    migrations_dir: Path | None = None,
) -> int:
    """Apply pending .sql migrations and return the count applied.

    Looks for migration files in ``app/db/migrations/<db_name>/`` relative to
    this source file, unless *migrations_dir* is given explicitly.
    """
    if migrations_dir is None:
        migrations_dir = Path(__file__).resolve().parent / "migrations" / db_name

    conn.executescript(_ENSURE_META)

    cur = conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_migrations")
    current_version: int = cur.fetchone()[0]

    if not migrations_dir.is_dir():
        logger.debug("No migrations directory at %s — skipping", migrations_dir)
        return 0

    sql_files = sorted(migrations_dir.glob("*.sql"))
    applied = 0

    for sql_file in sql_files:
        version = int(sql_file.name.split("_", 1)[0])
        if version <= current_version:
            continue

        sql = sql_file.read_text(encoding="utf-8")
        logger.info("Applying migration %s/%s", db_name, sql_file.name)

        # Wrap the migration in an explicit transaction so partial failures
        # roll back atomically. In legacy autocommit mode each statement in
        # executescript() is committed individually, so without the leading
        # BEGIN a multi-statement migration that fails on statement N leaves
        # statements 1..N-1 persisted while the version row is never written,
        # bricking startup with "duplicate column" on the next launch.
        try:
            conn.executescript("BEGIN;\n" + sql)
            conn.execute(
                "INSERT INTO schema_migrations(version, name, applied_at) VALUES(?, ?, ?)",
                (version, sql_file.stem, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
            applied += 1
        except sqlite3.Error:
            try:
                conn.rollback()
            except sqlite3.Error:
                pass
            logger.exception("Migration %s failed — aborting", sql_file.name)
            raise

    if applied:
        logger.info("Applied %d migration(s) to %s", applied, db_name)
    return applied
