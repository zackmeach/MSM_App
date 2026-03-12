-- userstate.db initial schema (satisfaction-aware model)

CREATE TABLE IF NOT EXISTS active_targets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    monster_id  INTEGER NOT NULL,
    added_at    TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_active_targets_monster ON active_targets(monster_id);
CREATE INDEX IF NOT EXISTS idx_active_targets_added ON active_targets(added_at);

CREATE TABLE IF NOT EXISTS target_requirement_progress (
    active_target_id    INTEGER NOT NULL REFERENCES active_targets(id) ON DELETE CASCADE,
    egg_type_id         INTEGER NOT NULL,
    required_count      INTEGER NOT NULL CHECK(required_count >= 1),
    satisfied_count     INTEGER NOT NULL DEFAULT 0 CHECK(satisfied_count >= 0),
    PRIMARY KEY (active_target_id, egg_type_id)
);

CREATE INDEX IF NOT EXISTS idx_trp_egg ON target_requirement_progress(egg_type_id);

CREATE TABLE IF NOT EXISTS app_settings (
    key     TEXT PRIMARY KEY,
    value   TEXT NOT NULL
);

INSERT OR IGNORE INTO app_settings(key, value) VALUES('breed_list_sort_order', 'time_desc');
