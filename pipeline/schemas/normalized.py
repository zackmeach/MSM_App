"""Frozen normalized-content record schemas and validators.

Every record type that flows through the maintainer pipeline is defined here
with exact field names, types, invariants, and validation logic.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ── Content-key regex ────────────────────────────────────────────────

_MONSTER_KEY_RE = re.compile(r"^monster:(wublin|celestial|amber):[a-z0-9]([a-z0-9-]*[a-z0-9])?$")
_EGG_KEY_RE = re.compile(r"^egg:[a-z0-9]([a-z0-9-]*[a-z0-9])?$")

MONSTER_TYPES = {"wublin", "celestial", "amber"}
ASSET_SOURCES = {"bbb_fan_kit", "generated_placeholder"}
ASSET_STATUSES = {"official", "placeholder", "ui_core"}
LICENSE_BASES = {"bbb_fan_kit_policy", "internal_generated_placeholder", "internal_ui_asset"}
ALIAS_KINDS = {"display_name", "source_slug", "legacy_name", "legacy_slug"}
REVIEW_ISSUE_TYPES = {
    "identity_ambiguous", "rename_vs_new_unclear", "replacement_unclear",
    "official_asset_missing", "source_payload_incomplete", "override_required",
}
REVIEW_STATUSES = {"open", "resolved", "wont_fix"}
DEPRECATION_REASON_CODES = {"removed_from_game", "replaced", "merged", "other"}
ENTITY_TYPES = {"monster", "egg", "ui"}


# ── Validation result ────────────────────────────────────────────────


@dataclass
class ValidationError:
    record_index: int | None
    field: str
    message: str


@dataclass
class ValidationResult:
    errors: list[ValidationError] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    def add(self, index: int | None, field_name: str, msg: str) -> None:
        self.errors.append(ValidationError(index, field_name, msg))


# ── Field-level checks ──────────────────────────────────────────────


def _require(record: dict, key: str, expected_type: type, result: ValidationResult, idx: int | None) -> bool:
    if key not in record:
        result.add(idx, key, f"missing required field '{key}'")
        return False
    if not isinstance(record[key], expected_type):
        result.add(idx, key, f"'{key}' must be {expected_type.__name__}, got {type(record[key]).__name__}")
        return False
    return True


def _require_enum(record: dict, key: str, allowed: set[str], result: ValidationResult, idx: int | None) -> bool:
    if not _require(record, key, str, result, idx):
        return False
    if record[key] not in allowed:
        result.add(idx, key, f"'{key}' value '{record[key]}' not in {sorted(allowed)}")
        return False
    return True


def _optional_string(record: dict, key: str, result: ValidationResult, idx: int | None) -> None:
    if key in record and record[key] is not None and not isinstance(record[key], str):
        result.add(idx, key, f"'{key}' must be string or null")


def _require_list_of_strings(record: dict, key: str, result: ValidationResult, idx: int | None) -> None:
    if not _require(record, key, list, result, idx):
        return
    for i, v in enumerate(record[key]):
        if not isinstance(v, str):
            result.add(idx, key, f"'{key}[{i}]' must be string")


def _require_provenance(record: dict, result: ValidationResult, idx: int | None) -> None:
    if "provenance" not in record:
        result.add(idx, "provenance", "missing required field 'provenance'")
        return
    prov = record["provenance"]
    if not isinstance(prov, dict):
        result.add(idx, "provenance", "'provenance' must be an object")


# ── Record-type validators ───────────────────────────────────────────


def validate_monster(record: dict, idx: int | None = None, result: ValidationResult | None = None) -> ValidationResult:
    r = result or ValidationResult()
    _require(record, "content_key", str, r, idx)
    if "content_key" in record and isinstance(record["content_key"], str):
        if not _MONSTER_KEY_RE.match(record["content_key"]):
            r.add(idx, "content_key", f"malformed monster key: '{record['content_key']}'")
    _require(record, "display_name", str, r, idx)
    _require_enum(record, "monster_type", MONSTER_TYPES, r, idx)
    _require(record, "source_slug", str, r, idx)
    _require(record, "source_url", str, r, idx)
    _require(record, "source_fingerprint", str, r, idx)
    _require(record, "wiki_slug", str, r, idx)
    _require(record, "image_path", str, r, idx)
    _require(record, "is_placeholder", bool, r, idx)
    _require_enum(record, "asset_source", ASSET_SOURCES, r, idx)
    _require(record, "asset_sha256", str, r, idx)
    _require(record, "is_deprecated", bool, r, idx)
    _optional_string(record, "deprecated_at_utc", r, idx)
    _optional_string(record, "deprecation_reason", r, idx)
    _require_provenance(record, r, idx)
    _require_list_of_strings(record, "overrides_applied", r, idx)
    return r


def validate_egg(record: dict, idx: int | None = None, result: ValidationResult | None = None) -> ValidationResult:
    r = result or ValidationResult()
    _require(record, "content_key", str, r, idx)
    if "content_key" in record and isinstance(record["content_key"], str):
        if not _EGG_KEY_RE.match(record["content_key"]):
            r.add(idx, "content_key", f"malformed egg key: '{record['content_key']}'")
    _require(record, "display_name", str, r, idx)
    _require(record, "breeding_time_seconds", int, r, idx)
    if "breeding_time_seconds" in record and isinstance(record["breeding_time_seconds"], int):
        if record["breeding_time_seconds"] <= 0 and not record.get("is_deprecated", False):
            r.add(idx, "breeding_time_seconds", "breeding_time_seconds must be > 0 for active eggs")
    _require(record, "breeding_time_display", str, r, idx)
    _require(record, "source_slug", str, r, idx)
    _require(record, "source_url", str, r, idx)
    _require(record, "source_fingerprint", str, r, idx)
    _require(record, "egg_image_path", str, r, idx)
    _require(record, "is_placeholder", bool, r, idx)
    _require_enum(record, "asset_source", ASSET_SOURCES, r, idx)
    _require(record, "asset_sha256", str, r, idx)
    _require(record, "is_deprecated", bool, r, idx)
    _optional_string(record, "deprecated_at_utc", r, idx)
    _optional_string(record, "deprecation_reason", r, idx)
    _require_provenance(record, r, idx)
    _require_list_of_strings(record, "overrides_applied", r, idx)
    return r


def validate_requirement(record: dict, idx: int | None = None, result: ValidationResult | None = None) -> ValidationResult:
    r = result or ValidationResult()
    _require(record, "monster_key", str, r, idx)
    _require(record, "egg_key", str, r, idx)
    _require(record, "quantity", int, r, idx)
    if "quantity" in record and isinstance(record["quantity"], int):
        if record["quantity"] < 1:
            r.add(idx, "quantity", "quantity must be >= 1")
    _require(record, "source_fingerprint", str, r, idx)
    _require_provenance(record, r, idx)
    _require_list_of_strings(record, "overrides_applied", r, idx)
    return r


def validate_asset(record: dict, idx: int | None = None, result: ValidationResult | None = None) -> ValidationResult:
    r = result or ValidationResult()
    _require_enum(record, "entity_type", ENTITY_TYPES, r, idx)
    if record.get("entity_type") in ("monster", "egg"):
        _require(record, "content_key", str, r, idx)
    _require(record, "relative_path", str, r, idx)
    _require(record, "sha256", str, r, idx)
    _require(record, "byte_size", int, r, idx)
    _require_enum(record, "asset_source", ASSET_SOURCES | {"bundled_ui"}, r, idx)
    _require_enum(record, "status", ASSET_STATUSES, r, idx)
    _require(record, "is_placeholder", bool, r, idx)
    _require_enum(record, "license_basis", LICENSE_BASES, r, idx)
    _require(record, "source_reference", str, r, idx)
    _require(record, "generated_at_utc", str, r, idx)
    return r


def validate_alias(record: dict, idx: int | None = None, result: ValidationResult | None = None) -> ValidationResult:
    r = result or ValidationResult()
    _require_enum(record, "entity_type", {"monster", "egg"}, r, idx)
    _require(record, "content_key", str, r, idx)
    _require_enum(record, "alias_kind", ALIAS_KINDS, r, idx)
    _require(record, "alias_value", str, r, idx)
    _require(record, "is_active", bool, r, idx)
    return r


def validate_deprecation(record: dict, idx: int | None = None, result: ValidationResult | None = None) -> ValidationResult:
    r = result or ValidationResult()
    _require_enum(record, "entity_type", {"monster", "egg"}, r, idx)
    _require(record, "content_key", str, r, idx)
    _require(record, "deprecated_at_utc", str, r, idx)
    _require_enum(record, "reason_code", DEPRECATION_REASON_CODES, r, idx)
    _optional_string(record, "replacement_content_key", r, idx)
    _require(record, "approved_by", str, r, idx)
    if "replacement_content_key" in record and record.get("replacement_content_key"):
        if record["replacement_content_key"] == record.get("content_key"):
            r.add(idx, "replacement_content_key", "replacement key cannot equal deprecated key")
    return r


def validate_review_item(record: dict, idx: int | None = None, result: ValidationResult | None = None) -> ValidationResult:
    r = result or ValidationResult()
    _require(record, "review_id", str, r, idx)
    _require_enum(record, "issue_type", REVIEW_ISSUE_TYPES, r, idx)
    _require_enum(record, "severity", {"error", "warning"}, r, idx)
    _require(record, "source_reference", str, r, idx)
    _require(record, "blocking", bool, r, idx)
    _require(record, "created_at_utc", str, r, idx)
    _require_enum(record, "status", REVIEW_STATUSES, r, idx)
    if record.get("status") == "resolved":
        _require(record, "approved_by", str, r, idx)
        _require(record, "resolution_notes", str, r, idx)
    return r


# ── Collection-level validators ──────────────────────────────────────


def validate_monsters_file(records: list[dict]) -> ValidationResult:
    r = ValidationResult()
    keys: set[str] = set()
    for i, rec in enumerate(records):
        validate_monster(rec, idx=i, result=r)
        key = rec.get("content_key", "")
        if key and key in keys:
            r.add(i, "content_key", f"duplicate content_key '{key}'")
        keys.add(key)
    return r


def validate_eggs_file(records: list[dict]) -> ValidationResult:
    r = ValidationResult()
    keys: set[str] = set()
    for i, rec in enumerate(records):
        validate_egg(rec, idx=i, result=r)
        key = rec.get("content_key", "")
        if key and key in keys:
            r.add(i, "content_key", f"duplicate content_key '{key}'")
        keys.add(key)
    return r


def validate_requirements_file(records: list[dict], valid_monster_keys: set[str], valid_egg_keys: set[str]) -> ValidationResult:
    r = ValidationResult()
    seen: set[tuple[str, str]] = set()
    for i, rec in enumerate(records):
        validate_requirement(rec, idx=i, result=r)
        mk = rec.get("monster_key", "")
        ek = rec.get("egg_key", "")
        if mk and mk not in valid_monster_keys:
            r.add(i, "monster_key", f"monster_key '{mk}' not found in monsters")
        if ek and ek not in valid_egg_keys:
            r.add(i, "egg_key", f"egg_key '{ek}' not found in eggs")
        pair = (mk, ek)
        if mk and ek and pair in seen:
            r.add(i, "monster_key+egg_key", f"duplicate requirement ({mk}, {ek})")
        seen.add(pair)
    return r


# ── File I/O helpers ─────────────────────────────────────────────────


def load_json_records(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array")
    return data


def save_json_records(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
        f.write("\n")
