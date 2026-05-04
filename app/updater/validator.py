"""Validate that a downloaded content.db has the required schema shape.

Supports both basic legacy validation and richer artifact-contract-aware
validation for the hardened update path.
"""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from urllib.parse import urlparse

REQUIRED_TABLES = {"monsters", "egg_types", "monster_requirements", "update_metadata"}
REQUIRED_METADATA_KEYS = {"content_version", "last_updated_utc", "source"}

SUPPORTED_ARTIFACT_CONTRACT_VERSIONS = {"1.1"}

# content_db_url must use one of these schemes and target one of these hosts.
# A poisoned manifest could otherwise redirect the downloader to plain HTTP
# (downgrade), file:// (local read leak), or an attacker-controlled host.
ALLOWED_DB_URL_SCHEMES: tuple[str, ...] = ("https",)
ALLOWED_DB_URL_HOSTS: tuple[str, ...] = ("raw.githubusercontent.com",)


class ValidationError(Exception):
    pass


def validate_content_db(db_path: str) -> None:
    """Raise ValidationError if the DB does not meet minimum content contract."""
    try:
        conn = sqlite3.connect(db_path)
        result = conn.execute("PRAGMA integrity_check").fetchone()
        if not result or result[0] != "ok":
            raise ValidationError(f"Integrity check failed: {result}")
    except sqlite3.Error as exc:
        raise ValidationError(f"Cannot open database: {exc}") from exc

    try:
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        missing = REQUIRED_TABLES - tables
        if missing:
            raise ValidationError(f"Missing tables: {missing}")

        for key in REQUIRED_METADATA_KEYS:
            row = conn.execute(
                "SELECT value FROM update_metadata WHERE key = ?", (key,)
            ).fetchone()
            if not row or not row[0]:
                raise ValidationError(f"Missing or empty metadata key: {key}")

        monster_count = conn.execute("SELECT COUNT(*) FROM monsters").fetchone()[0]
        if monster_count < 1:
            raise ValidationError("No monsters in database")

        egg_count = conn.execute("SELECT COUNT(*) FROM egg_types").fetchone()[0]
        if egg_count < 1:
            raise ValidationError("No egg types in database")

        orphan_monsters = conn.execute(
            "SELECT COUNT(*) FROM monster_requirements mr "
            "LEFT JOIN monsters m ON mr.monster_id = m.id "
            "WHERE m.id IS NULL"
        ).fetchone()[0]
        if orphan_monsters > 0:
            raise ValidationError(f"{orphan_monsters} requirement rows reference nonexistent monsters")

        orphan_eggs = conn.execute(
            "SELECT COUNT(*) FROM monster_requirements mr "
            "LEFT JOIN egg_types e ON mr.egg_type_id = e.id "
            "WHERE e.id IS NULL"
        ).fetchone()[0]
        if orphan_eggs > 0:
            raise ValidationError(f"{orphan_eggs} requirement rows reference nonexistent egg types")

    finally:
        conn.close()


def validate_checksum(file_path: str | Path, expected_sha256: str) -> None:
    """Raise ValidationError if file SHA-256 does not match expected hash."""
    actual = hashlib.sha256(Path(file_path).read_bytes()).hexdigest()
    if actual != expected_sha256:
        raise ValidationError(
            f"Checksum mismatch: expected {expected_sha256}, got {actual}"
        )


def validate_manifest_contract(
    manifest: dict,
    *,
    allowed_schemes: tuple[str, ...] = ALLOWED_DB_URL_SCHEMES,
    allowed_hosts: tuple[str, ...] = ALLOWED_DB_URL_HOSTS,
) -> None:
    """Raise ValidationError if the manifest contract is unsupported or malformed.

    The *allowed_schemes* and *allowed_hosts* parameters override the default
    production allowlist; tests with a local HTTP fixture pass a permissive
    allowlist. Production callers should use defaults.
    """
    contract = manifest.get("artifact_contract_version", "")
    if contract and contract not in SUPPORTED_ARTIFACT_CONTRACT_VERSIONS:
        raise ValidationError(f"Unsupported artifact contract version: {contract}")

    if not manifest.get("content_version"):
        raise ValidationError("Manifest missing content_version")
    if not manifest.get("content_db_url"):
        raise ValidationError("Manifest missing content_db_url")

    _validate_db_url(manifest["content_db_url"], allowed_schemes, allowed_hosts)

    sha = manifest.get("content_db_sha256", "")
    if contract and (not sha or len(sha) != 64):
        raise ValidationError(f"Manifest has missing or malformed content_db_sha256: {sha!r}")


def _validate_db_url(
    url: str,
    allowed_schemes: tuple[str, ...],
    allowed_hosts: tuple[str, ...],
) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in allowed_schemes:
        raise ValidationError(
            f"content_db_url scheme {parsed.scheme!r} not in {allowed_schemes}"
        )
    if parsed.hostname is None or parsed.hostname not in allowed_hosts:
        raise ValidationError(
            f"content_db_url host {parsed.hostname!r} not in {allowed_hosts}"
        )


def validate_client_compatibility(manifest: dict, client_version: str) -> None:
    """Raise ValidationError if the client version is too old for this release."""
    min_version = manifest.get("min_supported_client_version", "")
    if not min_version:
        return
    try:
        from packaging.version import Version
        if Version(client_version) < Version(min_version):
            raise ValidationError(
                f"Client version {client_version} is below minimum {min_version}"
            )
    except ImportError:
        min_parts = [int(x) for x in min_version.split(".")]
        client_parts = [int(x) for x in client_version.split(".")]
        if client_parts < min_parts:
            raise ValidationError(
                f"Client version {client_version} is below minimum {min_version}"
            )
