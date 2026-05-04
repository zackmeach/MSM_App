"""Tests for schema migrations and stable-key backfill logic."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.db.migrations import run_migrations
from app.bootstrap import backfill_stable_keys
from app.domain.models import monster_content_key, egg_content_key, canonical_slug
from app.repositories import monster_repo, target_repo


MIGRATIONS_ROOT = Path(__file__).resolve().parent.parent.parent / "app" / "db" / "migrations"


# ── Helpers ──────────────────────────────────────────────────────────


def _make_content_db() -> sqlite3.Connection:
    """Create an in-memory content DB with all migrations applied."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    run_migrations(conn, "content", migrations_dir=MIGRATIONS_ROOT / "content")
    return conn


def _make_userstate_db() -> sqlite3.Connection:
    """Create an in-memory userstate DB with all migrations applied."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    run_migrations(conn, "userstate", migrations_dir=MIGRATIONS_ROOT / "userstate")
    return conn


def _make_content_db_v1_only() -> sqlite3.Connection:
    """Create content DB with only migration 0001 (pre-stable-keys)."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(
        "CREATE TABLE IF NOT EXISTS schema_migrations "
        "(version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL);"
    )
    v1_sql = (MIGRATIONS_ROOT / "content" / "0001_initial_schema.sql").read_text("utf-8")
    conn.executescript(v1_sql)
    conn.execute(
        "INSERT INTO schema_migrations(version, name, applied_at) VALUES(1, '0001_initial_schema', '2025-01-01')"
    )
    conn.commit()
    return conn


