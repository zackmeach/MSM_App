"""Semantic diff engine for content releases.

Compares two sets of normalized content (baseline vs candidate) keyed by
``content_key`` and classifies each difference into a change class.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


ENTITY_CHANGE_CLASSES = {
    "new", "rename", "field_change", "requirements_change",
    "deprecated", "revived", "replacement",
}

ASSET_CHANGE_CLASSES = {
    "new", "removed", "hash_changed", "placeholder_to_official",
    "official_to_placeholder", "path_changed",
}


@dataclass
class EntityChange:
    entity_type: str
    content_key: str
    change_class: str
    before: dict | None
    after: dict | None
    notes: list[str] = field(default_factory=list)


@dataclass
class AssetChange:
    content_key: str
    relative_path_before: str | None
    relative_path_after: str | None
    change_class: str
    sha256_before: str | None
    sha256_after: str | None
    status_before: str | None
    status_after: str | None


@dataclass
class DiffSummary:
    new_monsters: int = 0
    changed_monsters: int = 0
    deprecated_monsters: int = 0
    revived_monsters: int = 0
    new_eggs: int = 0
    changed_eggs: int = 0
    deprecated_eggs: int = 0
    requirement_changes: int = 0
    official_to_placeholder_downgrades: int = 0
    placeholder_to_official_upgrades: int = 0


@dataclass
class DiffResult:
    previous_content_version: str
    next_content_version: str
    summary: DiffSummary = field(default_factory=DiffSummary)
    entity_changes: list[EntityChange] = field(default_factory=list)
    asset_changes: list[AssetChange] = field(default_factory=list)


def diff_monsters(
    baseline: list[dict],
    candidate: list[dict],
) -> list[EntityChange]:
    base_map = {m["content_key"]: m for m in baseline}
    cand_map = {m["content_key"]: m for m in candidate}
    changes: list[EntityChange] = []

    for key, cand in cand_map.items():
        if key not in base_map:
            changes.append(EntityChange(
                entity_type="monster",
                content_key=key,
                change_class="new",
                before=None,
                after=cand,
                notes=[f"New monster: {cand.get('display_name', key)}"],
            ))
            continue

        base = base_map[key]
        diffs = _field_diffs(base, cand, ["display_name", "monster_type", "wiki_slug",
                                           "image_path", "is_placeholder", "asset_source"])

        if base.get("is_deprecated") and not cand.get("is_deprecated"):
            changes.append(EntityChange(
                entity_type="monster",
                content_key=key,
                change_class="revived",
                before=base,
                after=cand,
                notes=["Monster revived from deprecated state"],
            ))
        elif not base.get("is_deprecated") and cand.get("is_deprecated"):
            changes.append(EntityChange(
                entity_type="monster",
                content_key=key,
                change_class="deprecated",
                before=base,
                after=cand,
                notes=[f"Monster deprecated: {cand.get('deprecation_reason', 'no reason')}"],
            ))
        elif base.get("display_name") != cand.get("display_name"):
            changes.append(EntityChange(
                entity_type="monster",
                content_key=key,
                change_class="rename",
                before=base,
                after=cand,
                notes=[f"Renamed: {base.get('display_name')} -> {cand.get('display_name')}"],
            ))
        elif diffs:
            changes.append(EntityChange(
                entity_type="monster",
                content_key=key,
                change_class="field_change",
                before=base,
                after=cand,
                notes=diffs,
            ))

    for key in base_map:
        if key not in cand_map:
            base = base_map[key]
            if not base.get("is_deprecated"):
                changes.append(EntityChange(
                    entity_type="monster",
                    content_key=key,
                    change_class="deprecated",
                    before=base,
                    after=None,
                    notes=["Monster removed from candidate content"],
                ))

    return changes


def diff_eggs(
    baseline: list[dict],
    candidate: list[dict],
) -> list[EntityChange]:
    base_map = {e["content_key"]: e for e in baseline}
    cand_map = {e["content_key"]: e for e in candidate}
    changes: list[EntityChange] = []

    for key, cand in cand_map.items():
        if key not in base_map:
            changes.append(EntityChange(
                entity_type="egg",
                content_key=key,
                change_class="new",
                before=None,
                after=cand,
                notes=[f"New egg type: {cand.get('display_name', key)}"],
            ))
            continue

        base = base_map[key]
        diffs = _field_diffs(base, cand, ["display_name", "breeding_time_seconds",
                                           "breeding_time_display", "egg_image_path",
                                           "is_placeholder", "asset_source",
                                           "is_deprecated"])

        if base.get("is_deprecated") and not cand.get("is_deprecated"):
            changes.append(EntityChange(
                entity_type="egg",
                content_key=key,
                change_class="revived",
                before=base,
                after=cand,
                notes=["Egg type revived from deprecated state"],
            ))
        elif not base.get("is_deprecated") and cand.get("is_deprecated"):
            changes.append(EntityChange(
                entity_type="egg",
                content_key=key,
                change_class="deprecated",
                before=base,
                after=cand,
                notes=[f"Egg type deprecated: {cand.get('deprecation_reason', 'no reason')}"],
            ))
        elif diffs:
            changes.append(EntityChange(
                entity_type="egg",
                content_key=key,
                change_class="field_change",
                before=base,
                after=cand,
                notes=diffs,
            ))

    for key in base_map:
        if key not in cand_map:
            base = base_map[key]
            if not base.get("is_deprecated"):
                changes.append(EntityChange(
                    entity_type="egg",
                    content_key=key,
                    change_class="deprecated",
                    before=base,
                    after=None,
                    notes=["Egg type removed from candidate content"],
                ))

    return changes


def diff_requirements(
    baseline: list[dict],
    candidate: list[dict],
) -> list[EntityChange]:
    def _req_key(r: dict) -> tuple[str, str]:
        return (r["monster_key"], r["egg_key"])

    base_map = {_req_key(r): r for r in baseline}
    cand_map = {_req_key(r): r for r in candidate}
    changes: list[EntityChange] = []

    for key, cand in cand_map.items():
        if key not in base_map:
            changes.append(EntityChange(
                entity_type="monster",
                content_key=key[0],
                change_class="requirements_change",
                before=None,
                after=cand,
                notes=[f"New requirement: {key[1]} x{cand['quantity']}"],
            ))
        else:
            base = base_map[key]
            if base["quantity"] != cand["quantity"]:
                changes.append(EntityChange(
                    entity_type="monster",
                    content_key=key[0],
                    change_class="requirements_change",
                    before=base,
                    after=cand,
                    notes=[f"Quantity changed for {key[1]}: {base['quantity']} -> {cand['quantity']}"],
                ))

    for key in base_map:
        if key not in cand_map:
            base = base_map[key]
            changes.append(EntityChange(
                entity_type="monster",
                content_key=key[0],
                change_class="requirements_change",
                before=base,
                after=None,
                notes=[f"Requirement removed: {key[1]}"],
            ))

    return changes


def diff_assets(
    baseline: list[dict],
    candidate: list[dict],
) -> list[AssetChange]:
    base_map = {a["relative_path"]: a for a in baseline}
    cand_map = {a["relative_path"]: a for a in candidate}
    changes: list[AssetChange] = []

    for path, cand in cand_map.items():
        if path not in base_map:
            changes.append(AssetChange(
                content_key=cand.get("content_key", ""),
                relative_path_before=None,
                relative_path_after=path,
                change_class="new",
                sha256_before=None,
                sha256_after=cand.get("sha256"),
                status_before=None,
                status_after=cand.get("status"),
            ))
            continue

        base = base_map[path]
        hash_changed = base.get("sha256", "") != cand.get("sha256", "")
        status_changed = base.get("status") != cand.get("status")
        if hash_changed or status_changed:
            if base.get("status") == "placeholder" and cand.get("status") == "official":
                cls = "placeholder_to_official"
            elif base.get("status") == "official" and cand.get("status") == "placeholder":
                cls = "official_to_placeholder"
            elif hash_changed:
                cls = "hash_changed"
            else:
                cls = "hash_changed"
            changes.append(AssetChange(
                content_key=cand.get("content_key", ""),
                relative_path_before=path,
                relative_path_after=path,
                change_class=cls,
                sha256_before=base.get("sha256"),
                sha256_after=cand.get("sha256"),
                status_before=base.get("status"),
                status_after=cand.get("status"),
            ))

    for path in base_map:
        if path not in cand_map:
            base = base_map[path]
            changes.append(AssetChange(
                content_key=base.get("content_key", ""),
                relative_path_before=path,
                relative_path_after=None,
                change_class="removed",
                sha256_before=base.get("sha256"),
                sha256_after=None,
                status_before=base.get("status"),
                status_after=None,
            ))

    return changes


def compute_diff(
    baseline_monsters: list[dict],
    candidate_monsters: list[dict],
    baseline_eggs: list[dict],
    candidate_eggs: list[dict],
    baseline_requirements: list[dict],
    candidate_requirements: list[dict],
    baseline_assets: list[dict],
    candidate_assets: list[dict],
    previous_version: str,
    next_version: str,
) -> DiffResult:
    monster_changes = diff_monsters(baseline_monsters, candidate_monsters)
    egg_changes = diff_eggs(baseline_eggs, candidate_eggs)
    req_changes = diff_requirements(baseline_requirements, candidate_requirements)
    asset_changes = diff_assets(baseline_assets, candidate_assets)

    summary = DiffSummary()
    for c in monster_changes:
        if c.change_class == "new":
            summary.new_monsters += 1
        elif c.change_class == "deprecated":
            summary.deprecated_monsters += 1
        elif c.change_class == "revived":
            summary.revived_monsters += 1
        elif c.change_class in ("field_change", "rename"):
            summary.changed_monsters += 1
    for c in egg_changes:
        if c.change_class == "new":
            summary.new_eggs += 1
        elif c.change_class == "deprecated":
            summary.deprecated_eggs += 1
        elif c.change_class == "field_change":
            summary.changed_eggs += 1
    summary.requirement_changes = len(req_changes)
    for ac in asset_changes:
        if ac.change_class == "placeholder_to_official":
            summary.placeholder_to_official_upgrades += 1
        elif ac.change_class == "official_to_placeholder":
            summary.official_to_placeholder_downgrades += 1

    return DiffResult(
        previous_content_version=previous_version,
        next_content_version=next_version,
        summary=summary,
        entity_changes=monster_changes + egg_changes + req_changes,
        asset_changes=asset_changes,
    )


def _field_diffs(base: dict, cand: dict, fields: list[str]) -> list[str]:
    diffs = []
    for f in fields:
        bv = base.get(f)
        cv = cand.get(f)
        if bv != cv:
            diffs.append(f"{f}: {bv!r} -> {cv!r}")
    return diffs
