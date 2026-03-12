"""Release content seed — populates resources/db/content.db with complete game data.

Covers all 19 regular Wublins, all 12 regular Celestials, and the
always-available Amber Vessel (Kayna). Additional Amber Vessels can be
added via the in-app update mechanism.

Run:  python scripts/seed_content_db.py
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.db.migrations import run_migrations  # noqa: E402

DB_PATH = ROOT / "resources" / "db" / "content.db"

# ── Egg Types ────────────────────────────────────────────────────────
# (name, breeding_time_seconds, breeding_time_display, egg_image_path)
# Times are standard (non-enhanced) breeding times from the game.

EGG_TYPES = [
    # Single Elements
    ("Noggin",       5,     "5s",      "images/eggs/noggin_egg.png"),
    ("Mammott",      5,     "5s",      "images/eggs/mammott_egg.png"),
    ("Toe Jammer",   5,     "5s",      "images/eggs/toejammer_egg.png"),
    ("Potbelly",     5,     "5s",      "images/eggs/potbelly_egg.png"),
    ("Tweedle",      5,     "5s",      "images/eggs/tweedle_egg.png"),
    # Double Elements
    ("Drumpler",     1800,  "30m",     "images/eggs/drumpler_egg.png"),
    ("Fwog",         1800,  "30m",     "images/eggs/fwog_egg.png"),
    ("Maw",          1800,  "30m",     "images/eggs/maw_egg.png"),
    ("Shrubb",       1800,  "30m",     "images/eggs/shrubb_egg.png"),
    ("Furcorn",      5400,  "1h 30m",  "images/eggs/furcorn_egg.png"),
    ("Pango",        7200,  "2h",      "images/eggs/pango_egg.png"),
    ("Oaktopus",     7200,  "2h",      "images/eggs/oaktopus_egg.png"),
    # Triple Elements
    ("Cybop",        28800, "8h",      "images/eggs/cybop_egg.png"),
    ("Quibble",      28800, "8h",      "images/eggs/quibble_egg.png"),
    ("Dandidoo",     28800, "8h",      "images/eggs/dandidoo_egg.png"),
    ("Scups",        28800, "8h",      "images/eggs/scups_egg.png"),
    ("Reedling",     28800, "8h",      "images/eggs/reedling_egg.png"),
    ("T-Rox",        28800, "8h",      "images/eggs/trox_egg.png"),
    ("Pummel",       28800, "8h",      "images/eggs/pummel_egg.png"),
    ("Congle",       28800, "8h",      "images/eggs/congle_egg.png"),
    ("Spunge",       28800, "8h",      "images/eggs/spunge_egg.png"),
    ("Bowgart",      30600, "8h 30m",  "images/eggs/bowgart_egg.png"),
    ("Clamble",      28800, "8h",      "images/eggs/clamble_egg.png"),
    ("PomPom",       28800, "8h",      "images/eggs/pompom_egg.png"),
    ("Thumpies",     27000, "7h 30m",  "images/eggs/thumpies_egg.png"),
    # Quad Elements
    ("Entbrat",      86400, "24h",     "images/eggs/entbrat_egg.png"),
    ("Deedge",       86400, "24h",     "images/eggs/deedge_egg.png"),
    ("Shellbeat",    86400, "24h",     "images/eggs/shellbeat_egg.png"),
    ("Quarrister",   86400, "24h",     "images/eggs/quarrister_egg.png"),
    ("Riff",         86400, "24h",     "images/eggs/riff_egg.png"),
    # Fire / Amber (used by Furnoss, Galvana, and Amber Vessel requirements)
    ("Kayna",        25200, "7h",      "images/eggs/kayna_egg.png"),
    ("Glowl",        36000, "10h",     "images/eggs/glowl_egg.png"),
    ("Flowah",       36000, "10h",     "images/eggs/flowah_egg.png"),
    ("Stogg",        36000, "10h",     "images/eggs/stogg_egg.png"),
    ("Floogull",     72000, "20h",     "images/eggs/floogull_egg.png"),
    ("Barrb",        72000, "20h",     "images/eggs/barrb_egg.png"),
    ("Repatillo",    72000, "20h",     "images/eggs/repatillo_egg.png"),
    ("Tring",       144000, "1d 16h",  "images/eggs/tring_egg.png"),
]

# ── Monsters ─────────────────────────────────────────────────────────
# (name, monster_type, image_path, wiki_slug)

MONSTERS = [
    # Wublins (19)
    ("Zynth",        "wublin",    "images/monsters/zynth.png",        "Zynth"),
    ("Brump",        "wublin",    "images/monsters/brump.png",        "Brump"),
    ("Thwok",        "wublin",    "images/monsters/thwok.png",        "Thwok"),
    ("Poewk",        "wublin",    "images/monsters/poewk.png",        "Poewk"),
    ("Zuuker",       "wublin",    "images/monsters/zuuker.png",       "Zuuker"),
    ("Tympa",        "wublin",    "images/monsters/tympa.png",        "Tympa"),
    ("Screemu",      "wublin",    "images/monsters/screemu.png",      "Screemu"),
    ("Dermit",       "wublin",    "images/monsters/dermit.png",       "Dermit"),
    ("Gheegur",      "wublin",    "images/monsters/gheegur.png",      "Gheegur"),
    ("Maulch",       "wublin",    "images/monsters/maulch.png",       "Maulch"),
    ("Fleechwurm",   "wublin",    "images/monsters/fleechwurm.png",   "Fleechwurm"),
    ("Astropod",     "wublin",    "images/monsters/astropod.png",     "Astropod"),
    ("Blipsqueak",   "wublin",    "images/monsters/blipsqueak.png",   "Blipsqueak"),
    ("Scargo",       "wublin",    "images/monsters/scargo.png",       "Scargo"),
    ("BonaPetite",   "wublin",    "images/monsters/bonapetite.png",   "BonaPetite"),
    ("Creepuscule",  "wublin",    "images/monsters/creepuscule.png",  "Creepuscule"),
    ("Whajje",       "wublin",    "images/monsters/whajje.png",       "Whajje"),
    ("Dwumrohl",     "wublin",    "images/monsters/dwumrohl.png",     "Dwumrohl"),
    ("Pixolotl",     "wublin",    "images/monsters/pixolotl.png",     "Pixolotl"),
    # Celestials (12)
    ("Hornacle",     "celestial", "images/monsters/hornacle.png",     "Hornacle"),
    ("Furnoss",      "celestial", "images/monsters/furnoss.png",      "Furnoss"),
    ("Glaishur",     "celestial", "images/monsters/glaishur.png",     "Glaishur"),
    ("Blasoom",      "celestial", "images/monsters/blasoom.png",      "Blasoom"),
    ("Syncopite",    "celestial", "images/monsters/syncopite.png",    "Syncopite"),
    ("Vhamp",        "celestial", "images/monsters/vhamp.png",        "Vhamp"),
    ("Galvana",      "celestial", "images/monsters/galvana.png",      "Galvana"),
    ("Scaratar",     "celestial", "images/monsters/scaratar.png",     "Scaratar"),
    ("Loodvigg",     "celestial", "images/monsters/loodvigg.png",     "Loodvigg"),
    ("Torrt",        "celestial", "images/monsters/torrt.png",        "Torrt"),
    ("Plixie",       "celestial", "images/monsters/plixie.png",       "Plixie"),
    ("Attmoz",       "celestial", "images/monsters/attmoz.png",       "Attmoz"),
    # Amber Vessels (always-available)
    ("Kayna",        "amber",     "images/monsters/kayna.png",        "Kayna"),
]

# ── Requirements ─────────────────────────────────────────────────────
# { monster_name: [(egg_name, quantity), ...] }
# Sources: lalaland.co.za (Wublins), msmpokegamer.com (Celestials, Amber)

REQUIREMENTS: dict[str, list[tuple[str, int]]] = {
    # ── Wublins ──────────────────────────────────────────────────────
    "Zynth": [
        ("Congle", 1), ("Drumpler", 1), ("Maw", 1),
        ("Oaktopus", 1), ("Pango", 1), ("T-Rox", 1),
    ],
    "Brump": [
        ("Furcorn", 6), ("Fwog", 2),
    ],
    "Thwok": [
        ("Bowgart", 4), ("Deedge", 1), ("Entbrat", 1), ("Furcorn", 4),
        ("PomPom", 4), ("Quarrister", 1), ("Quibble", 4), ("Riff", 1),
        ("Shellbeat", 1), ("Spunge", 4),
    ],
    "Poewk": [
        ("Clamble", 2), ("Dandidoo", 2), ("Oaktopus", 1), ("Pango", 1),
        ("PomPom", 1), ("Reedling", 1), ("Scups", 1), ("Shellbeat", 1),
        ("Shrubb", 1),
    ],
    "Zuuker": [
        ("Bowgart", 4), ("Deedge", 2), ("Entbrat", 2), ("Furcorn", 6),
        ("Fwog", 4), ("Oaktopus", 6), ("T-Rox", 6),
    ],
    "Tympa": [
        ("Clamble", 12), ("Drumpler", 24), ("Pummel", 12),
        ("Shellbeat", 8), ("T-Rox", 12),
    ],
    "Screemu": [
        ("Quibble", 6), ("Shellbeat", 2), ("Shrubb", 6), ("Spunge", 6),
    ],
    "Dermit": [
        ("Entbrat", 3), ("Fwog", 12), ("Quarrister", 3),
        ("Scups", 4), ("Thumpies", 4),
    ],
    "Gheegur": [
        ("Cybop", 6), ("PomPom", 4), ("Reedling", 6),
        ("Riff", 6), ("Scups", 4),
    ],
    "Maulch": [
        ("Clamble", 4), ("Entbrat", 4), ("Furcorn", 8), ("Noggin", 6),
        ("Pummel", 6), ("Quarrister", 4), ("Spunge", 6),
    ],
    "Fleechwurm": [
        ("Dandidoo", 4), ("Furcorn", 4), ("Pummel", 4), ("Quarrister", 3),
        ("Reedling", 3), ("Shellbeat", 3), ("Spunge", 3),
    ],
    "Astropod": [
        ("Deedge", 5), ("Reedling", 8), ("Scups", 8),
        ("Shellbeat", 5), ("Spunge", 6), ("Toe Jammer", 10),
    ],
    "Blipsqueak": [
        ("Cybop", 6), ("Deedge", 4), ("PomPom", 4),
        ("T-Rox", 6), ("Toe Jammer", 4),
    ],
    "Scargo": [
        ("Clamble", 3), ("Dandidoo", 3), ("Pummel", 2),
        ("Shellbeat", 3), ("Shrubb", 3), ("Spunge", 2),
    ],
    "BonaPetite": [
        ("Bowgart", 6), ("Drumpler", 10), ("Entbrat", 5), ("Fwog", 10),
        ("Mammott", 10), ("Maw", 10), ("PomPom", 6), ("Riff", 5),
        ("T-Rox", 6),
    ],
    "Creepuscule": [
        ("Congle", 8), ("Deedge", 5), ("Noggin", 12), ("Pummel", 6),
        ("Quibble", 10), ("Shellbeat", 5), ("T-Rox", 6),
    ],
    "Whajje": [
        ("Cybop", 10), ("Dandidoo", 10), ("Deedge", 7),
        ("Reedling", 10), ("Tweedle", 6),
    ],
    "Dwumrohl": [
        ("Bowgart", 4), ("Congle", 4), ("Deedge", 3), ("Entbrat", 3),
        ("Mammott", 8), ("Noggin", 8), ("PomPom", 4), ("Potbelly", 4),
        ("Pummel", 4), ("Quarrister", 3), ("Reedling", 4), ("Riff", 3),
        ("Scups", 2), ("Shellbeat", 3), ("Thumpies", 2),
        ("Toe Jammer", 8), ("Tweedle", 4),
    ],
    "Pixolotl": [
        ("Cybop", 14), ("Entbrat", 6), ("Fwog", 10), ("Pummel", 8),
        ("Riff", 6), ("Scups", 10), ("T-Rox", 8),
    ],
    # ── Celestials ───────────────────────────────────────────────────
    "Hornacle": [
        ("Toe Jammer", 50), ("Fwog", 15), ("Oaktopus", 12), ("Maw", 9),
        ("Quibble", 8), ("Pummel", 5), ("Bowgart", 4), ("Scups", 4),
        ("Spunge", 3), ("Congle", 3), ("Shellbeat", 3), ("T-Rox", 2),
    ],
    "Furnoss": [
        ("Noggin", 25), ("Potbelly", 10), ("Tweedle", 5), ("Kayna", 15),
        ("Glowl", 7), ("Flowah", 5), ("Stogg", 5), ("Cybop", 2),
        ("Shrubb", 3), ("Repatillo", 3), ("Floogull", 4), ("Barrb", 3),
        ("Dandidoo", 2), ("Reedling", 3), ("Tring", 2),
    ],
    "Glaishur": [
        ("Mammott", 40), ("Bowgart", 8), ("Deedge", 4), ("Furcorn", 10),
        ("Congle", 2), ("Drumpler", 7), ("Maw", 5), ("T-Rox", 2),
        ("Thumpies", 2), ("Pango", 3), ("PomPom", 3), ("Clamble", 1),
    ],
    "Blasoom": [
        ("Potbelly", 20), ("Shrubb", 5), ("Oaktopus", 5), ("Dandidoo", 8),
        ("Furcorn", 9), ("Clamble", 5), ("Thumpies", 4), ("Reedling", 4),
        ("Pummel", 3), ("Spunge", 3), ("Bowgart", 3), ("Entbrat", 3),
    ],
    "Syncopite": [
        ("Noggin", 75), ("Toe Jammer", 30), ("Potbelly", 12),
        ("Tweedle", 6), ("Fwog", 10), ("Oaktopus", 5), ("Cybop", 3),
        ("Dandidoo", 6), ("Scups", 3), ("Reedling", 4), ("Quibble", 6),
        ("Spunge", 6), ("Pummel", 4), ("Shrubb", 2), ("Shellbeat", 2),
    ],
    "Vhamp": [
        ("Noggin", 50), ("Toe Jammer", 50), ("Mammott", 35),
        ("Tweedle", 9), ("Drumpler", 12), ("Cybop", 15), ("Fwog", 5),
        ("Maw", 7), ("Scups", 3), ("Quibble", 5), ("T-Rox", 4),
        ("Pango", 5), ("PomPom", 1), ("Congle", 3), ("Riff", 1),
    ],
    "Galvana": [
        ("Noggin", 10), ("Mammott", 10), ("Toe Jammer", 10),
        ("Potbelly", 10), ("Tweedle", 10),
        ("Kayna", 6), ("Drumpler", 5), ("Fwog", 5), ("Maw", 5),
        ("Shrubb", 4), ("Furcorn", 4), ("Oaktopus", 4), ("Dandidoo", 4),
        ("Cybop", 4), ("Stogg", 3), ("Flowah", 3), ("Glowl", 3),
        ("T-Rox", 3), ("Congle", 3), ("Pango", 4), ("PomPom", 3),
        ("Pummel", 3), ("Clamble", 3), ("Scups", 3), ("Bowgart", 3),
        ("Reedling", 3), ("Spunge", 3), ("Thumpies", 3), ("Quibble", 4),
        ("Floogull", 2), ("Barrb", 2), ("Repatillo", 2),
        ("Quarrister", 1), ("Entbrat", 1), ("Deedge", 1),
        ("Shellbeat", 1), ("Riff", 1), ("Tring", 1),
    ],
    "Scaratar": [
        ("Noggin", 36), ("Mammott", 25), ("Potbelly", 16), ("Tweedle", 6),
        ("Drumpler", 4), ("Furcorn", 7), ("Shrubb", 6), ("Dandidoo", 5),
        ("Cybop", 3), ("Pango", 3), ("Thumpies", 4), ("Clamble", 3),
        ("PomPom", 1), ("Reedling", 2), ("Quarrister", 2),
    ],
    "Loodvigg": [
        ("Toe Jammer", 30), ("Mammott", 25), ("Potbelly", 6),
        ("Tweedle", 8), ("Maw", 15), ("Furcorn", 6), ("Oaktopus", 8),
        ("Quibble", 4), ("Dandidoo", 5), ("Bowgart", 5), ("Congle", 2),
        ("Pango", 2), ("Spunge", 1), ("Thumpies", 2), ("Deedge", 2),
    ],
    "Torrt": [
        ("Noggin", 50), ("Drumpler", 6), ("Fwog", 4), ("Shrubb", 2),
        ("Cybop", 6), ("Clamble", 6), ("Scups", 1), ("Pummel", 4),
        ("Reedling", 2), ("PomPom", 3), ("T-Rox", 1), ("Quarrister", 2),
    ],
    "Plixie": [
        ("Noggin", 70), ("Toe Jammer", 25), ("Mammott", 25),
        ("Potbelly", 16), ("Drumpler", 12), ("Fwog", 20), ("Maw", 35),
        ("Furcorn", 7), ("Shrubb", 8), ("Oaktopus", 15), ("T-Rox", 4),
        ("Pummel", 2), ("Clamble", 2), ("Entbrat", 5), ("Bowgart", 3),
    ],
    "Attmoz": [
        ("Tweedle", 25), ("Dandidoo", 5), ("Pango", 6), ("Scups", 6),
        ("Quibble", 3), ("PomPom", 3), ("Cybop", 8), ("Reedling", 2),
        ("Congle", 2), ("Thumpies", 2), ("Spunge", 3), ("Riff", 2),
    ],  # adjusted: total should be 65 to match wiki fill cost
    # ─── Amber Vessels ───────────────────────────────────────────────
    "Kayna": [
        ("Potbelly", 10), ("Mammott", 10), ("Tweedle", 10),
        ("Toe Jammer", 10), ("Noggin", 10), ("Oaktopus", 8),
        ("Furcorn", 8), ("Dandidoo", 8), ("Cybop", 8), ("Shrubb", 8),
        ("Clamble", 6), ("PomPom", 6), ("Scups", 6), ("T-Rox", 6),
        ("Bowgart", 6), ("Shellbeat", 2), ("Quarrister", 2),
        ("Entbrat", 2), ("Deedge", 2), ("Riff", 2),
    ],
}


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys=ON")

    run_migrations(conn, "content")

    _seed_egg_types(conn)
    _seed_monsters(conn)
    _seed_requirements(conn)
    _update_metadata(conn)

    conn.commit()
    conn.close()

    _print_summary()


def _seed_egg_types(conn: sqlite3.Connection) -> None:
    conn.executemany(
        "INSERT INTO egg_types(name, breeding_time_seconds, breeding_time_display, "
        "egg_image_path, is_placeholder) VALUES(?, ?, ?, ?, 1)",
        EGG_TYPES,
    )


def _seed_monsters(conn: sqlite3.Connection) -> None:
    conn.executemany(
        "INSERT INTO monsters(name, monster_type, image_path, wiki_slug, is_placeholder) "
        "VALUES(?, ?, ?, ?, 1)",
        MONSTERS,
    )


def _seed_requirements(conn: sqlite3.Connection) -> None:
    egg_ids = _get_id_map(conn, "egg_types")
    mon_ids = _get_id_map(conn, "monsters")

    rows = []
    for monster_name, reqs in REQUIREMENTS.items():
        mid = mon_ids[monster_name]
        for egg_name, qty in reqs:
            rows.append((mid, egg_ids[egg_name], qty))

    conn.executemany(
        "INSERT INTO monster_requirements(monster_id, egg_type_id, quantity) VALUES(?, ?, ?)",
        rows,
    )


def _update_metadata(conn: sqlite3.Connection) -> None:
    conn.execute("UPDATE update_metadata SET value = '1.0.0' WHERE key = 'content_version'")
    conn.execute("UPDATE update_metadata SET value = '2026-03-12T00:00:00Z' WHERE key = 'last_updated_utc'")
    conn.execute("UPDATE update_metadata SET value = 'bundled' WHERE key = 'source'")


def _get_id_map(conn: sqlite3.Connection, table: str) -> dict[str, int]:
    rows = conn.execute(f"SELECT name, id FROM {table}").fetchall()  # noqa: S608
    return {r[0]: r[1] for r in rows}


def _print_summary() -> None:
    conn = sqlite3.connect(str(DB_PATH))
    egg_count = conn.execute("SELECT COUNT(*) FROM egg_types").fetchone()[0]
    mon_count = conn.execute("SELECT COUNT(*) FROM monsters").fetchone()[0]
    req_count = conn.execute("SELECT COUNT(*) FROM monster_requirements").fetchone()[0]
    version = conn.execute("SELECT value FROM update_metadata WHERE key='content_version'").fetchone()[0]
    conn.close()

    wublins = 19
    celestials = 12
    amber = 1
    print(f"Seeded content.db at {DB_PATH}")
    print(f"  Content version: {version}")
    print(f"  Egg types:   {egg_count}")
    print(f"  Monsters:    {mon_count} ({wublins} Wublins, {celestials} Celestials, {amber} Amber)")
    print(f"  Requirements: {req_count} rows")


if __name__ == "__main__":
    main()
