"""Single source of truth for the bundled content_version.

Both `scripts/seed_content_db.py` and `scripts/publish_content.py` (when used)
read from `pipeline/normalized/version.txt` so a data change requires exactly
one PR-visible edit to bump the version that bootstrap uses to decide whether
to refresh the user's `%APPDATA%\\content.db` copy.
"""

from __future__ import annotations

from pathlib import Path

_VERSION_FILE = Path(__file__).resolve().parent / "normalized" / "version.txt"


def load_content_version() -> str:
    """Read the canonical content version. Returns '0.0.0-dev' if the file is absent."""
    if _VERSION_FILE.exists():
        text = _VERSION_FILE.read_text(encoding="utf-8").strip()
        return text or "0.0.0-dev"
    return "0.0.0-dev"
