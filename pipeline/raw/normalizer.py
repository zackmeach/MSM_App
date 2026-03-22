"""Normalization transforms from raw source payloads to canonical records.

Takes raw cached payloads and produces normalized monster/egg/requirement
records, emitting manual review items when identity is ambiguous.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.domain.models import canonical_slug, monster_content_key, egg_content_key
from pipeline.schemas.normalized import (
    validate_monster,
    validate_egg,
    validate_requirement,
)

logger = logging.getLogger(__name__)


@dataclass
class NormalizationResult:
    monsters: list[dict] = field(default_factory=list)
    eggs: list[dict] = field(default_factory=list)
    requirements: list[dict] = field(default_factory=list)
    review_items: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def normalize_monster_payload(
    raw_payload: dict[str, Any],
    source_category: str,
    source_reference: str,
    content_hash: str,
    retrieved_at_utc: str,
    existing_keys: set[str] | None = None,
    aliases: dict[str, str] | None = None,
    overrides: dict[str, dict] | None = None,
) -> tuple[dict | None, list[dict]]:
    """Normalize a single raw monster payload into a canonical record.

    Returns (normalized_record_or_None, review_items).
    """
    review_items: list[dict] = []
    keys = existing_keys or set()
    alias_map = aliases or {}
    override_map = overrides or {}

    name = raw_payload.get("name", "").strip()
    monster_type = raw_payload.get("monster_type", "").strip().lower()
    wiki_slug = raw_payload.get("wiki_slug", name)
    source_slug = raw_payload.get("source_slug", wiki_slug)

    if not name or not monster_type:
        review_items.append(_make_review_item(
            "source_payload_incomplete",
            "error",
            source_reference,
            blocking=True,
            notes=f"Missing name or type in raw payload: {raw_payload}",
        ))
        return None, review_items

    key = monster_content_key(monster_type, name)

    if key in alias_map:
        key = alias_map[key]

    override_key = f"monster:{monster_type}:{canonical_slug(name)}"
    applied_overrides: list[str] = []
    if override_key in override_map:
        ov = override_map[override_key]
        if "forced_content_key" in ov:
            key = ov["forced_content_key"]
            applied_overrides.append(ov.get("override_id", "unknown"))

    if key in keys:
        review_items.append(_make_review_item(
            "identity_ambiguous",
            "error",
            source_reference,
            blocking=True,
            candidate_key=key,
            notes=f"Duplicate content_key '{key}' found during normalization",
        ))
        return None, review_items

    image_path = raw_payload.get("image_path", f"images/monsters/{canonical_slug(name)}.png")
    source_fp = hashlib.sha256(json.dumps(raw_payload, sort_keys=True).encode()).hexdigest()

    record = {
        "content_key": key,
        "display_name": name,
        "monster_type": monster_type,
        "source_slug": source_slug,
        "source_url": raw_payload.get("source_url", ""),
        "source_fingerprint": f"sha256:{source_fp}",
        "wiki_slug": wiki_slug,
        "image_path": image_path,
        "is_placeholder": raw_payload.get("is_placeholder", True),
        "asset_source": raw_payload.get("asset_source", "generated_placeholder"),
        "asset_sha256": raw_payload.get("asset_sha256", ""),
        "is_deprecated": raw_payload.get("is_deprecated", False),
        "deprecated_at_utc": raw_payload.get("deprecated_at_utc"),
        "deprecation_reason": raw_payload.get("deprecation_reason"),
        "provenance": {
            "factual_source": source_category,
            "retrieved_at_utc": retrieved_at_utc,
            "raw_snapshot_id": f"raw-{content_hash[:12]}",
        },
        "overrides_applied": applied_overrides,
    }

    return record, review_items


def normalize_egg_payload(
    raw_payload: dict[str, Any],
    source_category: str,
    source_reference: str,
    content_hash: str,
    retrieved_at_utc: str,
) -> tuple[dict | None, list[dict]]:
    """Normalize a single raw egg payload into a canonical record."""
    review_items: list[dict] = []

    name = raw_payload.get("name", "").strip()
    if not name:
        review_items.append(_make_review_item(
            "source_payload_incomplete",
            "error",
            source_reference,
            blocking=True,
            notes=f"Missing egg name in raw payload: {raw_payload}",
        ))
        return None, review_items

    breeding_time = raw_payload.get("breeding_time_seconds", 0)
    if not isinstance(breeding_time, int) or breeding_time <= 0:
        review_items.append(_make_review_item(
            "source_payload_incomplete",
            "warning",
            source_reference,
            blocking=False,
            notes=f"Invalid breeding_time_seconds for egg '{name}'",
        ))

    key = egg_content_key(name)
    source_fp = hashlib.sha256(json.dumps(raw_payload, sort_keys=True).encode()).hexdigest()

    record = {
        "content_key": key,
        "display_name": name,
        "breeding_time_seconds": breeding_time,
        "breeding_time_display": raw_payload.get("breeding_time_display", ""),
        "source_slug": raw_payload.get("source_slug", name),
        "source_url": raw_payload.get("source_url", ""),
        "source_fingerprint": f"sha256:{source_fp}",
        "egg_image_path": raw_payload.get("egg_image_path", f"images/eggs/{canonical_slug(name)}_egg.png"),
        "is_placeholder": raw_payload.get("is_placeholder", True),
        "asset_source": raw_payload.get("asset_source", "generated_placeholder"),
        "asset_sha256": raw_payload.get("asset_sha256", ""),
        "is_deprecated": raw_payload.get("is_deprecated", False),
        "deprecated_at_utc": raw_payload.get("deprecated_at_utc"),
        "deprecation_reason": raw_payload.get("deprecation_reason"),
        "provenance": {
            "factual_source": source_category,
            "retrieved_at_utc": retrieved_at_utc,
            "raw_snapshot_id": f"raw-{content_hash[:12]}",
        },
        "overrides_applied": [],
    }

    return record, review_items


def _make_review_item(
    issue_type: str,
    severity: str,
    source_reference: str,
    *,
    blocking: bool,
    candidate_key: str = "",
    notes: str = "",
) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    review_id = f"auto-{hashlib.sha256(f'{issue_type}:{source_reference}:{candidate_key}:{now}'.encode()).hexdigest()[:12]}"
    item: dict[str, Any] = {
        "review_id": review_id,
        "issue_type": issue_type,
        "severity": severity,
        "source_reference": source_reference,
        "blocking": blocking,
        "created_at_utc": now,
        "status": "open",
    }
    if candidate_key:
        item["candidate_content_key"] = candidate_key
    if notes:
        item["proposed_resolution"] = notes
    return item
