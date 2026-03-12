"""Two-tier asset path resolution: download cache > bundled install > placeholder."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_PLACEHOLDER_PATH: Path | None = None
_BUNDLE_DIR: Path | None = None
_CACHE_DIR: Path | None = None


def configure(bundle_dir: Path, cache_dir: Path) -> None:
    global _BUNDLE_DIR, _CACHE_DIR
    _BUNDLE_DIR = bundle_dir
    _CACHE_DIR = cache_dir


def resolve(relative_path: str) -> str:
    """Return the absolute path of the best available asset."""
    if not relative_path:
        return _placeholder_path()

    if _CACHE_DIR:
        cached = _CACHE_DIR / relative_path
        if cached.exists():
            return str(cached)

    if _BUNDLE_DIR:
        bundled = _BUNDLE_DIR / relative_path
        if bundled.exists():
            return str(bundled)

    logger.debug("Asset not found, using placeholder: %s", relative_path)
    return _placeholder_path()


def _placeholder_path() -> str:
    global _PLACEHOLDER_PATH
    if _PLACEHOLDER_PATH is None:
        if _BUNDLE_DIR:
            p = _BUNDLE_DIR / "images" / "ui" / "placeholder.png"
            if p.exists():
                _PLACEHOLDER_PATH = p
                return str(p)
        return ""
    return str(_PLACEHOLDER_PATH)
