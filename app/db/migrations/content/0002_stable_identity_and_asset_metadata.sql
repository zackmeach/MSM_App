-- Stable content identity, provenance, asset metadata, and deprecation support.

-- Monsters: add durable identity and provenance columns.
ALTER TABLE monsters ADD COLUMN content_key TEXT NOT NULL DEFAULT '';
ALTER TABLE monsters ADD COLUMN source_fingerprint TEXT NOT NULL DEFAULT '';
ALTER TABLE monsters ADD COLUMN asset_source TEXT NOT NULL DEFAULT 'generated_placeholder';
ALTER TABLE monsters ADD COLUMN asset_sha256 TEXT NOT NULL DEFAULT '';
ALTER TABLE monsters ADD COLUMN deprecated_at_utc TEXT;
ALTER TABLE monsters ADD COLUMN deprecation_reason TEXT;

-- Egg types: add durable identity, deprecation, and provenance columns.
ALTER TABLE egg_types ADD COLUMN content_key TEXT NOT NULL DEFAULT '';
ALTER TABLE egg_types ADD COLUMN is_deprecated INTEGER NOT NULL DEFAULT 0 CHECK(is_deprecated IN (0,1));
ALTER TABLE egg_types ADD COLUMN deprecated_at_utc TEXT;
ALTER TABLE egg_types ADD COLUMN deprecation_reason TEXT;
ALTER TABLE egg_types ADD COLUMN source_fingerprint TEXT NOT NULL DEFAULT '';
ALTER TABLE egg_types ADD COLUMN asset_source TEXT NOT NULL DEFAULT 'generated_placeholder';
ALTER TABLE egg_types ADD COLUMN asset_sha256 TEXT NOT NULL DEFAULT '';

-- Alias lookup table for slug-drift and legacy-name resolution.
CREATE TABLE IF NOT EXISTS content_aliases (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL CHECK(entity_type IN ('monster','egg')),
    content_key TEXT NOT NULL,
    alias_kind  TEXT NOT NULL CHECK(alias_kind IN ('display_name','source_slug','legacy_name','legacy_slug')),
    alias_value TEXT NOT NULL,
    is_active   INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)),
    notes       TEXT,
    UNIQUE(entity_type, alias_kind, alias_value)
);

CREATE INDEX IF NOT EXISTS idx_aliases_key ON content_aliases(content_key);

-- Audit trail for pipeline-generated content changes.
CREATE TABLE IF NOT EXISTS content_audit (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    content_key     TEXT NOT NULL,
    action          TEXT NOT NULL,
    content_version TEXT NOT NULL,
    changed_at_utc  TEXT NOT NULL,
    details         TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_key ON content_audit(content_key);
CREATE INDEX IF NOT EXISTS idx_audit_version ON content_audit(content_version);

-- Extend update_metadata with pipeline-required keys.
INSERT OR IGNORE INTO update_metadata(key, value) VALUES('schema_version', '2');
INSERT OR IGNORE INTO update_metadata(key, value) VALUES('artifact_contract_version', '1.1');
INSERT OR IGNORE INTO update_metadata(key, value) VALUES('build_id', '');
INSERT OR IGNORE INTO update_metadata(key, value) VALUES('git_sha', '');
