"""Shared repository helpers."""

from __future__ import annotations

import sqlite3
from typing import Any


def fetchone_dict(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> dict[str, Any] | None:
    conn.row_factory = sqlite3.Row
    row = conn.execute(sql, params).fetchone()
    conn.row_factory = None
    if row is None:
        return None
    return dict(row)


def fetchall_dicts(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql, params).fetchall()
    conn.row_factory = None
    return [dict(r) for r in rows]
