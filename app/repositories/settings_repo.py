"""Repository for app_settings in userstate.db."""

from __future__ import annotations

import sqlite3


def get(conn: sqlite3.Connection, key: str, default: str = "") -> str:
    row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    return row[0] if row else default


def set_value(conn: sqlite3.Connection, key: str, value: str) -> None:
    """Upsert an app_settings row. Caller owns the transaction (no commit here)."""
    conn.execute(
        "INSERT INTO app_settings(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
