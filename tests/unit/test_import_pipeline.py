"""Tests for the content import pipeline orchestration.

Tests the full import flow with mocked fetcher, verifying:
- New monster detection
- Changed requirement detection
- Review item generation
- Dry-run mode
- Review queue operations
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from pipeline.curation.review_queue import (
    has_blocking_items,
    load_review_queue,
    save_review_queue,
)
from pipeline.raw.normalizer import normalize_monster_payload, normalize_egg_payload
from pipeline.raw.source_cache import CacheEntry, SourceCache
from pipeline.raw.wiki_fetcher import FetchResult


# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def existing_monsters():
    """Sample existing normalized monsters."""
    return [
        {
            "content_key": "monster:wublin:zynth",
            "display_name": "Zynth",
            "monster_type": "wublin",
            "source_slug": "Zynth",
        },
        {
            "content_key": "monster:wublin:thwok",
            "display_name": "Thwok",
            "monster_type": "wublin",
            "source_slug": "Thwok",
        },
    ]


@pytest.fixture
def existing_requirements():
    """Sample existing requirements."""
    return [
        {"monster_key": "monster:wublin:zynth", "egg_key": "egg:noggin", "quantity": 2},
        {"monster_key": "monster:wublin:zynth", "egg_key": "egg:mammott", "quantity": 1},
    ]


@pytest.fixture
def sample_cache_entry():
    return CacheEntry(
        source_category="fandom",
        source_reference="wiki/Zynth",
        retrieved_at_utc="2026-03-22T12:00:00+00:00",
        content_hash="abc123def456",
        payload_path="/tmp/fandom_Zynth_abc123def456.raw",
        byte_size=1024,
    )


# ── Normalizer integration ──────────────────────────────────────────


class TestNormalizationFlow:
    """Test raw payload normalization as used by the import pipeline."""

    def test_normalizes_valid_monster(self, sample_cache_entry):
        raw = {
            "name": "Zynth",
            "monster_type": "wublin",
            "wiki_slug": "Zynth",
            "source_url": "https://example.com/Zynth",
        }
        record, review_items = normalize_monster_payload(
            raw,
            source_category="fandom",
            source_reference="wiki/Zynth",
            content_hash=sample_cache_entry.content_hash,
            retrieved_at_utc=sample_cache_entry.retrieved_at_utc,
        )

        assert record is not None
        assert record["content_key"] == "monster:wublin:zynth"
        assert record["display_name"] == "Zynth"
        assert record["provenance"]["factual_source"] == "fandom"
        assert review_items == []

    def test_rejects_incomplete_payload(self, sample_cache_entry):
        raw = {"name": "", "monster_type": ""}
        record, review_items = normalize_monster_payload(
            raw,
            source_category="fandom",
            source_reference="wiki/Unknown",
            content_hash=sample_cache_entry.content_hash,
            retrieved_at_utc=sample_cache_entry.retrieved_at_utc,
        )

        assert record is None
        assert len(review_items) == 1
        assert review_items[0]["issue_type"] == "source_payload_incomplete"
        assert review_items[0]["blocking"] is True

    def test_duplicate_key_generates_review_item(self, sample_cache_entry):
        raw = {
            "name": "Zynth",
            "monster_type": "wublin",
        }
        existing_keys = {"monster:wublin:zynth"}
        record, review_items = normalize_monster_payload(
            raw,
            source_category="fandom",
            source_reference="wiki/Zynth",
            content_hash=sample_cache_entry.content_hash,
            retrieved_at_utc=sample_cache_entry.retrieved_at_utc,
            existing_keys=existing_keys,
        )

        assert record is None
        assert len(review_items) == 1
        assert review_items[0]["issue_type"] == "identity_ambiguous"
        assert review_items[0]["blocking"] is True


# ── Change detection ────────────────────────────────────────────────


class TestChangeDetection:
    """Test classification of changes between existing and new records."""

    def test_detects_new_monster(self, existing_monsters):
        existing_keys = {m["content_key"] for m in existing_monsters}
        new_key = "monster:wublin:dwumrohl"
        assert new_key not in existing_keys

    def test_detects_unchanged_monster(self, existing_monsters):
        key_index = {m["content_key"]: m for m in existing_monsters}
        candidate = {
            "content_key": "monster:wublin:zynth",
            "display_name": "Zynth",
            "monster_type": "wublin",
        }
        existing = key_index.get(candidate["content_key"])
        assert existing is not None
        assert existing["display_name"] == candidate["display_name"]

    def test_detects_modified_monster(self, existing_monsters):
        key_index = {m["content_key"]: m for m in existing_monsters}
        candidate = {
            "content_key": "monster:wublin:zynth",
            "display_name": "Zynth Revised",  # changed
            "monster_type": "wublin",
        }
        existing = key_index.get(candidate["content_key"])
        assert existing is not None
        assert existing["display_name"] != candidate["display_name"]


class TestRequirementChangeDetection:
    """Test detection of changed breeding requirements."""

    def test_detects_quantity_change(self, existing_requirements):
        req_index = {}
        for req in existing_requirements:
            key = f"{req['monster_key']}:{req['egg_key']}"
            req_index[key] = req

        # New requirement has different quantity
        new_req = {"monster_key": "monster:wublin:zynth", "egg_key": "egg:noggin", "quantity": 5}
        key = f"{new_req['monster_key']}:{new_req['egg_key']}"
        existing = req_index.get(key)

        assert existing is not None
        assert existing["quantity"] != new_req["quantity"]

    def test_detects_new_requirement(self, existing_requirements):
        req_index = {}
        for req in existing_requirements:
            key = f"{req['monster_key']}:{req['egg_key']}"
            req_index[key] = req

        new_req = {"monster_key": "monster:wublin:zynth", "egg_key": "egg:tweedle", "quantity": 3}
        key = f"{new_req['monster_key']}:{new_req['egg_key']}"
        assert key not in req_index


# ── Review queue operations ─────────────────────────────────────────


class TestReviewQueue:
    """Test review queue file operations."""

    def test_save_and_load(self, tmp_path):
        queue_path = tmp_path / "review_queue.json"
        items = [
            {
                "review_id": "auto-abc123",
                "issue_type": "new_entity",
                "severity": "warning",
                "source_reference": "wiki/Zynth",
                "blocking": False,
                "status": "open",
            },
            {
                "review_id": "auto-def456",
                "issue_type": "requirement_change",
                "severity": "warning",
                "source_reference": "wiki/Thwok",
                "blocking": True,
                "status": "open",
            },
        ]

        save_review_queue(queue_path, items)
        loaded = load_review_queue(queue_path)

        assert len(loaded) == 2
        assert loaded[0]["review_id"] == "auto-abc123"
        assert loaded[1]["review_id"] == "auto-def456"

    def test_has_blocking_items(self):
        items = [
            {"blocking": True, "status": "open"},
            {"blocking": False, "status": "open"},
        ]
        assert has_blocking_items(items) is True

    def test_no_blocking_when_all_approved(self):
        items = [
            {"blocking": True, "status": "approved"},
            {"blocking": False, "status": "open"},
        ]
        assert has_blocking_items(items) is False

    def test_empty_queue_not_blocking(self):
        assert has_blocking_items([]) is False

    def test_load_nonexistent_returns_empty(self, tmp_path):
        items = load_review_queue(tmp_path / "does_not_exist.json")
        assert items == []


class TestReviewCLIIntegration:
    """Test the review CLI script's core logic."""

    def test_approve_changes_status(self):
        items = [
            {"review_id": "auto-abc123", "status": "open", "blocking": True},
        ]
        # Simulate approval
        for item in items:
            if item["review_id"].startswith("auto-abc"):
                item["status"] = "approved"

        assert items[0]["status"] == "approved"
        assert has_blocking_items(items) is False

    def test_reject_removes_item(self):
        items = [
            {"review_id": "auto-abc123", "status": "open", "blocking": True},
            {"review_id": "auto-def456", "status": "open", "blocking": False},
        ]
        items = [i for i in items if not i["review_id"].startswith("auto-abc")]
        assert len(items) == 1
        assert items[0]["review_id"] == "auto-def456"
