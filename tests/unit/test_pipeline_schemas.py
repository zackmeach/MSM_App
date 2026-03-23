"""Tests for normalized content schemas and validators."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline.schemas.normalized import (
    ValidationResult,
    validate_monster,
    validate_egg,
    validate_requirement,
    validate_asset,
    validate_alias,
    validate_deprecation,
    validate_review_item,
    validate_monsters_file,
    validate_eggs_file,
    validate_requirements_file,
    load_json_records,
)
from pipeline.curation.overrides import load_overrides, validate_overrides, OverrideSet
from pipeline.curation.review_queue import (
    load_review_queue,
    validate_review_queue,
    has_blocking_items,
)


NORMALIZED_DIR = Path(__file__).resolve().parent.parent.parent / "pipeline" / "normalized"
CURATION_DIR = Path(__file__).resolve().parent.parent.parent / "pipeline" / "curation"
REVIEW_DIR = Path(__file__).resolve().parent.parent.parent / "pipeline" / "review"


# ── Fixtures ─────────────────────────────────────────────────────────


def _valid_monster() -> dict:
    return {
        "content_key": "monster:wublin:zynth",
        "display_name": "Zynth",
        "monster_type": "wublin",
        "source_slug": "Zynth",
        "source_url": "https://example.invalid/wiki/Zynth",
        "source_fingerprint": "",
        "wiki_slug": "Zynth",
        "image_path": "images/monsters/zynth.png",
        "is_placeholder": True,
        "asset_source": "generated_placeholder",
        "asset_sha256": "",
        "is_deprecated": False,
        "deprecated_at_utc": None,
        "deprecation_reason": None,
        "provenance": {"factual_source": "seed"},
        "overrides_applied": [],
    }


def _valid_egg() -> dict:
    return {
        "content_key": "egg:noggin",
        "display_name": "Noggin",
        "breeding_time_seconds": 5,
        "breeding_time_display": "5s",
        "source_slug": "Noggin",
        "source_url": "https://example.invalid/wiki/Noggin",
        "source_fingerprint": "",
        "egg_image_path": "images/eggs/noggin_egg.png",
        "is_placeholder": True,
        "asset_source": "generated_placeholder",
        "asset_sha256": "",
        "is_deprecated": False,
        "deprecated_at_utc": None,
        "deprecation_reason": None,
        "provenance": {"factual_source": "seed"},
        "overrides_applied": [],
    }


def _valid_requirement() -> dict:
    return {
        "monster_key": "monster:wublin:zynth",
        "egg_key": "egg:noggin",
        "quantity": 3,
        "source_fingerprint": "",
        "provenance": {"factual_source": "seed"},
        "overrides_applied": [],
    }


def _valid_asset() -> dict:
    return {
        "entity_type": "monster",
        "content_key": "monster:wublin:zynth",
        "relative_path": "images/monsters/zynth.png",
        "sha256": "abcdef0123456789",
        "byte_size": 1024,
        "asset_source": "generated_placeholder",
        "status": "placeholder",
        "is_placeholder": True,
        "license_basis": "internal_generated_placeholder",
        "source_reference": "seed",
        "generated_at_utc": "2026-03-22T00:00:00Z",
    }


# ── Monster schema tests ────────────────────────────────────────────


class TestValidateMonster:
    def test_valid_monster_passes(self):
        r = validate_monster(_valid_monster())
        assert r.ok

    def test_missing_content_key(self):
        m = _valid_monster()
        del m["content_key"]
        r = validate_monster(m)
        assert not r.ok
        assert any(e.field == "content_key" for e in r.errors)

    def test_invalid_content_key_format(self):
        m = _valid_monster()
        m["content_key"] = "bad:format"
        r = validate_monster(m)
        assert not r.ok

    def test_invalid_monster_type(self):
        m = _valid_monster()
        m["monster_type"] = "fire"
        r = validate_monster(m)
        assert not r.ok

    def test_missing_provenance(self):
        m = _valid_monster()
        del m["provenance"]
        r = validate_monster(m)
        assert not r.ok


# ── Egg schema tests ────────────────────────────────────────────────


class TestValidateEgg:
    def test_valid_egg_passes(self):
        r = validate_egg(_valid_egg())
        assert r.ok

    def test_zero_breeding_time_active_egg(self):
        e = _valid_egg()
        e["breeding_time_seconds"] = 0
        r = validate_egg(e)
        assert not r.ok

    def test_invalid_egg_key_format(self):
        e = _valid_egg()
        e["content_key"] = "monster:wublin:wrong"
        r = validate_egg(e)
        assert not r.ok


# ── Requirement schema tests ────────────────────────────────────────


class TestValidateRequirement:
    def test_valid_requirement_passes(self):
        r = validate_requirement(_valid_requirement())
        assert r.ok

    def test_zero_quantity(self):
        req = _valid_requirement()
        req["quantity"] = 0
        r = validate_requirement(req)
        assert not r.ok

    def test_missing_monster_key(self):
        req = _valid_requirement()
        del req["monster_key"]
        r = validate_requirement(req)
        assert not r.ok


# ── Asset schema tests ──────────────────────────────────────────────


class TestValidateAsset:
    def test_valid_asset_passes(self):
        r = validate_asset(_valid_asset())
        assert r.ok

    def test_ui_asset_no_content_key(self):
        a = _valid_asset()
        a["entity_type"] = "ui"
        del a["content_key"]
        a["asset_source"] = "bundled_ui"
        a["status"] = "ui_core"
        a["license_basis"] = "internal_ui_asset"
        r = validate_asset(a)
        assert r.ok


# ── Alias schema tests ──────────────────────────────────────────────


class TestValidateAlias:
    def test_valid_alias(self):
        r = validate_alias({
            "entity_type": "monster",
            "content_key": "monster:wublin:zynth",
            "alias_kind": "display_name",
            "alias_value": "Zynth",
            "is_active": True,
        })
        assert r.ok

    def test_invalid_alias_kind(self):
        r = validate_alias({
            "entity_type": "monster",
            "content_key": "monster:wublin:zynth",
            "alias_kind": "bad_kind",
            "alias_value": "Zynth",
            "is_active": True,
        })
        assert not r.ok


# ── Deprecation schema tests ────────────────────────────────────────


class TestValidateDeprecation:
    def test_valid_deprecation(self):
        r = validate_deprecation({
            "entity_type": "monster",
            "content_key": "monster:wublin:zynth",
            "deprecated_at_utc": "2026-01-01T00:00:00Z",
            "reason_code": "removed_from_game",
            "approved_by": "maintainer",
        })
        assert r.ok

    def test_self_replacement_rejected(self):
        r = validate_deprecation({
            "entity_type": "monster",
            "content_key": "monster:wublin:zynth",
            "deprecated_at_utc": "2026-01-01T00:00:00Z",
            "reason_code": "replaced",
            "replacement_content_key": "monster:wublin:zynth",
            "approved_by": "maintainer",
        })
        assert not r.ok


# ── Review item schema tests ────────────────────────────────────────


class TestValidateReviewItem:
    def test_valid_open_item(self):
        r = validate_review_item({
            "review_id": "rev-001",
            "issue_type": "identity_ambiguous",
            "severity": "error",
            "source_reference": "wiki page X",
            "blocking": True,
            "created_at_utc": "2026-03-22T00:00:00Z",
            "status": "open",
        })
        assert r.ok

    def test_resolved_needs_approver(self):
        r = validate_review_item({
            "review_id": "rev-002",
            "issue_type": "identity_ambiguous",
            "severity": "error",
            "source_reference": "wiki page X",
            "blocking": True,
            "created_at_utc": "2026-03-22T00:00:00Z",
            "status": "resolved",
        })
        assert not r.ok  # needs approved_by and resolution_notes


# ── Collection-level validation tests ────────────────────────────────


class TestCollectionValidation:
    def test_duplicate_monster_keys_rejected(self):
        m1 = _valid_monster()
        m2 = _valid_monster()
        r = validate_monsters_file([m1, m2])
        assert not r.ok

    def test_requirement_referencing_unknown_monster(self):
        req = _valid_requirement()
        r = validate_requirements_file([req], set(), {"egg:noggin"})
        assert not r.ok

    def test_requirement_referencing_unknown_egg(self):
        req = _valid_requirement()
        r = validate_requirements_file([req], {"monster:wublin:zynth"}, set())
        assert not r.ok


# ── Baseline file parity tests ───────────────────────────────────────


class TestBaselineFilesParity:
    """Verify the exported baseline matches expected counts from seed data."""

    def test_monsters_count(self):
        records = load_json_records(NORMALIZED_DIR / "monsters.json")
        assert len(records) == 64  # 20 + 12 + 32

    def test_eggs_count(self):
        records = load_json_records(NORMALIZED_DIR / "eggs.json")
        assert len(records) == 76

    def test_requirements_count(self):
        records = load_json_records(NORMALIZED_DIR / "requirements.json")
        assert len(records) == 806

    def test_type_splits(self):
        records = load_json_records(NORMALIZED_DIR / "monsters.json")
        types = {}
        for r in records:
            t = r["monster_type"]
            types[t] = types.get(t, 0) + 1
        assert types == {"wublin": 20, "celestial": 12, "amber": 32}

    def test_monsters_validate(self):
        records = load_json_records(NORMALIZED_DIR / "monsters.json")
        r = validate_monsters_file(records)
        assert r.ok, [f"[{e.record_index}] {e.field}: {e.message}" for e in r.errors]

    def test_eggs_validate(self):
        records = load_json_records(NORMALIZED_DIR / "eggs.json")
        r = validate_eggs_file(records)
        assert r.ok, [f"[{e.record_index}] {e.field}: {e.message}" for e in r.errors]

    def test_requirements_validate(self):
        monsters = load_json_records(NORMALIZED_DIR / "monsters.json")
        eggs = load_json_records(NORMALIZED_DIR / "eggs.json")
        reqs = load_json_records(NORMALIZED_DIR / "requirements.json")
        mk = {m["content_key"] for m in monsters}
        ek = {e["content_key"] for e in eggs}
        r = validate_requirements_file(reqs, mk, ek)
        assert r.ok, [f"[{e.record_index}] {e.field}: {e.message}" for e in r.errors]


# ── Override tests ───────────────────────────────────────────────────


class TestOverrides:
    def test_load_empty_overrides(self):
        ov = load_overrides(CURATION_DIR / "overrides.yaml")
        assert ov.total == 0

    def test_validate_empty_overrides(self):
        ov = OverrideSet()
        r = validate_overrides(ov)
        assert r.ok

    def test_duplicate_override_id_rejected(self):
        ov = OverrideSet(identity_overrides=[
            {"override_id": "id1", "entity_type": "monster", "target_selector": {},
             "approved_by": "x", "reason": "y", "effective_from_content_version": "1.0"},
            {"override_id": "id1", "entity_type": "monster", "target_selector": {},
             "approved_by": "x", "reason": "y", "effective_from_content_version": "1.0"},
        ])
        r = validate_overrides(ov)
        assert not r.ok


# ── Review queue tests ───────────────────────────────────────────────


class TestReviewQueue:
    def test_load_empty_queue(self):
        items = load_review_queue(REVIEW_DIR / "manual-review-queue.json")
        assert items == []

    def test_no_blocking_items_empty(self):
        assert not has_blocking_items([])

    def test_blocking_open_item(self):
        items = [{
            "review_id": "r1", "issue_type": "identity_ambiguous",
            "severity": "error", "source_reference": "x",
            "blocking": True, "created_at_utc": "2026-01-01",
            "status": "open",
        }]
        assert has_blocking_items(items)

    def test_blocking_resolved_not_blocking(self):
        items = [{
            "review_id": "r1", "issue_type": "identity_ambiguous",
            "severity": "error", "source_reference": "x",
            "blocking": True, "created_at_utc": "2026-01-01",
            "status": "resolved", "approved_by": "me", "resolution_notes": "ok",
        }]
        assert not has_blocking_items(items)
