"""Publish-time and install-time validation checks.

Each check returns a ``ValidationCheck`` that gets aggregated into the
``validation-report.json``.
"""

from __future__ import annotations

import sqlite3
import logging
from pathlib import Path

from pipeline.publish.artifacts import ValidationCheck

logger = logging.getLogger(__name__)


def check_db_integrity(db_path: Path) -> ValidationCheck:
    try:
        conn = sqlite3.connect(str(db_path))
        result = conn.execute("PRAGMA integrity_check").fetchone()
        conn.close()
        ok = result and result[0] == "ok"
        return ValidationCheck(
            check_id="db.integrity",
            owner_module="pipeline.validation.content_db",
            scope="content.db",
            status="pass" if ok else "fail",
            severity="error",
            blocking_level="publish_blocker",
            message="SQLite integrity check returned ok" if ok else f"Integrity check failed: {result}",
        )
    except Exception as e:
        return ValidationCheck(
            check_id="db.integrity",
            owner_module="pipeline.validation.content_db",
            scope="content.db",
            status="fail",
            severity="error",
            blocking_level="publish_blocker",
            message=f"Integrity check exception: {e}",
        )


def check_required_tables(db_path: Path) -> ValidationCheck:
    required = {"monsters", "egg_types", "monster_requirements", "update_metadata"}
    try:
        conn = sqlite3.connect(str(db_path))
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        conn.close()
        missing = required - tables
        if missing:
            return ValidationCheck(
                check_id="db.required_tables",
                owner_module="pipeline.validation.content_db",
                scope="content.db",
                status="fail",
                severity="error",
                blocking_level="publish_blocker",
                message=f"Missing required tables: {sorted(missing)}",
            )
        return ValidationCheck(
            check_id="db.required_tables",
            owner_module="pipeline.validation.content_db",
            scope="content.db",
            status="pass",
            severity="error",
            blocking_level="publish_blocker",
            message="All required tables present",
        )
    except Exception as e:
        return ValidationCheck(
            check_id="db.required_tables",
            owner_module="pipeline.validation.content_db",
            scope="content.db",
            status="fail",
            severity="error",
            blocking_level="publish_blocker",
            message=f"Table check exception: {e}",
        )


def check_required_metadata(db_path: Path) -> ValidationCheck:
    required_keys = {"content_version", "last_updated_utc", "source"}
    try:
        conn = sqlite3.connect(str(db_path))
        meta = {r[0]: r[1] for r in conn.execute("SELECT key, value FROM update_metadata").fetchall()}
        conn.close()
        missing = required_keys - set(meta.keys())
        empty = {k for k in required_keys if k in meta and not meta[k].strip()}
        issues = missing | empty
        if issues:
            return ValidationCheck(
                check_id="db.required_metadata",
                owner_module="pipeline.validation.content_db",
                scope="content.db",
                status="fail",
                severity="error",
                blocking_level="publish_blocker",
                message=f"Missing or empty metadata keys: {sorted(issues)}",
            )
        return ValidationCheck(
            check_id="db.required_metadata",
            owner_module="pipeline.validation.content_db",
            scope="content.db",
            status="pass",
            severity="error",
            blocking_level="publish_blocker",
            message="All required metadata keys present and non-empty",
        )
    except Exception as e:
        return ValidationCheck(
            check_id="db.required_metadata",
            owner_module="pipeline.validation.content_db",
            scope="content.db",
            status="fail",
            severity="error",
            blocking_level="publish_blocker",
            message=f"Metadata check exception: {e}",
        )


def check_no_orphan_requirements(db_path: Path) -> ValidationCheck:
    try:
        conn = sqlite3.connect(str(db_path))
        orphan_monsters = conn.execute(
            "SELECT COUNT(*) FROM monster_requirements mr "
            "LEFT JOIN monsters m ON mr.monster_id = m.id WHERE m.id IS NULL"
        ).fetchone()[0]
        orphan_eggs = conn.execute(
            "SELECT COUNT(*) FROM monster_requirements mr "
            "LEFT JOIN egg_types e ON mr.egg_type_id = e.id WHERE e.id IS NULL"
        ).fetchone()[0]
        conn.close()
        total = orphan_monsters + orphan_eggs
        if total > 0:
            return ValidationCheck(
                check_id="db.no_orphan_requirements",
                owner_module="pipeline.validation.content_db",
                scope="content.db",
                status="fail",
                severity="error",
                blocking_level="publish_blocker",
                message=f"Found {total} orphan requirement refs ({orphan_monsters} monster, {orphan_eggs} egg)",
            )
        return ValidationCheck(
            check_id="db.no_orphan_requirements",
            owner_module="pipeline.validation.content_db",
            scope="content.db",
            status="pass",
            severity="error",
            blocking_level="publish_blocker",
            message="No orphan requirement references",
        )
    except Exception as e:
        return ValidationCheck(
            check_id="db.no_orphan_requirements",
            owner_module="pipeline.validation.content_db",
            scope="content.db",
            status="fail",
            severity="error",
            blocking_level="publish_blocker",
            message=f"Orphan check exception: {e}",
        )


