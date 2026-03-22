"""Raw source cache for maintainer-side content acquisition.

Stores fetched payloads with metadata for provenance tracking,
deduplication, and rebuild reproducibility.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    source_category: str
    source_reference: str
    retrieved_at_utc: str
    content_hash: str
    payload_path: str
    byte_size: int

    @property
    def cache_key(self) -> str:
        return f"{self.source_category}:{self.source_reference}:{self.content_hash}"


@dataclass
class SourceCache:
    """File-system-backed raw source cache."""

    cache_dir: Path
    _index: dict[str, CacheEntry] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._load_index()

    # ── Public API ───────────────────────────────────────────────────

    def store(
        self,
        source_category: str,
        source_reference: str,
        payload: bytes,
    ) -> CacheEntry:
        content_hash = hashlib.sha256(payload).hexdigest()
        now = datetime.now(timezone.utc).isoformat()

        existing = self._index.get(f"{source_category}:{source_reference}:{content_hash}")
        if existing:
            logger.debug("Cache hit for %s:%s (hash unchanged)", source_category, source_reference)
            return existing

        safe_ref = source_reference.replace("/", "_").replace("\\", "_")[:80]
        filename = f"{source_category}_{safe_ref}_{content_hash[:12]}.raw"
        payload_path = str(self.cache_dir / filename)

        (self.cache_dir / filename).write_bytes(payload)

        entry = CacheEntry(
            source_category=source_category,
            source_reference=source_reference,
            retrieved_at_utc=now,
            content_hash=content_hash,
            payload_path=payload_path,
            byte_size=len(payload),
        )
        self._index[entry.cache_key] = entry
        self._save_index()
        logger.info("Cached %s:%s (%d bytes)", source_category, source_reference, len(payload))
        return entry

    def get(self, source_category: str, source_reference: str) -> CacheEntry | None:
        for key, entry in self._index.items():
            if key.startswith(f"{source_category}:{source_reference}:"):
                return entry
        return None

    def entries(self) -> list[CacheEntry]:
        return list(self._index.values())

    # ── Persistence ──────────────────────────────────────────────────

    def _index_path(self) -> Path:
        return self.cache_dir / "_index.json"

    def _load_index(self) -> None:
        p = self._index_path()
        if not p.exists():
            return
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        for item in data:
            entry = CacheEntry(**item)
            self._index[entry.cache_key] = entry

    def _save_index(self) -> None:
        with open(self._index_path(), "w", encoding="utf-8") as f:
            json.dump([asdict(e) for e in self._index.values()], f, indent=2)
