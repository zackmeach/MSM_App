"""Override file loader and validator.

Override files are YAML documents under ``pipeline/curation/`` that let
maintainers force identity assignments, field corrections, asset
classifications, and other curator-level decisions that override raw-source
data.
"""

from __future__ import annotations

import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pipeline.schemas.normalized import ValidationResult


OVERRIDE_SECTIONS = {
    "identity_overrides",
    "field_overrides",
    "asset_overrides",
    "classification_overrides",
}

_REQUIRED_OVERRIDE_FIELDS = {
    "override_id", "entity_type", "target_selector", "approved_by",
    "reason", "effective_from_content_version",
}


@dataclass
class OverrideSet:
    identity_overrides: list[dict] = field(default_factory=list)
    field_overrides: list[dict] = field(default_factory=list)
    asset_overrides: list[dict] = field(default_factory=list)
    classification_overrides: list[dict] = field(default_factory=list)

    @property
    def total(self) -> int:
        return (
            len(self.identity_overrides)
            + len(self.field_overrides)
            + len(self.asset_overrides)
            + len(self.classification_overrides)
        )


def load_overrides(path: Path) -> OverrideSet:
    if not path.exists():
        return OverrideSet()
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return OverrideSet(
        identity_overrides=data.get("identity_overrides", []) or [],
        field_overrides=data.get("field_overrides", []) or [],
        asset_overrides=data.get("asset_overrides", []) or [],
        classification_overrides=data.get("classification_overrides", []) or [],
    )


def validate_overrides(overrides: OverrideSet) -> ValidationResult:
    r = ValidationResult()
    all_sections = [
        ("identity_overrides", overrides.identity_overrides),
        ("field_overrides", overrides.field_overrides),
        ("asset_overrides", overrides.asset_overrides),
        ("classification_overrides", overrides.classification_overrides),
    ]
    seen_ids: set[str] = set()
    for section_name, entries in all_sections:
        for i, entry in enumerate(entries):
            if not isinstance(entry, dict):
                r.add(i, section_name, f"entry must be a mapping, got {type(entry).__name__}")
                continue
            for req in _REQUIRED_OVERRIDE_FIELDS:
                if req not in entry:
                    r.add(i, req, f"missing required override field '{req}' in {section_name}")
            oid = entry.get("override_id", "")
            if oid:
                if oid in seen_ids:
                    r.add(i, "override_id", f"duplicate override_id '{oid}'")
                seen_ids.add(oid)
    return r
