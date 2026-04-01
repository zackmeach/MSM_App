"""Shared pytest fixtures — in-memory SQLite databases with seeded content."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from app.db.migrations import run_migrations


@pytest.fixture
def content_conn() -> sqlite3.Connection:
    """In-memory content DB with schema applied and dev seed data."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    run_migrations(conn, "content")
    _seed_content(conn)
    return conn


@pytest.fixture
def userstate_conn() -> sqlite3.Connection:
    """In-memory userstate DB with schema applied."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    run_migrations(conn, "userstate")
    return conn


def _seed_content(conn: sqlite3.Connection) -> None:
    """Insert a representative dev dataset covering Wublins, Celestials, and Amber."""
    eggs = [
        ("Mammott",    120,    "2m",    "images/eggs/mammott_egg.png"),
        ("Noggin",      5,     "5s",    "images/eggs/noggin_egg.png"),
        ("Potbelly",   7200,   "2h",    "images/eggs/potbelly_egg.png"),
        ("Toe Jammer",  60,    "1m",    "images/eggs/toe-jammer_egg.png"),
        ("Tweedle",    14400,  "4h",    "images/eggs/tweedle_egg.png"),
        ("Furcorn",    28800,  "8h",    "images/eggs/furcorn_egg.png"),
        ("Pango",      28800,  "8h",    "images/eggs/pango_egg.png"),
        ("Drumpler",   1800,   "30m",   "images/eggs/drumpler_egg.png"),
        ("Fwog",       1800,   "30m",   "images/eggs/fwog_egg.png"),
        ("Bowgart",    43200,  "12h",   "images/eggs/bowgart_egg.png"),
        ("Clamble",    43200,  "12h",   "images/eggs/clamble_egg.png"),
        ("PomPom",     43200,  "12h",   "images/eggs/pompom_egg.png"),
        ("Thumpies",   43200,  "12h",   "images/eggs/thumpies_egg.png"),
        ("Oaktopus",   28800,  "8h",    "images/eggs/oaktopus_egg.png"),
        ("Shrubb",     28800,  "8h",    "images/eggs/shrubb_egg.png"),
    ]
    conn.executemany(
        "INSERT INTO egg_types(name, breeding_time_seconds, breeding_time_display, egg_image_path, is_placeholder) "
        "VALUES(?, ?, ?, ?, 1)",
        eggs,
    )

    monsters = [
        ("Zynth",    "wublin",    "images/monsters/zynth.png",        "Zynth"),
        ("Poewk",    "wublin",    "images/monsters/poewk.png",        "Poewk"),
        ("Dwumrohl", "wublin",    "images/monsters/dwumrohl.png",     "Dwumrohl"),
        ("Galvana",  "celestial", "images/monsters/galvana.png",      "Galvana"),
        ("Glaishur", "celestial", "images/monsters/glaishur.png",     "Glaishur"),
        ("Attmoz",   "amber",     "images/monsters/attmoz.png", "Attmoz"),
        ("Kayna",    "amber",     "images/monsters/kayna.png",  "Kayna"),
    ]
    conn.executemany(
        "INSERT INTO monsters(name, monster_type, image_path, wiki_slug, is_placeholder) "
        "VALUES(?, ?, ?, ?, 1)",
        monsters,
    )

    egg_ids = {r[0]: r[1] for r in conn.execute("SELECT name, id FROM egg_types").fetchall()}
    mon_ids = {r[0]: r[1] for r in conn.execute("SELECT name, id FROM monsters").fetchall()}

    reqs = [
        (mon_ids["Zynth"], egg_ids["Bowgart"],  1),
        (mon_ids["Zynth"], egg_ids["Clamble"],  1),
        (mon_ids["Zynth"], egg_ids["PomPom"],   1),
        (mon_ids["Zynth"], egg_ids["Thumpies"], 1),
        (mon_ids["Poewk"], egg_ids["Bowgart"],  1),
        (mon_ids["Poewk"], egg_ids["Drumpler"], 2),
        (mon_ids["Poewk"], egg_ids["Fwog"],     1),
        (mon_ids["Poewk"], egg_ids["Pango"],    1),
        (mon_ids["Dwumrohl"], egg_ids["Mammott"],    2),
        (mon_ids["Dwumrohl"], egg_ids["Noggin"],     2),
        (mon_ids["Dwumrohl"], egg_ids["Potbelly"],   2),
        (mon_ids["Dwumrohl"], egg_ids["Toe Jammer"], 2),
        (mon_ids["Galvana"], egg_ids["Bowgart"],  2),
        (mon_ids["Galvana"], egg_ids["Mammott"],  4),
        (mon_ids["Galvana"], egg_ids["Tweedle"],  2),
        (mon_ids["Galvana"], egg_ids["Furcorn"],  1),
        (mon_ids["Glaishur"], egg_ids["Mammott"],  3),
        (mon_ids["Glaishur"], egg_ids["Tweedle"],  2),
        (mon_ids["Glaishur"], egg_ids["Potbelly"], 2),
        (mon_ids["Glaishur"], egg_ids["Furcorn"],  1),
        (mon_ids["Attmoz"], egg_ids["Drumpler"], 3),
        (mon_ids["Attmoz"], egg_ids["Mammott"],  2),
        (mon_ids["Attmoz"], egg_ids["Noggin"],   1),
        # Amber Vessel: Kayna
        (mon_ids["Kayna"], egg_ids["Potbelly"],   4),
        (mon_ids["Kayna"], egg_ids["Mammott"],    4),
        (mon_ids["Kayna"], egg_ids["Tweedle"],    4),
        (mon_ids["Kayna"], egg_ids["Oaktopus"],   3),
        (mon_ids["Kayna"], egg_ids["Shrubb"],     3),
    ]
    conn.executemany(
        "INSERT INTO monster_requirements(monster_id, egg_type_id, quantity) VALUES(?, ?, ?)",
        reqs,
    )
    conn.commit()


@pytest.fixture
def id_maps(content_conn: sqlite3.Connection) -> dict:
    """Return convenience dicts for egg and monster name→id lookups."""
    egg_ids = {r[0]: r[1] for r in content_conn.execute("SELECT name, id FROM egg_types").fetchall()}
    mon_ids = {r[0]: r[1] for r in content_conn.execute("SELECT name, id FROM monsters").fetchall()}
    return {"eggs": egg_ids, "monsters": mon_ids}
