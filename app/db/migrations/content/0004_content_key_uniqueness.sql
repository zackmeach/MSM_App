-- Enforce content_key uniqueness via partial unique indexes.
--
-- content_key is the slug-based stable identity for monsters and eggs
-- (e.g. monster:wublin:zynth, egg:noggin). Migration 0002 introduced the
-- columns as NOT NULL DEFAULT '', so "missing" and "valid empty" are
-- indistinguishable at the column level. Without uniqueness, a content
-- rebuild that produced two rows with the same key would silently
-- corrupt user-state lookups (fetch_monster_by_key would resolve to
-- whichever row SQLite returned first).
--
-- We use partial unique indexes (WHERE content_key != '') so that:
--   1. populated keys are guaranteed unique, AND
--   2. multiple empty placeholders can still coexist before the
--      launch-time backfill in app/bootstrap.py runs.
--
-- This migration must NOT contain BEGIN/COMMIT — the runner wraps each
-- .sql in a transaction (W0.5).

CREATE UNIQUE INDEX IF NOT EXISTS uq_monsters_content_key ON monsters(content_key) WHERE content_key != '';
CREATE UNIQUE INDEX IF NOT EXISTS uq_egg_types_content_key ON egg_types(content_key) WHERE content_key != '';
