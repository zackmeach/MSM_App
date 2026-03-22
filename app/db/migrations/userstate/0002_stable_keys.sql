-- Add stable content keys to user state for durable identity across content rebuilds.

ALTER TABLE active_targets ADD COLUMN monster_key TEXT NOT NULL DEFAULT '';
ALTER TABLE target_requirement_progress ADD COLUMN egg_key TEXT NOT NULL DEFAULT '';

-- Track the last content version reconciled against user state.
INSERT OR IGNORE INTO app_settings(key, value) VALUES('last_reconciled_content_version', '');
