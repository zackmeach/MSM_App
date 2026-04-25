-- Per-egg element associations for displaying element sigils on Breed List rows.
-- Each row links one egg type to one element key, with `position` preserving
-- the canonical display order (e.g. Plant first, then Cold for Furcorn).

CREATE TABLE IF NOT EXISTS egg_type_elements (
    egg_type_id INTEGER NOT NULL,
    element_key TEXT    NOT NULL,
    position    INTEGER NOT NULL,
    PRIMARY KEY (egg_type_id, position),
    FOREIGN KEY (egg_type_id) REFERENCES egg_types(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_egg_type_elements_egg ON egg_type_elements(egg_type_id);
