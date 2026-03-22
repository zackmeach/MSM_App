"""Tests for raw source cache and normalization adapters."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline.raw.source_cache import SourceCache, CacheEntry
from pipeline.raw.normalizer import (
    normalize_monster_payload,
    normalize_egg_payload,
    NormalizationResult,
)


# ── Source Cache Tests ───────────────────────────────────────────────


class TestSourceCache:
    def test_store_and_retrieve(self, tmp_path: Path):
        cache = SourceCache(cache_dir=tmp_path / "raw")
        payload = b'{"name": "Zynth", "type": "wublin"}'
        entry = cache.store("factual_source", "wiki/Zynth", payload)

        assert entry.source_category == "factual_source"
        assert entry.source_reference == "wiki/Zynth"
        assert entry.byte_size == len(payload)
        assert entry.content_hash != ""

    def test_cache_hit_on_same_content(self, tmp_path: Path):
        cache = SourceCache(cache_dir=tmp_path / "raw")
        payload = b'{"name": "Zynth"}'
        e1 = cache.store("factual_source", "wiki/Zynth", payload)
        e2 = cache.store("factual_source", "wiki/Zynth", payload)
        assert e1.cache_key == e2.cache_key

    def test_different_content_creates_new_entry(self, tmp_path: Path):
        cache = SourceCache(cache_dir=tmp_path / "raw")
        e1 = cache.store("factual_source", "wiki/Zynth", b'{"v": 1}')
        e2 = cache.store("factual_source", "wiki/Zynth", b'{"v": 2}')
        assert e1.content_hash != e2.content_hash

    def test_get_returns_entry(self, tmp_path: Path):
        cache = SourceCache(cache_dir=tmp_path / "raw")
        cache.store("factual_source", "wiki/Zynth", b'data')
        entry = cache.get("factual_source", "wiki/Zynth")
        assert entry is not None
        assert entry.source_reference == "wiki/Zynth"

    def test_get_returns_none_for_missing(self, tmp_path: Path):
        cache = SourceCache(cache_dir=tmp_path / "raw")
        assert cache.get("factual_source", "missing") is None

    def test_persistence_across_instances(self, tmp_path: Path):
        cache_dir = tmp_path / "raw"
        cache1 = SourceCache(cache_dir=cache_dir)
        cache1.store("factual_source", "wiki/Zynth", b'data')

        cache2 = SourceCache(cache_dir=cache_dir)
        entry = cache2.get("factual_source", "wiki/Zynth")
        assert entry is not None

    def test_entries_list(self, tmp_path: Path):
        cache = SourceCache(cache_dir=tmp_path / "raw")
        cache.store("a", "ref1", b'data1')
        cache.store("b", "ref2", b'data2')
        assert len(cache.entries()) == 2


# ── Monster Normalization Tests ──────────────────────────────────────


class TestNormalizeMonster:
    def test_basic_normalization(self):
        raw = {
            "name": "Zynth",
            "monster_type": "wublin",
            "wiki_slug": "Zynth",
            "source_url": "https://example.invalid/wiki/Zynth",
        }
        record, review = normalize_monster_payload(
            raw, "fandom", "wiki/Zynth", "abc123", "2026-03-22T00:00:00Z"
        )
        assert record is not None
        assert record["content_key"] == "monster:wublin:zynth"
        assert record["display_name"] == "Zynth"
        assert record["monster_type"] == "wublin"
        assert record["provenance"]["factual_source"] == "fandom"
        assert len(review) == 0

    def test_missing_name_emits_review(self):
        raw = {"monster_type": "wublin"}
        record, review = normalize_monster_payload(
            raw, "fandom", "wiki/Unknown", "abc", "2026-01-01"
        )
        assert record is None
        assert len(review) == 1
        assert review[0]["issue_type"] == "source_payload_incomplete"
        assert review[0]["blocking"] is True

    def test_duplicate_key_emits_review(self):
        raw = {
            "name": "Zynth",
            "monster_type": "wublin",
            "wiki_slug": "Zynth",
        }
        existing = {"monster:wublin:zynth"}
        record, review = normalize_monster_payload(
            raw, "fandom", "wiki/Zynth", "abc", "2026-01-01",
            existing_keys=existing,
        )
        assert record is None
        assert len(review) == 1
        assert review[0]["issue_type"] == "identity_ambiguous"

    def test_override_forces_key(self):
        raw = {
            "name": "Zynth",
            "monster_type": "wublin",
            "wiki_slug": "Zynth",
        }
        overrides = {
            "monster:wublin:zynth": {
                "override_id": "ov-001",
                "forced_content_key": "monster:wublin:zynth-custom",
            },
        }
        record, review = normalize_monster_payload(
            raw, "fandom", "wiki/Zynth", "abc", "2026-01-01",
            overrides=overrides,
        )
        assert record is not None
        assert record["content_key"] == "monster:wublin:zynth-custom"
        assert "ov-001" in record["overrides_applied"]

    def test_source_fingerprint_generated(self):
        raw = {"name": "Brump", "monster_type": "wublin", "wiki_slug": "Brump"}
        record, _ = normalize_monster_payload(
            raw, "fandom", "wiki/Brump", "abc", "2026-01-01"
        )
        assert record is not None
        assert record["source_fingerprint"].startswith("sha256:")


# ── Egg Normalization Tests ──────────────────────────────────────────


class TestNormalizeEgg:
    def test_basic_normalization(self):
        raw = {
            "name": "Noggin",
            "breeding_time_seconds": 5,
            "breeding_time_display": "5s",
            "source_url": "https://example.invalid/wiki/Noggin",
        }
        record, review = normalize_egg_payload(
            raw, "fandom", "wiki/Noggin", "abc", "2026-01-01"
        )
        assert record is not None
        assert record["content_key"] == "egg:noggin"
        assert record["breeding_time_seconds"] == 5
        assert len(review) == 0

    def test_missing_name_emits_review(self):
        raw = {"breeding_time_seconds": 5}
        record, review = normalize_egg_payload(
            raw, "fandom", "wiki/Unknown", "abc", "2026-01-01"
        )
        assert record is None
        assert len(review) == 1
        assert review[0]["blocking"] is True

    def test_invalid_breeding_time_emits_warning(self):
        raw = {
            "name": "BadEgg",
            "breeding_time_seconds": -1,
            "breeding_time_display": "??",
        }
        record, review = normalize_egg_payload(
            raw, "fandom", "wiki/BadEgg", "abc", "2026-01-01"
        )
        assert record is not None  # still produces a record
        assert len(review) == 1
        assert review[0]["severity"] == "warning"
        assert review[0]["blocking"] is False

    def test_egg_image_path_default(self):
        raw = {"name": "Toe Jammer", "breeding_time_seconds": 5, "breeding_time_display": "5s"}
        record, _ = normalize_egg_payload(
            raw, "fandom", "wiki/Toe_Jammer", "abc", "2026-01-01"
        )
        assert record is not None
        assert record["egg_image_path"] == "images/eggs/toe-jammer_egg.png"
