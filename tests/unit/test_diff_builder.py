"""Tests for the semantic diff engine and deterministic DB builder."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from pipeline.diff.engine import (
    diff_monsters,
    diff_eggs,
    diff_requirements,
    diff_assets,
    compute_diff,
    DiffResult,
)
from pipeline.build.db_builder import build_content_db, BuildResult
from pipeline.schemas.normalized import load_json_records


NORMALIZED_DIR = Path(__file__).resolve().parent.parent.parent / "pipeline" / "normalized"


# ── Helpers ──────────────────────────────────────────────────────────

def _mon(key: str, name: str, mtype: str = "wublin", **kw) -> dict:
    base = {
        "content_key": key,
        "display_name": name,
        "monster_type": mtype,
        "source_slug": name,
        "source_url": "",
        "source_fingerprint": "",
        "wiki_slug": name,
        "image_path": f"images/monsters/{name.lower()}.png",
        "is_placeholder": True,
        "asset_source": "generated_placeholder",
        "asset_sha256": "",
        "is_deprecated": False,
        "deprecated_at_utc": None,
        "deprecation_reason": None,
        "provenance": {"factual_source": "test"},
        "overrides_applied": [],
    }
    base.update(kw)
    return base


def _egg(key: str, name: str, time_s: int = 5, **kw) -> dict:
    base = {
        "content_key": key,
        "display_name": name,
        "breeding_time_seconds": time_s,
        "breeding_time_display": f"{time_s}s",
        "source_slug": name,
        "source_url": "",
        "source_fingerprint": "",
        "egg_image_path": f"images/eggs/{name.lower()}_egg.png",
        "is_placeholder": True,
        "asset_source": "generated_placeholder",
        "asset_sha256": "",
        "is_deprecated": False,
        "deprecated_at_utc": None,
        "deprecation_reason": None,
        "provenance": {"factual_source": "test"},
        "overrides_applied": [],
    }
    base.update(kw)
    return base


def _req(mk: str, ek: str, qty: int) -> dict:
    return {
        "monster_key": mk,
        "egg_key": ek,
        "quantity": qty,
        "source_fingerprint": "",
        "provenance": {"factual_source": "test"},
        "overrides_applied": [],
    }


def _asset(key: str, path: str, sha: str = "abc", status: str = "placeholder") -> dict:
    return {
        "entity_type": "monster",
        "content_key": key,
        "relative_path": path,
        "sha256": sha,
        "byte_size": 100,
        "asset_source": "generated_placeholder",
        "status": status,
        "is_placeholder": status == "placeholder",
        "license_basis": "internal_generated_placeholder",
        "source_reference": "test",
        "generated_at_utc": "2026-01-01",
    }


# ── Monster diff tests ──────────────────────────────────────────────


class TestDiffMonsters:
    def test_no_changes(self):
        m = _mon("monster:wublin:zynth", "Zynth")
        changes = diff_monsters([m], [m])
        assert len(changes) == 0

    def test_new_monster(self):
        changes = diff_monsters([], [_mon("monster:wublin:zynth", "Zynth")])
        assert len(changes) == 1
        assert changes[0].change_class == "new"

    def test_deprecated_monster(self):
        m = _mon("monster:wublin:zynth", "Zynth")
        m2 = {**m, "is_deprecated": True, "deprecation_reason": "removed"}
        changes = diff_monsters([m], [m2])
        assert len(changes) == 1
        assert changes[0].change_class == "deprecated"

    def test_revived_monster(self):
        m_dep = _mon("monster:wublin:zynth", "Zynth", is_deprecated=True)
        m_active = _mon("monster:wublin:zynth", "Zynth", is_deprecated=False)
        changes = diff_monsters([m_dep], [m_active])
        assert len(changes) == 1
        assert changes[0].change_class == "revived"

    def test_renamed_monster(self):
        m1 = _mon("monster:wublin:zynth", "Zynth")
        m2 = _mon("monster:wublin:zynth", "Zynth2")
        changes = diff_monsters([m1], [m2])
        assert len(changes) == 1
        assert changes[0].change_class == "rename"

    def test_field_change(self):
        m1 = _mon("monster:wublin:zynth", "Zynth", is_placeholder=True)
        m2 = _mon("monster:wublin:zynth", "Zynth", is_placeholder=False, asset_source="bbb_fan_kit")
        changes = diff_monsters([m1], [m2])
        assert len(changes) == 1
        assert changes[0].change_class == "field_change"

    def test_removed_from_candidate(self):
        m = _mon("monster:wublin:zynth", "Zynth")
        changes = diff_monsters([m], [])
        assert len(changes) == 1
        assert changes[0].change_class == "deprecated"


# ── Egg diff tests ──────────────────────────────────────────────────


class TestDiffEggs:
    def test_no_changes(self):
        e = _egg("egg:noggin", "Noggin")
        assert len(diff_eggs([e], [e])) == 0

    def test_new_egg(self):
        changes = diff_eggs([], [_egg("egg:noggin", "Noggin")])
        assert len(changes) == 1
        assert changes[0].change_class == "new"

    def test_egg_time_change(self):
        e1 = _egg("egg:noggin", "Noggin", time_s=5)
        e2 = _egg("egg:noggin", "Noggin", time_s=10)
        changes = diff_eggs([e1], [e2])
        assert len(changes) == 1
        assert changes[0].change_class == "field_change"

    def test_egg_deprecated_in_place(self):
        e1 = _egg("egg:noggin", "Noggin", is_deprecated=False)
        e2 = _egg("egg:noggin", "Noggin", is_deprecated=True)
        changes = diff_eggs([e1], [e2])
        assert len(changes) == 1
        assert changes[0].change_class == "deprecated"

    def test_egg_revived(self):
        e1 = _egg("egg:noggin", "Noggin", is_deprecated=True)
        e2 = _egg("egg:noggin", "Noggin", is_deprecated=False)
        changes = diff_eggs([e1], [e2])
        assert len(changes) == 1
        assert changes[0].change_class == "revived"

    def test_egg_removed_from_candidate(self):
        e = _egg("egg:noggin", "Noggin")
        changes = diff_eggs([e], [])
        assert len(changes) == 1
        assert changes[0].change_class == "deprecated"

    def test_already_deprecated_egg_removed_no_duplicate(self):
        e = _egg("egg:noggin", "Noggin", is_deprecated=True)
        changes = diff_eggs([e], [])
        assert len(changes) == 0


# ── Requirement diff tests ──────────────────────────────────────────


class TestDiffRequirements:
    def test_no_changes(self):
        r = _req("monster:wublin:zynth", "egg:noggin", 3)
        assert len(diff_requirements([r], [r])) == 0

    def test_quantity_change(self):
        r1 = _req("monster:wublin:zynth", "egg:noggin", 3)
        r2 = _req("monster:wublin:zynth", "egg:noggin", 5)
        changes = diff_requirements([r1], [r2])
        assert len(changes) == 1
        assert changes[0].change_class == "requirements_change"

    def test_new_requirement(self):
        r = _req("monster:wublin:zynth", "egg:mammott", 2)
        changes = diff_requirements([], [r])
        assert len(changes) == 1

    def test_removed_requirement(self):
        r = _req("monster:wublin:zynth", "egg:noggin", 3)
        changes = diff_requirements([r], [])
        assert len(changes) == 1


# ── Asset diff tests ────────────────────────────────────────────────


class TestDiffAssets:
    def test_placeholder_to_official(self):
        a1 = _asset("monster:wublin:zynth", "img/zynth.png", "aaa", "placeholder")
        a2 = _asset("monster:wublin:zynth", "img/zynth.png", "bbb", "official")
        changes = diff_assets([a1], [a2])
        assert len(changes) == 1
        assert changes[0].change_class == "placeholder_to_official"

    def test_official_to_placeholder(self):
        a1 = _asset("monster:wublin:zynth", "img/zynth.png", "aaa", "official")
        a2 = _asset("monster:wublin:zynth", "img/zynth.png", "bbb", "placeholder")
        changes = diff_assets([a1], [a2])
        assert len(changes) == 1
        assert changes[0].change_class == "official_to_placeholder"

    def test_new_asset(self):
        changes = diff_assets([], [_asset("k", "p.png")])
        assert len(changes) == 1
        assert changes[0].change_class == "new"

    def test_empty_hash_to_real_hash_detected(self):
        """First real build: baseline has empty sha256, candidate has computed hash."""
        a1 = _asset("monster:wublin:zynth", "img/zynth.png", "", "placeholder")
        a2 = _asset("monster:wublin:zynth", "img/zynth.png", "abc123", "placeholder")
        changes = diff_assets([a1], [a2])
        assert len(changes) == 1
        assert changes[0].change_class == "hash_changed"

    def test_empty_hash_placeholder_to_official(self):
        """Baseline has empty sha256 placeholder, candidate has real official hash."""
        a1 = _asset("monster:wublin:zynth", "img/zynth.png", "", "placeholder")
        a2 = _asset("monster:wublin:zynth", "img/zynth.png", "abc123", "official")
        changes = diff_assets([a1], [a2])
        assert len(changes) == 1
        assert changes[0].change_class == "placeholder_to_official"

    def test_status_change_same_hash(self):
        """Status changes even when hash doesn't (e.g. metadata correction)."""
        a1 = _asset("monster:wublin:zynth", "img/zynth.png", "abc", "placeholder")
        a2 = _asset("monster:wublin:zynth", "img/zynth.png", "abc", "official")
        changes = diff_assets([a1], [a2])
        assert len(changes) == 1
        assert changes[0].change_class == "placeholder_to_official"

    def test_both_empty_hash_same_status_no_change(self):
        """Identical assets with empty hashes produce no change."""
        a1 = _asset("monster:wublin:zynth", "img/zynth.png", "", "placeholder")
        a2 = _asset("monster:wublin:zynth", "img/zynth.png", "", "placeholder")
        changes = diff_assets([a1], [a2])
        assert len(changes) == 0


