"""Release artifact generator.

Produces all publish-time artifacts from build outputs:
  - ``manifest.json``
  - ``assets-manifest.json``
  - ``diff-report.json``
  - ``validation-report.json``
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipeline.diff.engine import DiffResult, EntityChange, AssetChange, DiffSummary

logger = logging.getLogger(__name__)

ARTIFACT_CONTRACT_VERSION = "1.1"


# ── Manifest ─────────────────────────────────────────────────────────


def generate_manifest(
    content_version: str,
    content_db_path: Path,
    schema_version: int,
    build_id: str,
    git_sha: str,
    *,
    base_url: str = "https://updates.example.com/msm/stable",
    channel: str = "stable",
    min_client_version: str = "1.0.0",
    rollback_to: str | None = None,
    assets_pack_path: Path | None = None,
) -> dict:
    db_bytes = content_db_path.read_bytes()
    db_sha256 = hashlib.sha256(db_bytes).hexdigest()

    version_url = f"{base_url}/{content_version}"

    manifest: dict[str, Any] = {
        "artifact_contract_version": ARTIFACT_CONTRACT_VERSION,
        "channel": channel,
        "content_version": content_version,
        "published_at_utc": datetime.now(timezone.utc).isoformat(),
        "schema_version": schema_version,
        "min_supported_client_version": min_client_version,
        "content_db_url": f"{version_url}/content.db",
        "content_db_sha256": db_sha256,
        "content_db_size_bytes": len(db_bytes),
        "content_db_required": True,
        "assets_manifest_url": f"{version_url}/assets-manifest.json",
        "assets_pack_optional": True,
        "diff_report_url": f"{version_url}/diff-report.json",
        "validation_report_url": f"{version_url}/validation-report.json",
        "generated_by_build_id": build_id,
        "generated_by_git_sha": git_sha,
    }

    if assets_pack_path and assets_pack_path.exists():
        pack_bytes = assets_pack_path.read_bytes()
        manifest["assets_pack_url"] = f"{version_url}/assets-pack.zip"
        manifest["assets_pack_sha256"] = hashlib.sha256(pack_bytes).hexdigest()
        manifest["assets_pack_size_bytes"] = len(pack_bytes)

    if rollback_to:
        manifest["rollback_to_version"] = rollback_to

    return manifest


# ── Assets manifest ──────────────────────────────────────────────────


def generate_assets_manifest(
    content_version: str,
    build_id: str,
    assets: list[dict],
    *,
    asset_pack_sha256: str | None = None,
) -> dict:
    return {
        "artifact_contract_version": ARTIFACT_CONTRACT_VERSION,
        "content_version": content_version,
        "generated_by_build_id": build_id,
        "asset_pack_present": asset_pack_sha256 is not None,
        "asset_pack_sha256": asset_pack_sha256,
        "assets": assets,
    }


# ── Diff report ──────────────────────────────────────────────────────


def generate_diff_report(
    diff: DiffResult,
    build_id: str,
    review_items: list[dict] | None = None,
) -> dict:
    return {
        "artifact_contract_version": ARTIFACT_CONTRACT_VERSION,
        "previous_content_version": diff.previous_content_version,
        "next_content_version": diff.next_content_version,
        "generated_by_build_id": build_id,
        "summary": asdict(diff.summary),
        "entity_changes": [
            {
                "entity_type": c.entity_type,
                "content_key": c.content_key,
                "change_class": c.change_class,
                "before": c.before,
                "after": c.after,
                "notes": c.notes,
            }
            for c in diff.entity_changes
        ],
        "asset_changes": [
            {
                "content_key": ac.content_key,
                "relative_path_before": ac.relative_path_before,
                "relative_path_after": ac.relative_path_after,
                "change_class": ac.change_class,
                "sha256_before": ac.sha256_before,
                "sha256_after": ac.sha256_after,
                "status_before": ac.status_before,
                "status_after": ac.status_after,
            }
            for ac in diff.asset_changes
        ],
        "manual_review_items": review_items or [],
    }


# ── Validation report ────────────────────────────────────────────────


@dataclass
class ValidationCheck:
    check_id: str
    owner_module: str
    scope: str
    status: str  # pass, fail, warn
    severity: str  # error, warning
    blocking_level: str  # publish_blocker, client_install_blocker, warning_only
    message: str
    details: dict | None = None


def generate_validation_report(
    content_version: str,
    build_id: str,
    checks: list[ValidationCheck],
) -> dict:
    has_fail = any(c.status == "fail" for c in checks)
    has_warn = any(c.status == "warn" for c in checks)
    overall = "fail" if has_fail else ("warn" if has_warn else "pass")

    return {
        "artifact_contract_version": ARTIFACT_CONTRACT_VERSION,
        "content_version": content_version,
        "generated_by_build_id": build_id,
        "overall_status": overall,
        "checks": [
            {
                "check_id": c.check_id,
                "owner_module": c.owner_module,
                "scope": c.scope,
                "status": c.status,
                "severity": c.severity,
                "blocking_level": c.blocking_level,
                "message": c.message,
                **({"details": c.details} if c.details else {}),
            }
            for c in checks
        ],
    }


# ── I/O ──────────────────────────────────────────────────────────────


def write_artifact(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
