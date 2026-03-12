-- content.db initial schema

CREATE TABLE IF NOT EXISTS monsters (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL UNIQUE,
    monster_type    TEXT    NOT NULL CHECK(monster_type IN ('wublin','celestial','amber')),
    image_path      TEXT    NOT NULL DEFAULT '',
    is_placeholder  INTEGER NOT NULL DEFAULT 1 CHECK(is_placeholder IN (0,1)),
    wiki_slug       TEXT    NOT NULL DEFAULT '',
    is_deprecated   INTEGER NOT NULL DEFAULT 0 CHECK(is_deprecated IN (0,1))
);

CREATE INDEX IF NOT EXISTS idx_monsters_type ON monsters(monster_type);
CREATE INDEX IF NOT EXISTS idx_monsters_deprecated ON monsters(is_deprecated);

CREATE TABLE IF NOT EXISTS egg_types (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    name                    TEXT    NOT NULL UNIQUE,
    breeding_time_seconds   INTEGER NOT NULL CHECK(breeding_time_seconds > 0),
    breeding_time_display   TEXT    NOT NULL,
    egg_image_path          TEXT    NOT NULL DEFAULT '',
    is_placeholder          INTEGER NOT NULL DEFAULT 1 CHECK(is_placeholder IN (0,1))
);

CREATE INDEX IF NOT EXISTS idx_egg_types_breeding_time ON egg_types(breeding_time_seconds);

CREATE TABLE IF NOT EXISTS monster_requirements (
    monster_id      INTEGER NOT NULL REFERENCES monsters(id) ON DELETE CASCADE,
    egg_type_id     INTEGER NOT NULL REFERENCES egg_types(id) ON DELETE RESTRICT,
    quantity        INTEGER NOT NULL CHECK(quantity >= 1),
    PRIMARY KEY (monster_id, egg_type_id)
);

CREATE INDEX IF NOT EXISTS idx_req_monster ON monster_requirements(monster_id);
CREATE INDEX IF NOT EXISTS idx_req_egg_type ON monster_requirements(egg_type_id);

CREATE TABLE IF NOT EXISTS update_metadata (
    key     TEXT PRIMARY KEY,
    value   TEXT NOT NULL
);

INSERT OR IGNORE INTO update_metadata(key, value) VALUES('content_version', '0.1.0-dev');
INSERT OR IGNORE INTO update_metadata(key, value) VALUES('last_updated_utc', '2025-01-01T00:00:00Z');
INSERT OR IGNORE INTO update_metadata(key, value) VALUES('source', 'seed');