def _make_userstate_db_v1_only() -> sqlite3.Connection:
    """Create userstate DB with only migration 0001."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(
        "CREATE TABLE IF NOT EXISTS schema_migrations "
        "(version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL);"
    )
    v1_sql = (MIGRATIONS_ROOT / "userstate" / "0001_initial_schema.sql").read_text("utf-8")
    conn.executescript(v1_sql)
    conn.execute(
        "INSERT INTO schema_migrations(version, name, applied_at) VALUES(1, '0001_initial_schema', '2025-01-01')"
    )
    conn.commit()
    return conn


def _seed_monster(conn: sqlite3.Connection, name: str, mtype: str, *, content_key: str = "") -> int:
    cur = conn.execute(
        "INSERT INTO monsters(name, monster_type, image_path, wiki_slug, is_placeholder, content_key) "
        "VALUES(?, ?, ?, ?, 1, ?)",
        (name, mtype, f"images/monsters/{canonical_slug(name)}.png", name, content_key),
    )
    conn.commit()
    return cur.lastrowid


def _seed_egg(conn: sqlite3.Connection, name: str, *, content_key: str = "") -> int:
    cur = conn.execute(
        "INSERT INTO egg_types(name, breeding_time_seconds, breeding_time_display, egg_image_path, is_placeholder, content_key) "
        "VALUES(?, 5, '5s', ?, 1, ?)",
        (name, f"images/eggs/{canonical_slug(name)}_egg.png", content_key),
    )
    conn.commit()
    return cur.lastrowid


# ── canonical_slug tests ─────────────────────────────────────────────


class TestCanonicalSlug:
    def test_simple_lowercase(self):
        assert canonical_slug("Zynth") == "zynth"

    def test_spaces_to_hyphens(self):
        assert canonical_slug("Toe Jammer") == "toe-jammer"

    def test_strips_punctuation(self):
        assert canonical_slug("BonaPetite") == "bonapetite"

    def test_no_consecutive_hyphens(self):
        assert canonical_slug("Foo  Bar") == "foo-bar"

    def test_strips_leading_trailing(self):
        assert canonical_slug(" -Monster- ") == "monster"

    def test_mixed_case_and_numbers(self):
        assert canonical_slug("T-Rox") == "t-rox"


class TestContentKeyGeneration:
    def test_monster_key(self):
        assert monster_content_key("wublin", "Zynth") == "monster:wublin:zynth"

    def test_monster_key_amber(self):
        assert monster_content_key("amber", "Kayna") == "monster:amber:kayna"

    def test_egg_key_simple(self):
        assert egg_content_key("Noggin") == "egg:noggin"

    def test_egg_key_with_space(self):
        assert egg_content_key("Toe Jammer") == "egg:toe-jammer"


# ── Content DB migration tests ───────────────────────────────────────


class TestContentMigrations:
    def test_v2_adds_content_key_to_monsters(self):
        conn = _make_content_db()
        cols = {r[1] for r in conn.execute("PRAGMA table_info(monsters)").fetchall()}
        assert "content_key" in cols
        assert "source_fingerprint" in cols
        assert "asset_source" in cols
        assert "asset_sha256" in cols
        assert "deprecated_at_utc" in cols
        assert "deprecation_reason" in cols

    def test_v2_adds_content_key_to_egg_types(self):
        conn = _make_content_db()
        cols = {r[1] for r in conn.execute("PRAGMA table_info(egg_types)").fetchall()}
        assert "content_key" in cols
        assert "is_deprecated" in cols
        assert "deprecated_at_utc" in cols
        assert "deprecation_reason" in cols
        assert "source_fingerprint" in cols
        assert "asset_source" in cols
        assert "asset_sha256" in cols

    def test_v2_creates_content_aliases(self):
        conn = _make_content_db()
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert "content_aliases" in tables

    def test_v2_creates_content_audit(self):
        conn = _make_content_db()
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert "content_audit" in tables

    def test_v2_adds_metadata_keys(self):
        conn = _make_content_db()
        meta = {r[0]: r[1] for r in conn.execute("SELECT key, value FROM update_metadata").fetchall()}
        assert "schema_version" in meta
        assert meta["schema_version"] == "2"
        assert "artifact_contract_version" in meta
        assert "build_id" in meta
        assert "git_sha" in meta

    def test_schema_migrations_records_latest(self):
        conn = _make_content_db()
        row = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
        # Latest migration: 0003 added the egg_type_elements table.
        assert row[0] == 3

    def test_v3_adds_egg_type_elements_table(self):
        conn = _make_content_db()
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert "egg_type_elements" in tables
        # Confirm columns are as expected.
        cols = {r[1] for r in conn.execute("PRAGMA table_info(egg_type_elements)").fetchall()}
        assert {"egg_type_id", "element_key", "position"} <= cols

    def test_upgrade_from_v1(self):
        """Upgrading a v1 DB with existing data preserves rows."""
        conn = _make_content_db_v1_only()
        conn.execute(
            "INSERT INTO monsters(name, monster_type, image_path, wiki_slug, is_placeholder) "
            "VALUES('TestMon', 'wublin', 'img.png', 'TestMon', 1)"
        )
        conn.commit()

        run_migrations(conn, "content", migrations_dir=MIGRATIONS_ROOT / "content")

        row = conn.execute("SELECT content_key FROM monsters WHERE name='TestMon'").fetchone()
        assert row is not None
        assert row[0] == ""  # backfill hasn't run yet, just migration


# ── Userstate DB migration tests ─────────────────────────────────────


class TestUserstateMigrations:
    def test_v2_adds_monster_key(self):
        conn = _make_userstate_db()
        cols = {r[1] for r in conn.execute("PRAGMA table_info(active_targets)").fetchall()}
        assert "monster_key" in cols

    def test_v2_adds_egg_key(self):
        conn = _make_userstate_db()
        cols = {r[1] for r in conn.execute("PRAGMA table_info(target_requirement_progress)").fetchall()}
        assert "egg_key" in cols

    def test_v2_adds_reconciliation_setting(self):
        conn = _make_userstate_db()
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key='last_reconciled_content_version'"
        ).fetchone()
        assert row is not None
        assert row[0] == ""

    def test_upgrade_from_v1_preserves_targets(self):
        conn = _make_userstate_db_v1_only()
        conn.execute(
            "INSERT INTO active_targets(monster_id, added_at) VALUES(1, '2025-01-01T00:00:00Z')"
        )
        conn.commit()

        run_migrations(conn, "userstate", migrations_dir=MIGRATIONS_ROOT / "userstate")

        row = conn.execute("SELECT monster_key FROM active_targets WHERE monster_id=1").fetchone()
        assert row is not None
        assert row[0] == ""  # backfill hasn't run yet


# ── Backfill tests ───────────────────────────────────────────────────


class TestBackfillStableKeys:
    def test_backfill_monsters(self):
        conn = _make_content_db()
        us = _make_userstate_db()

        _seed_monster(conn, "Zynth", "wublin")
        _seed_monster(conn, "Galvana", "celestial")

        backfill_stable_keys(conn, us)

        keys = [r[0] for r in conn.execute("SELECT content_key FROM monsters ORDER BY id").fetchall()]
        assert keys == ["monster:wublin:zynth", "monster:celestial:galvana"]

    def test_backfill_eggs(self):
        conn = _make_content_db()
        us = _make_userstate_db()

        _seed_egg(conn, "Noggin")
        _seed_egg(conn, "Toe Jammer")

        backfill_stable_keys(conn, us)

        keys = [r[0] for r in conn.execute("SELECT content_key FROM egg_types ORDER BY id").fetchall()]
        assert keys == ["egg:noggin", "egg:toe-jammer"]

    def test_backfill_userstate_keys(self):
        conn = _make_content_db()
        us = _make_userstate_db()

        mid = _seed_monster(conn, "Zynth", "wublin")
        eid = _seed_egg(conn, "Noggin")
        conn.execute(
            "INSERT INTO monster_requirements(monster_id, egg_type_id, quantity) VALUES(?, ?, 3)",
            (mid, eid),
        )
        conn.commit()

        backfill_stable_keys(conn, us)

        us.execute(
            "INSERT INTO active_targets(monster_id, added_at, monster_key) VALUES(?, '2025-01-01', '')",
            (mid,),
        )
        us.execute(
            "INSERT INTO target_requirement_progress(active_target_id, egg_type_id, required_count, satisfied_count, egg_key) "
            "VALUES(1, ?, 3, 0, '')",
            (eid,),
        )
        us.commit()

        backfill_stable_keys(conn, us)

        target = us.execute("SELECT monster_key FROM active_targets WHERE id=1").fetchone()
        assert target[0] == "monster:wublin:zynth"

        progress = us.execute("SELECT egg_key FROM target_requirement_progress WHERE active_target_id=1").fetchone()
        assert progress[0] == "egg:noggin"

    def test_backfill_idempotent(self):
        conn = _make_content_db()
        us = _make_userstate_db()

        _seed_monster(conn, "Brump", "wublin")

        backfill_stable_keys(conn, us)
        backfill_stable_keys(conn, us)

        keys = [r[0] for r in conn.execute("SELECT content_key FROM monsters").fetchall()]
        assert keys == ["monster:wublin:brump"]

    def test_backfill_skips_already_keyed_rows(self):
        conn = _make_content_db()
        us = _make_userstate_db()

        _seed_monster(conn, "Zynth", "wublin", content_key="monster:wublin:zynth")

        backfill_stable_keys(conn, us)

        row = conn.execute("SELECT content_key FROM monsters WHERE name='Zynth'").fetchone()
        assert row[0] == "monster:wublin:zynth"

    def test_backfill_with_mixed_schemas(self):
        """Old userstate (v1, no monster_key column) + new content (v2)."""
        conn = _make_content_db()
        us = _make_userstate_db_v1_only()

        _seed_monster(conn, "Zynth", "wublin")

        # Should not crash even though userstate doesn't have monster_key col
        backfill_stable_keys(conn, us)

        keys = [r[0] for r in conn.execute("SELECT content_key FROM monsters").fetchall()]
        assert keys == ["monster:wublin:zynth"]


# ── Repository model tests (v2 fields) ──────────────────────────────


class TestRepositoryV2Fields:
    def test_monster_has_content_key(self):
        conn = _make_content_db()
        _seed_monster(conn, "Zynth", "wublin", content_key="monster:wublin:zynth")
        m = monster_repo.fetch_monster_by_id(conn, 1)
        assert m is not None
        assert m.content_key == "monster:wublin:zynth"
        assert m.asset_source == "generated_placeholder"

    def test_monster_by_key(self):
        conn = _make_content_db()
        _seed_monster(conn, "Brump", "wublin", content_key="monster:wublin:brump")
        m = monster_repo.fetch_monster_by_key(conn, "monster:wublin:brump")
        assert m is not None
        assert m.name == "Brump"

    def test_egg_has_content_key(self):
        conn = _make_content_db()
        _seed_egg(conn, "Noggin", content_key="egg:noggin")
        eggs = monster_repo.fetch_all_egg_types(conn)
        assert len(eggs) == 1
        assert eggs[0].content_key == "egg:noggin"

    def test_egg_by_key(self):
        conn = _make_content_db()
        _seed_egg(conn, "Mammott", content_key="egg:mammott")
        e = monster_repo.fetch_egg_type_by_key(conn, "egg:mammott")
        assert e is not None
        assert e.name == "Mammott"

    def test_target_has_monster_key(self):
        us = _make_userstate_db()
        tid = target_repo.insert_target(us, 1, monster_key="monster:wublin:zynth")
        us.commit()
        t = target_repo.fetch_target_by_id(us, tid)
        assert t is not None
        assert t.monster_key == "monster:wublin:zynth"

    def test_progress_has_egg_key(self):
        from app.domain.models import MonsterRequirement
        us = _make_userstate_db()
        tid = target_repo.insert_target(us, 1, monster_key="monster:wublin:zynth")
        reqs = [MonsterRequirement(monster_id=1, egg_type_id=1, quantity=3)]
        target_repo.materialize_progress(us, tid, reqs, egg_keys={1: "egg:noggin"})
        us.commit()
        progress = target_repo.fetch_all_progress(us)
        assert len(progress) == 1
        assert progress[0].egg_key == "egg:noggin"

    def test_delete_restore_preserves_keys(self):
        from app.domain.models import MonsterRequirement
        us = _make_userstate_db()
        tid = target_repo.insert_target(us, 1, monster_key="monster:wublin:zynth")
        reqs = [MonsterRequirement(monster_id=1, egg_type_id=1, quantity=3)]
        target_repo.materialize_progress(us, tid, reqs, egg_keys={1: "egg:noggin"})
        us.commit()

        snapshot = target_repo.delete_progress_for_target(us, tid)
        assert snapshot[0].egg_key == "egg:noggin"

        target_repo.restore_progress_rows(us, snapshot)
        us.commit()
        progress = target_repo.fetch_all_progress(us)
        assert progress[0].egg_key == "egg:noggin"


# ── Startup with both old and new DBs ───────────────────────────────


class TestMigrationAtomicity:
    """Verify migrations apply atomically — partial failure rolls back fully."""

    def test_partial_migration_failure_rolls_back(self, tmp_path):
        """A migration that fails midway must NOT leave partial DDL behind.

        Without atomicity, sqlite3.Connection.executescript() commits each
        statement individually, so a multi-statement migration that fails on
        statement N persists statements 1..N-1 but never inserts the version
        row. The next launch re-runs the whole file and aborts on
        'duplicate column'. This test makes that regression visible.
        """
        conn = _make_content_db_v1_only()

        migrations_dir = tmp_path / "broken_migrations"
        migrations_dir.mkdir()
        # First statement is valid; the second references a missing table.
        # If the migration is atomic, neither persists.
        (migrations_dir / "0002_partial_failure.sql").write_text(
            "ALTER TABLE monsters ADD COLUMN partial_marker TEXT;\n"
            "ALTER TABLE nonexistent_table ADD COLUMN never_runs TEXT;\n",
            encoding="utf-8",
        )

        with pytest.raises(sqlite3.OperationalError):
            run_migrations(conn, "content", migrations_dir=migrations_dir)

        cols = {r[1] for r in conn.execute("PRAGMA table_info(monsters)").fetchall()}
        assert "partial_marker" not in cols, (
            "Migration applied non-atomically: the first ALTER persisted "
            "after a later statement failed. Re-running the migration will "
            "abort with 'duplicate column'."
        )

        max_version = conn.execute(
            "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
        ).fetchone()[0]
        assert max_version == 1, "Failed migration must not be recorded as applied"

    def test_atomic_migration_can_be_retried_after_failure(self, tmp_path):
        """After a rolled-back failed migration, a fixed version applies cleanly.

        This is the practical user-facing benefit: a release with a buggy
        migration doesn't brick the install — fixing the migration and
        relaunching just works.
        """
        conn = _make_content_db_v1_only()

        broken_dir = tmp_path / "broken"
        broken_dir.mkdir()
        (broken_dir / "0002_broken.sql").write_text(
            "ALTER TABLE monsters ADD COLUMN good_col TEXT;\n"
            "ALTER TABLE missing_table ADD COLUMN bad_col TEXT;\n",
            encoding="utf-8",
        )

        with pytest.raises(sqlite3.OperationalError):
            run_migrations(conn, "content", migrations_dir=broken_dir)

        # Operator ships a fix in 0002_fixed.sql.
        fixed_dir = tmp_path / "fixed"
        fixed_dir.mkdir()
        (fixed_dir / "0002_fixed.sql").write_text(
            "ALTER TABLE monsters ADD COLUMN good_col TEXT;\n",
            encoding="utf-8",
        )

        applied = run_migrations(conn, "content", migrations_dir=fixed_dir)
        assert applied == 1

        cols = {r[1] for r in conn.execute("PRAGMA table_info(monsters)").fetchall()}
        assert "good_col" in cols


class TestMixedSchemaStartup:
    def test_old_content_new_userstate(self):
        """Old content v1, new userstate v2 -- backfill can't populate keys but doesn't crash."""
        content = _make_content_db_v1_only()
        content.execute(
            "INSERT INTO monsters(name, monster_type, image_path, wiki_slug, is_placeholder) "
            "VALUES('Zynth', 'wublin', 'img.png', 'Zynth', 1)"
        )
        content.commit()

        userstate = _make_userstate_db()
        userstate.execute(
            "INSERT INTO active_targets(monster_id, added_at, monster_key) VALUES(1, '2025-01-01', '')"
        )
        userstate.commit()

        backfill_stable_keys(content, userstate)

        row = userstate.execute("SELECT monster_key FROM active_targets WHERE id=1").fetchone()
        assert row[0] == ""  # can't backfill without content_key column

    def test_new_content_old_userstate(self):
        """New content v2, old userstate v1 -- content keys backfill, userstate left alone."""
        content = _make_content_db()
        _seed_monster(content, "Zynth", "wublin")

        userstate = _make_userstate_db_v1_only()
        userstate.execute(
            "INSERT INTO active_targets(monster_id, added_at) VALUES(1, '2025-01-01')"
        )
        userstate.commit()

        backfill_stable_keys(content, userstate)

        row = content.execute("SELECT content_key FROM monsters WHERE name='Zynth'").fetchone()
        assert row[0] == "monster:wublin:zynth"
