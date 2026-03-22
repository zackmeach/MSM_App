"""Release content seed — populates resources/db/content.db from normalized pipeline data.

Reads canonical content from ``pipeline/normalized/`` and builds the release
content DB.  Falls back to the embedded Python literal data only when the
normalized files do not exist (backwards-compatible bootstrap).

Run:  python scripts/seed_content_db.py
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.db.migrations import run_migrations  # noqa: E402
from app.domain.models import egg_content_key, monster_content_key  # noqa: E402

DB_PATH = ROOT / "resources" / "db" / "content.db"
NORMALIZED_DIR = ROOT / "pipeline" / "normalized"

# ── Fallback embedded data (kept for bootstrap if normalized files absent) ────

EGG_TYPES = [
    ("Noggin",       5,     "5s",      "images/eggs/noggin_egg.png"),
    ("Mammott",      5,     "5s",      "images/eggs/mammott_egg.png"),
    ("Toe Jammer",   5,     "5s",      "images/eggs/toejammer_egg.png"),
    ("Potbelly",     5,     "5s",      "images/eggs/potbelly_egg.png"),
    ("Tweedle",      5,     "5s",      "images/eggs/tweedle_egg.png"),
    ("Drumpler",     1800,  "30m",     "images/eggs/drumpler_egg.png"),
    ("Fwog",         1800,  "30m",     "images/eggs/fwog_egg.png"),
    ("Maw",          1800,  "30m",     "images/eggs/maw_egg.png"),
    ("Shrubb",       1800,  "30m",     "images/eggs/shrubb_egg.png"),
    ("Furcorn",      5400,  "1h 30m",  "images/eggs/furcorn_egg.png"),
    ("Pango",        7200,  "2h",      "images/eggs/pango_egg.png"),
    ("Oaktopus",     7200,  "2h",      "images/eggs/oaktopus_egg.png"),
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
    ("Entbrat",      86400, "24h",     "images/eggs/entbrat_egg.png"),
    ("Deedge",       86400, "24h",     "images/eggs/deedge_egg.png"),
    ("Shellbeat",    86400, "24h",     "images/eggs/shellbeat_egg.png"),
    ("Quarrister",   86400, "24h",     "images/eggs/quarrister_egg.png"),
    ("Riff",         86400, "24h",     "images/eggs/riff_egg.png"),
    ("Kayna",        25200, "7h",      "images/eggs/kayna_egg.png"),
    ("Glowl",        36000, "10h",     "images/eggs/glowl_egg.png"),
    ("Flowah",       36000, "10h",     "images/eggs/flowah_egg.png"),
    ("Stogg",        36000, "10h",     "images/eggs/stogg_egg.png"),
    ("Floogull",     72000, "20h",     "images/eggs/floogull_egg.png"),
    ("Barrb",        72000, "20h",     "images/eggs/barrb_egg.png"),
    ("Repatillo",    72000, "20h",     "images/eggs/repatillo_egg.png"),
    ("Tring",       144000, "1d 16h",  "images/eggs/tring_egg.png"),
]

MONSTERS = [
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
    ("Kayna",        "amber",     "images/monsters/kayna_amber.png",  "Kayna"),
    ("Glowl",        "amber",     "images/monsters/glowl_amber.png",  "Glowl"),
    ("Flowah",       "amber",     "images/monsters/flowah_amber.png", "Flowah"),
    ("Stogg",        "amber",     "images/monsters/stogg_amber.png",  "Stogg"),
    ("Floogull",     "amber",     "images/monsters/floogull_amber.png", "Floogull"),
    ("Barrb",        "amber",     "images/monsters/barrb_amber.png",  "Barrb"),
    ("Repatillo",    "amber",     "images/monsters/repatillo_amber.png", "Repatillo"),
    ("Tring",        "amber",     "images/monsters/tring_amber.png",  "Tring"),
]

REQUIREMENTS: dict[str, list[tuple[str, int]]] = {
    "Zynth": [("Congle", 1), ("Drumpler", 1), ("Maw", 1), ("Oaktopus", 1), ("Pango", 1), ("T-Rox", 1)],
    "Brump": [("Furcorn", 6), ("Fwog", 2)],
    "Thwok": [("Bowgart", 4), ("Deedge", 1), ("Entbrat", 1), ("Furcorn", 4), ("PomPom", 4), ("Quarrister", 1), ("Quibble", 4), ("Riff", 1), ("Shellbeat", 1), ("Spunge", 4)],
    "Poewk": [("Clamble", 2), ("Dandidoo", 2), ("Oaktopus", 1), ("Pango", 1), ("PomPom", 1), ("Reedling", 1), ("Scups", 1), ("Shellbeat", 1), ("Shrubb", 1)],
    "Zuuker": [("Bowgart", 4), ("Deedge", 2), ("Entbrat", 2), ("Furcorn", 6), ("Fwog", 4), ("Oaktopus", 6), ("T-Rox", 6)],
    "Tympa": [("Clamble", 12), ("Drumpler", 24), ("Pummel", 12), ("Shellbeat", 8), ("T-Rox", 12)],
    "Screemu": [("Quibble", 6), ("Shellbeat", 2), ("Shrubb", 6), ("Spunge", 6)],
    "Dermit": [("Entbrat", 3), ("Fwog", 12), ("Quarrister", 3), ("Scups", 4), ("Thumpies", 4)],
    "Gheegur": [("Cybop", 6), ("PomPom", 4), ("Reedling", 6), ("Riff", 6), ("Scups", 4)],
    "Maulch": [("Clamble", 4), ("Entbrat", 4), ("Furcorn", 8), ("Noggin", 6), ("Pummel", 6), ("Quarrister", 4), ("Spunge", 6)],
    "Fleechwurm": [("Dandidoo", 4), ("Furcorn", 4), ("Pummel", 4), ("Quarrister", 3), ("Reedling", 3), ("Shellbeat", 3), ("Spunge", 3)],
    "Astropod": [("Deedge", 5), ("Reedling", 8), ("Scups", 8), ("Shellbeat", 5), ("Spunge", 6), ("Toe Jammer", 10)],
    "Blipsqueak": [("Cybop", 6), ("Deedge", 4), ("PomPom", 4), ("T-Rox", 6), ("Toe Jammer", 4)],
    "Scargo": [("Clamble", 3), ("Dandidoo", 3), ("Pummel", 2), ("Shellbeat", 3), ("Shrubb", 3), ("Spunge", 2)],
    "BonaPetite": [("Bowgart", 6), ("Drumpler", 10), ("Entbrat", 5), ("Fwog", 10), ("Mammott", 10), ("Maw", 10), ("PomPom", 6), ("Riff", 5), ("T-Rox", 6)],
    "Creepuscule": [("Congle", 8), ("Deedge", 5), ("Noggin", 12), ("Pummel", 6), ("Quibble", 10), ("Shellbeat", 5), ("T-Rox", 6)],
    "Whajje": [("Cybop", 10), ("Dandidoo", 10), ("Deedge", 7), ("Reedling", 10), ("Tweedle", 6)],
    "Dwumrohl": [("Bowgart", 4), ("Congle", 4), ("Deedge", 3), ("Entbrat", 3), ("Mammott", 8), ("Noggin", 8), ("PomPom", 4), ("Potbelly", 4), ("Pummel", 4), ("Quarrister", 3), ("Reedling", 4), ("Riff", 3), ("Scups", 2), ("Shellbeat", 3), ("Thumpies", 2), ("Toe Jammer", 8), ("Tweedle", 4)],
    "Pixolotl": [("Cybop", 14), ("Entbrat", 6), ("Fwog", 10), ("Pummel", 8), ("Riff", 6), ("Scups", 10), ("T-Rox", 8)],
    "Hornacle": [("Toe Jammer", 50), ("Fwog", 15), ("Oaktopus", 12), ("Maw", 9), ("Quibble", 8), ("Pummel", 5), ("Bowgart", 4), ("Scups", 4), ("Spunge", 3), ("Congle", 3), ("Shellbeat", 3), ("T-Rox", 2)],
    "Furnoss": [("Noggin", 25), ("Potbelly", 10), ("Tweedle", 5), ("Kayna", 15), ("Glowl", 7), ("Flowah", 5), ("Stogg", 5), ("Cybop", 2), ("Shrubb", 3), ("Repatillo", 3), ("Floogull", 4), ("Barrb", 3), ("Dandidoo", 2), ("Reedling", 3), ("Tring", 2)],
    "Glaishur": [("Mammott", 40), ("Bowgart", 8), ("Deedge", 4), ("Furcorn", 10), ("Congle", 2), ("Drumpler", 7), ("Maw", 5), ("T-Rox", 2), ("Thumpies", 2), ("Pango", 3), ("PomPom", 3), ("Clamble", 1)],
    "Blasoom": [("Potbelly", 20), ("Shrubb", 5), ("Oaktopus", 5), ("Dandidoo", 8), ("Furcorn", 9), ("Clamble", 5), ("Thumpies", 4), ("Reedling", 4), ("Pummel", 3), ("Spunge", 3), ("Bowgart", 3), ("Entbrat", 3)],
    "Syncopite": [("Noggin", 75), ("Toe Jammer", 30), ("Potbelly", 12), ("Tweedle", 6), ("Fwog", 10), ("Oaktopus", 5), ("Cybop", 3), ("Dandidoo", 6), ("Scups", 3), ("Reedling", 4), ("Quibble", 6), ("Spunge", 6), ("Pummel", 4), ("Shrubb", 2), ("Shellbeat", 2)],
    "Vhamp": [("Noggin", 50), ("Toe Jammer", 50), ("Mammott", 35), ("Tweedle", 9), ("Drumpler", 12), ("Cybop", 15), ("Fwog", 5), ("Maw", 7), ("Scups", 3), ("Quibble", 5), ("T-Rox", 4), ("Pango", 5), ("PomPom", 1), ("Congle", 3), ("Riff", 1)],
    "Galvana": [("Noggin", 10), ("Mammott", 10), ("Toe Jammer", 10), ("Potbelly", 10), ("Tweedle", 10), ("Kayna", 6), ("Drumpler", 5), ("Fwog", 5), ("Maw", 5), ("Shrubb", 4), ("Furcorn", 4), ("Oaktopus", 4), ("Dandidoo", 4), ("Cybop", 4), ("Stogg", 3), ("Flowah", 3), ("Glowl", 3), ("T-Rox", 3), ("Congle", 3), ("Pango", 4), ("PomPom", 3), ("Pummel", 3), ("Clamble", 3), ("Scups", 3), ("Bowgart", 3), ("Reedling", 3), ("Spunge", 3), ("Thumpies", 3), ("Quibble", 4), ("Floogull", 2), ("Barrb", 2), ("Repatillo", 2), ("Quarrister", 1), ("Entbrat", 1), ("Deedge", 1), ("Shellbeat", 1), ("Riff", 1), ("Tring", 1)],
    "Scaratar": [("Noggin", 36), ("Mammott", 25), ("Potbelly", 16), ("Tweedle", 6), ("Drumpler", 4), ("Furcorn", 7), ("Shrubb", 6), ("Dandidoo", 5), ("Cybop", 3), ("Pango", 3), ("Thumpies", 4), ("Clamble", 3), ("PomPom", 1), ("Reedling", 2), ("Quarrister", 2)],
    "Loodvigg": [("Toe Jammer", 30), ("Mammott", 25), ("Potbelly", 6), ("Tweedle", 8), ("Maw", 15), ("Furcorn", 6), ("Oaktopus", 8), ("Quibble", 4), ("Dandidoo", 5), ("Bowgart", 5), ("Congle", 2), ("Pango", 2), ("Spunge", 1), ("Thumpies", 2), ("Deedge", 2)],
    "Torrt": [("Noggin", 50), ("Drumpler", 6), ("Fwog", 4), ("Shrubb", 2), ("Cybop", 6), ("Clamble", 6), ("Scups", 1), ("Pummel", 4), ("Reedling", 2), ("PomPom", 3), ("T-Rox", 1), ("Quarrister", 2)],
    "Plixie": [("Noggin", 70), ("Toe Jammer", 25), ("Mammott", 25), ("Potbelly", 16), ("Drumpler", 12), ("Fwog", 20), ("Maw", 35), ("Furcorn", 7), ("Shrubb", 8), ("Oaktopus", 15), ("T-Rox", 4), ("Pummel", 2), ("Clamble", 2), ("Entbrat", 5), ("Bowgart", 3)],
    "Attmoz": [("Tweedle", 25), ("Dandidoo", 5), ("Pango", 6), ("Scups", 6), ("Quibble", 3), ("PomPom", 3), ("Cybop", 8), ("Reedling", 2), ("Congle", 2), ("Thumpies", 2), ("Spunge", 3), ("Riff", 2)],
    "Kayna": [("Potbelly", 10), ("Mammott", 10), ("Tweedle", 10), ("Toe Jammer", 10), ("Noggin", 10), ("Oaktopus", 8), ("Furcorn", 8), ("Dandidoo", 8), ("Cybop", 8), ("Shrubb", 8), ("Clamble", 6), ("PomPom", 6), ("Scups", 6), ("T-Rox", 6), ("Bowgart", 6), ("Shellbeat", 2), ("Quarrister", 2), ("Entbrat", 2), ("Deedge", 2), ("Riff", 2)],
    "Glowl": [("Noggin", 12), ("Mammott", 12), ("Toe Jammer", 12), ("Potbelly", 8), ("Tweedle", 8), ("Drumpler", 6), ("Fwog", 6), ("Maw", 6), ("Shrubb", 6), ("Oaktopus", 6), ("Cybop", 4), ("Scups", 4), ("Bowgart", 4), ("T-Rox", 4), ("Entbrat", 2), ("Deedge", 2)],
    "Flowah": [("Potbelly", 15), ("Tweedle", 12), ("Noggin", 10), ("Mammott", 8), ("Furcorn", 8), ("Oaktopus", 6), ("Shrubb", 6), ("Dandidoo", 6), ("Reedling", 4), ("PomPom", 4), ("Bowgart", 4), ("Pummel", 4), ("Entbrat", 2), ("Quarrister", 2), ("Riff", 2)],
    "Stogg": [("Noggin", 15), ("Mammott", 12), ("Toe Jammer", 10), ("Drumpler", 8), ("Fwog", 8), ("Maw", 6), ("Cybop", 6), ("Congle", 4), ("T-Rox", 4), ("Clamble", 4), ("Thumpies", 4), ("Scups", 4), ("Shellbeat", 2), ("Deedge", 2), ("Quarrister", 2)],
    "Floogull": [("Toe Jammer", 12), ("Mammott", 10), ("Potbelly", 10), ("Tweedle", 8), ("Fwog", 6), ("Oaktopus", 6), ("Pango", 6), ("Furcorn", 6), ("Quibble", 4), ("Spunge", 4), ("Bowgart", 4), ("PomPom", 4), ("Shellbeat", 2), ("Entbrat", 2), ("Deedge", 2)],
    "Barrb": [("Noggin", 12), ("Tweedle", 10), ("Potbelly", 10), ("Drumpler", 6), ("Shrubb", 6), ("Furcorn", 6), ("Maw", 6), ("Cybop", 4), ("Dandidoo", 4), ("Reedling", 4), ("Pummel", 4), ("Clamble", 4), ("T-Rox", 4), ("Quarrister", 2), ("Riff", 2)],
    "Repatillo": [("Mammott", 12), ("Noggin", 10), ("Toe Jammer", 10), ("Drumpler", 6), ("Fwog", 6), ("Pango", 6), ("Oaktopus", 6), ("Congle", 4), ("Thumpies", 4), ("Scups", 4), ("Quibble", 4), ("Spunge", 4), ("T-Rox", 4), ("Deedge", 2), ("Shellbeat", 2)],
    "Tring": [("Noggin", 15), ("Toe Jammer", 15), ("Mammott", 15), ("Potbelly", 10), ("Tweedle", 10), ("Drumpler", 8), ("Fwog", 8), ("Maw", 8), ("Shrubb", 6), ("Furcorn", 6), ("Oaktopus", 6), ("Cybop", 4), ("Quibble", 4), ("Dandidoo", 4), ("Scups", 4), ("Reedling", 4), ("T-Rox", 4), ("Pummel", 4), ("Congle", 4), ("Bowgart", 4), ("PomPom", 4), ("Thumpies", 2), ("Clamble", 2), ("Spunge", 2), ("Entbrat", 2), ("Deedge", 2), ("Shellbeat", 2), ("Quarrister", 2), ("Riff", 2)],
}


# ── Normalized-source loader ────────────────────────────────────────


def _load_normalized() -> tuple[list[dict], list[dict], list[dict]] | None:
    """Load normalized monster/egg/requirement JSON, or None if unavailable."""
    m_path = NORMALIZED_DIR / "monsters.json"
    e_path = NORMALIZED_DIR / "eggs.json"
    r_path = NORMALIZED_DIR / "requirements.json"
    if not (m_path.exists() and e_path.exists() and r_path.exists()):
        return None
    with open(m_path, encoding="utf-8") as f:
        monsters = json.load(f)
    with open(e_path, encoding="utf-8") as f:
        eggs = json.load(f)
    with open(r_path, encoding="utf-8") as f:
        reqs = json.load(f)
    return monsters, eggs, reqs


# ── Seeding functions ────────────────────────────────────────────────


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys=ON")

    run_migrations(conn, "content")

    normalized = _load_normalized()
    if normalized:
        _seed_from_normalized(conn, *normalized)
        print("(seeded from normalized pipeline data)")
    else:
        _seed_from_literals(conn)
        print("(seeded from embedded literal data — normalized files not found)")

    _update_metadata(conn)
    conn.commit()
    conn.close()
    _print_summary()


def _seed_from_normalized(
    conn: sqlite3.Connection,
    monsters: list[dict],
    eggs: list[dict],
    requirements: list[dict],
) -> None:
    conn.executemany(
        "INSERT INTO egg_types"
        "(name, breeding_time_seconds, breeding_time_display, egg_image_path, "
        "is_placeholder, content_key, source_fingerprint, asset_source, asset_sha256) "
        "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                e["display_name"],
                e["breeding_time_seconds"],
                e["breeding_time_display"],
                e["egg_image_path"],
                1 if e["is_placeholder"] else 0,
                e["content_key"],
                e.get("source_fingerprint", ""),
                e.get("asset_source", "generated_placeholder"),
                e.get("asset_sha256", ""),
            )
            for e in eggs
        ],
    )

    conn.executemany(
        "INSERT INTO monsters"
        "(name, monster_type, image_path, wiki_slug, is_placeholder, content_key, "
        "source_fingerprint, asset_source, asset_sha256, is_deprecated) "
        "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                m["display_name"],
                m["monster_type"],
                m["image_path"],
                m.get("wiki_slug", m.get("source_slug", "")),
                1 if m["is_placeholder"] else 0,
                m["content_key"],
                m.get("source_fingerprint", ""),
                m.get("asset_source", "generated_placeholder"),
                m.get("asset_sha256", ""),
                1 if m.get("is_deprecated", False) else 0,
            )
            for m in monsters
        ],
    )

    egg_ids = _get_id_map(conn, "egg_types")
    mon_ids = _get_id_map(conn, "monsters")

    egg_key_to_name: dict[str, str] = {e["content_key"]: e["display_name"] for e in eggs}
    mon_key_to_name: dict[str, str] = {m["content_key"]: m["display_name"] for m in monsters}

    rows = []
    for req in requirements:
        m_name = mon_key_to_name.get(req["monster_key"], "")
        e_name = egg_key_to_name.get(req["egg_key"], "")
        if m_name in mon_ids and e_name in egg_ids:
            rows.append((mon_ids[m_name], egg_ids[e_name], req["quantity"]))

    conn.executemany(
        "INSERT INTO monster_requirements(monster_id, egg_type_id, quantity) VALUES(?, ?, ?)",
        rows,
    )


def _seed_from_literals(conn: sqlite3.Connection) -> None:
    conn.executemany(
        "INSERT INTO egg_types(name, breeding_time_seconds, breeding_time_display, "
        "egg_image_path, is_placeholder, content_key) VALUES(?, ?, ?, ?, 1, ?)",
        [(*et, egg_content_key(et[0])) for et in EGG_TYPES],
    )
    conn.executemany(
        "INSERT INTO monsters(name, monster_type, image_path, wiki_slug, is_placeholder, content_key) "
        "VALUES(?, ?, ?, ?, 1, ?)",
        [(*m, monster_content_key(m[1], m[0])) for m in MONSTERS],
    )

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
    amber = 8
    print(f"Seeded content.db at {DB_PATH}")
    print(f"  Content version: {version}")
    print(f"  Egg types:   {egg_count}")
    print(f"  Monsters:    {mon_count} ({wublins} Wublins, {celestials} Celestials, {amber} Amber)")
    print(f"  Requirements: {req_count} rows")


if __name__ == "__main__":
    main()
