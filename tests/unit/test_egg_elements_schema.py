"""Tests for egg_elements.json schema validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pipeline.validation.checks import (
    check_egg_elements_schema,
    run_publish_validation,
)

ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMA = ROOT / "pipeline" / "schemas" / "egg_elements.schema.json"
DATA = ROOT / "pipeline" / "normalized" / "egg_elements.json"


def test_real_egg_elements_passes_schema():
    if not (SCHEMA.exists() and DATA.exists()):
        pytest.skip("Schema or data file missing")
    result = check_egg_elements_schema(DATA, SCHEMA)
    assert result.status == "pass", result.message


def test_typo_in_element_key_fails(tmp_path: Path):
    if not SCHEMA.exists():
        pytest.skip("Schema file missing")
    bad = tmp_path / "egg_elements.json"
    bad.write_text(json.dumps({
        "elements": {"egg:noggin": ["naturl-plant"]}
    }), encoding="utf-8")
    result = check_egg_elements_schema(bad, SCHEMA)
    assert result.status == "fail"


def test_missing_elements_object_fails(tmp_path: Path):
    if not SCHEMA.exists():
        pytest.skip("Schema file missing")
    bad = tmp_path / "egg_elements.json"
    bad.write_text(json.dumps({"_comment": "no elements"}), encoding="utf-8")
    result = check_egg_elements_schema(bad, SCHEMA)
    assert result.status == "fail"


def test_invalid_egg_key_pattern_fails(tmp_path: Path):
    if not SCHEMA.exists():
        pytest.skip("Schema file missing")
    bad = tmp_path / "egg_elements.json"
    bad.write_text(json.dumps({
        "elements": {"NOT_AN_EGG_KEY": ["natural-plant"]}
    }), encoding="utf-8")
    result = check_egg_elements_schema(bad, SCHEMA)
    assert result.status == "fail"


def test_missing_egg_elements_file_passes_with_warning(tmp_path: Path):
    """Absent data file is allowed — element pips just don't render."""
    if not SCHEMA.exists():
        pytest.skip("Schema file missing")
    nonexistent = tmp_path / "no_such_file.json"
    result = check_egg_elements_schema(nonexistent, SCHEMA)
    assert result.status == "pass"


def _check_ids(checks):
    return {c.check_id for c in checks}


def test_publish_validation_includes_schema_check_when_paths_passed():
    """The publish pipeline must wire the schema check; otherwise it's dead code."""
    bundled_db = ROOT / "resources" / "db" / "content.db"
    if not (bundled_db.exists() and SCHEMA.exists() and DATA.exists()):
        pytest.skip("Bundled DB / schema / data missing")

    checks = run_publish_validation(
        bundled_db,
        assets=[],
        review_items=[],
        egg_elements_path=DATA,
        schema_path=SCHEMA,
    )
    assert "data.egg_elements_schema" in _check_ids(checks)


def test_publish_validation_omits_schema_check_when_paths_absent():
    """Backward-compatible: callers that don't pass paths still get the original list."""
    bundled_db = ROOT / "resources" / "db" / "content.db"
    if not bundled_db.exists():
        pytest.skip("Bundled DB missing")

    checks = run_publish_validation(bundled_db, assets=[], review_items=[])
    assert "data.egg_elements_schema" not in _check_ids(checks)