# ── Full diff computation tests ─────────────────────────────────────


class TestComputeDiff:
    def test_empty_to_full(self):
        m = [_mon("monster:wublin:zynth", "Zynth")]
        e = [_egg("egg:noggin", "Noggin")]
        r = [_req("monster:wublin:zynth", "egg:noggin", 3)]
        a = [_asset("monster:wublin:zynth", "img/zynth.png")]

        result = compute_diff([], m, [], e, [], r, [], a, "0.0.0", "1.0.0")
        assert result.summary.new_monsters == 1
        assert result.summary.new_eggs == 1
        assert result.summary.requirement_changes == 1

    def test_identical_content_no_changes(self):
        m = [_mon("monster:wublin:zynth", "Zynth")]
        e = [_egg("egg:noggin", "Noggin")]
        r = [_req("monster:wublin:zynth", "egg:noggin", 3)]
        a = [_asset("monster:wublin:zynth", "img/zynth.png")]

        result = compute_diff(m, m, e, e, r, r, a, a, "1.0.0", "1.0.1")
        assert len(result.entity_changes) == 0
        assert len(result.asset_changes) == 0


# ── Deterministic DB builder tests ──────────────────────────────────


class TestDBBuilder:
    def test_build_from_normalized_baseline(self, tmp_path: Path):
        monsters = load_json_records(NORMALIZED_DIR / "monsters.json")
        eggs = load_json_records(NORMALIZED_DIR / "eggs.json")
        reqs = load_json_records(NORMALIZED_DIR / "requirements.json")

        result = build_content_db(
            tmp_path / "content.db", monsters, eggs, reqs,
            content_version="1.0.0-test",
        )
        assert result.monster_count == 64
        assert result.egg_count == 76
        assert result.requirement_count == 806

        conn = sqlite3.connect(str(tmp_path / "content.db"))
        v = conn.execute("SELECT value FROM update_metadata WHERE key='content_version'").fetchone()
        assert v[0] == "1.0.0-test"
        conn.close()

    def test_deterministic_build(self, tmp_path: Path):
        """Same input produces identical output."""
        monsters = load_json_records(NORMALIZED_DIR / "monsters.json")
        eggs = load_json_records(NORMALIZED_DIR / "eggs.json")
        reqs = load_json_records(NORMALIZED_DIR / "requirements.json")

        r1 = build_content_db(tmp_path / "db1.db", monsters, eggs, reqs, content_version="1.0.0")
        r2 = build_content_db(tmp_path / "db2.db", monsters, eggs, reqs, content_version="1.0.0")
        assert r1.monster_count == r2.monster_count
        assert r1.egg_count == r2.egg_count
        assert r1.requirement_count == r2.requirement_count

    def test_id_preservation_from_baseline(self, tmp_path: Path):
        monsters = load_json_records(NORMALIZED_DIR / "monsters.json")
        eggs = load_json_records(NORMALIZED_DIR / "eggs.json")
        reqs = load_json_records(NORMALIZED_DIR / "requirements.json")

        baseline_path = tmp_path / "baseline.db"
        build_content_db(baseline_path, monsters, eggs, reqs, content_version="1.0.0")

        result = build_content_db(
            tmp_path / "next.db", monsters, eggs, reqs,
            content_version="1.1.0",
            baseline_db_path=baseline_path,
        )
        assert result.id_preserved > 0
        assert result.id_reassigned == 0

    def test_content_keys_populated(self, tmp_path: Path):
        monsters = [_mon("monster:wublin:zynth", "Zynth")]
        eggs = [_egg("egg:noggin", "Noggin")]
        reqs = [_req("monster:wublin:zynth", "egg:noggin", 3)]

        build_content_db(tmp_path / "test.db", monsters, eggs, reqs)

        conn = sqlite3.connect(str(tmp_path / "test.db"))
        mk = conn.execute("SELECT content_key FROM monsters").fetchone()[0]
        ek = conn.execute("SELECT content_key FROM egg_types").fetchone()[0]
        conn.close()
        assert mk == "monster:wublin:zynth"
        assert ek == "egg:noggin"
