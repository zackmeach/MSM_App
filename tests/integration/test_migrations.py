"""Tests for the migration runner."""

from __future__ import annotations

import sqlite3

from app.db.migrations import run_migrations


class TestMigrationRunner:
    def test_content_migrations_apply(self, content_conn):
        row = content_conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
        assert row[0] is not None and row[0] >= 1

    def test_userstate_migrations_apply(self, userstate_conn):
        row = userstate_conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
        assert row[0] is not None and row[0] >= 1

    def test_idempotent_rerun(self, content_conn):
        applied = run_migrations(content_conn, "content")
        assert applied == 0

    def test_fresh_db_reaches_current(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("PRAGMA foreign_keys=ON")
        applied = run_migrations(conn, "content")
        assert applied >= 1

        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        assert "monsters" in tables
        assert "egg_types" in tables
        assert "monster_requirements" in tables
        assert "update_metadata" in tables
