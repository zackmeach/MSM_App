"""Tests for artifact generation and publish-time validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline.publish.artifacts import (
    generate_manifest,
    generate_assets_manifest,
    generate_diff_report,
    generate_validation_report,
    write_artifact,
    ValidationCheck,
    ARTIFACT_CONTRACT_VERSION,
)
from pipeline.validation.checks import (
    check_db_integrity,
    check_required_tables,
    check_required_metadata,
    check_no_orphan_requirements,
    check_unique_content_keys,
    check_no_blocking_review_items,
    check_placeholder_count,
    run_publish_validation,
)
from pipeline.diff.engine import DiffResult, DiffSummary, EntityChange, AssetChange
from pipeline.build.db_builder import build_content_db
from pipeline.schemas.normalized import load_json_records


NORMALIZED_DIR = Path(__file__).resolve().parent.parent.parent / "pipeline" / "normalized"


# ── Helpers ──────────────────────────────────────────────────────────


def _build_test_db(tmp_path: Path) -> Path:
    monsters = load_json_records(NORMALIZED_DIR / "monsters.json")
    eggs = load_json_records(NORMALIZED_DIR / "eggs.json")
    reqs = load_json_records(NORMALIZED_DIR / "requirements.json")
    db_path = tmp_path / "content.db"
    build_content_db(db_path, monsters, eggs, reqs, content_version="1.0.0-test")
    return db_path


# ── Manifest tests ───────────────────────────────────────────────────


class TestManifest:
    def test_manifest_has_required_fields(self, tmp_path: Path):
        db = _build_test_db(tmp_path)
        m = generate_manifest("1.0.0", db, 2, "build-001", "abc123")
        assert m["artifact_contract_version"] == ARTIFACT_CONTRACT_VERSION
        assert m["content_version"] == "1.0.0"
        assert m["content_db_sha256"] and len(m["content_db_sha256"]) == 64
        assert m["content_db_size_bytes"] > 0
        assert m["content_db_required"] is True
        assert m["schema_version"] == 2
        assert m["generated_by_build_id"] == "build-001"

    def test_manifest_without_asset_pack(self, tmp_path: Path):
        db = _build_test_db(tmp_path)
        m = generate_manifest("1.0.0", db, 2, "build-001", "abc123")
        assert "assets_pack_url" not in m
        assert m["assets_pack_optional"] is True

    def test_manifest_with_rollback(self, tmp_path: Path):
        db = _build_test_db(tmp_path)
        m = generate_manifest("1.1.0", db, 2, "build-002", "def456", rollback_to="1.0.0")
        assert m["rollback_to_version"] == "1.0.0"


# ── Assets manifest tests ───────────────────────────────────────────


class TestAssetsManifest:
    def test_basic_structure(self):
        assets = [{"entity_type": "monster", "content_key": "k", "relative_path": "p.png",
                    "sha256": "abc", "byte_size": 100, "asset_source": "generated_placeholder",
                    "status": "placeholder", "is_placeholder": True,
                    "license_basis": "internal_generated_placeholder",
                    "source_reference": "s", "generated_at_utc": "t"}]
        am = generate_assets_manifest("1.0.0", "build-001", assets)
        assert am["artifact_contract_version"] == ARTIFACT_CONTRACT_VERSION
        assert am["content_version"] == "1.0.0"
        assert am["asset_pack_present"] is False
        assert len(am["assets"]) == 1

    def test_with_asset_pack(self):
        am = generate_assets_manifest("1.0.0", "b", [], asset_pack_sha256="deadbeef")
        assert am["asset_pack_present"] is True
        assert am["asset_pack_sha256"] == "deadbeef"


# ── Diff report tests ───────────────────────────────────────────────


class TestDiffReport:
    def test_diff_report_structure(self):
        diff = DiffResult(
            previous_content_version="0.9.0",
            next_content_version="1.0.0",
            summary=DiffSummary(new_monsters=2),
            entity_changes=[
                EntityChange("monster", "monster:wublin:zynth", "new", None, {"name": "Zynth"}, ["new"]),
            ],
            asset_changes=[],
        )
        report = generate_diff_report(diff, "build-001")
        assert report["artifact_contract_version"] == ARTIFACT_CONTRACT_VERSION
        assert report["summary"]["new_monsters"] == 2
        assert len(report["entity_changes"]) == 1
        assert report["entity_changes"][0]["change_class"] == "new"


# ── Validation report tests ─────────────────────────────────────────


class TestValidationReport:
    def test_all_pass(self):
        checks = [
            ValidationCheck("c1", "mod", "scope", "pass", "error", "publish_blocker", "ok"),
        ]
        report = generate_validation_report("1.0.0", "b", checks)
        assert report["overall_status"] == "pass"

    def test_fail_with_warning(self):
        checks = [
            ValidationCheck("c1", "mod", "scope", "pass", "error", "publish_blocker", "ok"),
            ValidationCheck("c2", "mod", "scope", "warn", "warning", "warning_only", "placeholder"),
        ]
        report = generate_validation_report("1.0.0", "b", checks)
        assert report["overall_status"] == "warn"

    def test_fail_overrides_warn(self):
        checks = [
            ValidationCheck("c1", "mod", "scope", "fail", "error", "publish_blocker", "bad"),
            ValidationCheck("c2", "mod", "scope", "warn", "warning", "warning_only", "placeholder"),
        ]
        report = generate_validation_report("1.0.0", "b", checks)
        assert report["overall_status"] == "fail"


# ── Validation checks on real DB ─────────────────────────────────────


class TestValidationChecks:
    def test_integrity_check(self, tmp_path: Path):
        db = _build_test_db(tmp_path)
        c = check_db_integrity(db)
        assert c.status == "pass"

    def test_required_tables(self, tmp_path: Path):
        db = _build_test_db(tmp_path)
        c = check_required_tables(db)
        assert c.status == "pass"

    def test_required_metadata(self, tmp_path: Path):
        db = _build_test_db(tmp_path)
        c = check_required_metadata(db)
        assert c.status == "pass"

    def test_no_orphans(self, tmp_path: Path):
        db = _build_test_db(tmp_path)
        c = check_no_orphan_requirements(db)
        assert c.status == "pass"

    def test_unique_keys(self, tmp_path: Path):
        db = _build_test_db(tmp_path)
        c = check_unique_content_keys(db)
        assert c.status == "pass"

    def test_no_blocking_reviews_empty(self):
        c = check_no_blocking_review_items([])
        assert c.status == "pass"

    def test_blocking_reviews_detected(self):
        items = [{"review_id": "r1", "blocking": True, "status": "open"}]
        c = check_no_blocking_review_items(items)
        assert c.status == "fail"

    def test_placeholder_count_warns(self):
        assets = [{"is_placeholder": True, "entity_type": "monster", "content_key": "k"}]
        c = check_placeholder_count(assets)
        assert c.status == "warn"

    def test_no_placeholders_passes(self):
        assets = [{"is_placeholder": False, "entity_type": "monster", "content_key": "k"}]
        c = check_placeholder_count(assets)
        assert c.status == "pass"


class TestFullPublishValidation:
    def test_full_validation_passes(self, tmp_path: Path):
        db = _build_test_db(tmp_path)
        assets = load_json_records(NORMALIZED_DIR / "assets.json")
        checks = run_publish_validation(db, assets, [])
        statuses = {c.check_id: c.status for c in checks}
        assert statuses["db.integrity"] == "pass"
        assert statuses["db.required_tables"] == "pass"
        assert statuses["db.no_orphan_requirements"] == "pass"
        assert statuses["db.unique_content_keys"] == "pass"
        assert statuses["review.no_blocking_items"] == "pass"
        # placeholder_count will warn because all seed assets are placeholders
        assert statuses["assets.placeholder_count"] == "warn"


# ── Write artifact I/O ───────────────────────────────────────────────


class TestWriteArtifact:
    def test_write_and_read(self, tmp_path: Path):
        data = {"key": "value", "number": 42}
        out = tmp_path / "subdir" / "test.json"
        write_artifact(out, data)
        loaded = json.loads(out.read_text("utf-8"))
        assert loaded == data