def check_unique_content_keys(db_path: Path) -> ValidationCheck:
    try:
        conn = sqlite3.connect(str(db_path))
        dup_monsters = conn.execute(
            "SELECT content_key, COUNT(*) c FROM monsters "
            "WHERE content_key != '' GROUP BY content_key HAVING c > 1"
        ).fetchall()
        dup_eggs = conn.execute(
            "SELECT content_key, COUNT(*) c FROM egg_types "
            "WHERE content_key != '' GROUP BY content_key HAVING c > 1"
        ).fetchall()
        conn.close()
        dups = dup_monsters + dup_eggs
        if dups:
            keys = [r[0] for r in dups]
            return ValidationCheck(
                check_id="db.unique_content_keys",
                owner_module="pipeline.validation.identity",
                scope="content.db",
                status="fail",
                severity="error",
                blocking_level="publish_blocker",
                message=f"Duplicate content_keys found: {keys}",
            )
        return ValidationCheck(
            check_id="db.unique_content_keys",
            owner_module="pipeline.validation.identity",
            scope="content.db",
            status="pass",
            severity="error",
            blocking_level="publish_blocker",
            message="All content_keys are unique",
        )
    except Exception as e:
        return ValidationCheck(
            check_id="db.unique_content_keys",
            owner_module="pipeline.validation.identity",
            scope="content.db",
            status="fail",
            severity="error",
            blocking_level="publish_blocker",
            message=f"Unique key check exception: {e}",
        )


def check_no_blocking_review_items(review_items: list[dict]) -> ValidationCheck:
    blocking = [
        item for item in review_items
        if item.get("blocking") and item.get("status") == "open"
    ]
    if blocking:
        return ValidationCheck(
            check_id="review.no_blocking_items",
            owner_module="pipeline.validation.review",
            scope="manual-review-queue",
            status="fail",
            severity="error",
            blocking_level="publish_blocker",
            message=f"{len(blocking)} unresolved blocking review item(s)",
            details={"review_ids": [item["review_id"] for item in blocking]},
        )
    return ValidationCheck(
        check_id="review.no_blocking_items",
        owner_module="pipeline.validation.review",
        scope="manual-review-queue",
        status="pass",
        severity="error",
        blocking_level="publish_blocker",
        message="No unresolved blocking review items",
    )


def check_placeholder_count(assets: list[dict]) -> ValidationCheck:
    placeholders = [a for a in assets if a.get("is_placeholder") and a.get("entity_type") != "ui"]
    if placeholders:
        keys = [a.get("content_key", a.get("relative_path")) for a in placeholders]
        return ValidationCheck(
            check_id="assets.placeholder_count",
            owner_module="pipeline.validation.assets",
            scope="assets-manifest.json",
            status="warn",
            severity="warning",
            blocking_level="warning_only",
            message=f"{len(placeholders)} entity asset(s) remain placeholders",
            details={"content_keys": keys},
        )
    return ValidationCheck(
        check_id="assets.placeholder_count",
        owner_module="pipeline.validation.assets",
        scope="assets-manifest.json",
        status="pass",
        severity="warning",
        blocking_level="warning_only",
        message="No placeholder entity assets",
    )


def run_publish_validation(
    db_path: Path,
    assets: list[dict],
    review_items: list[dict],
) -> list[ValidationCheck]:
    return [
        check_db_integrity(db_path),
        check_required_tables(db_path),
        check_required_metadata(db_path),
        check_no_orphan_requirements(db_path),
        check_unique_content_keys(db_path),
        check_no_blocking_review_items(review_items),
        check_placeholder_count(assets),
    ]
