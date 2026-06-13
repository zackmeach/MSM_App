"""Validate that a downloaded content.db has the required schema shape.

Supports both basic legacy validation and richer artifact-contract-aware
validation for the hardened update path.
"""

from __future__ import annotations

import hashlib
import re
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
    """Raise ValidationError if the DB does not meet minimum content contract.

    The connection is closed on every exit path, including early failures:
    a leaked handle blocks the caller's staged-file cleanup on Windows
    (WinError 32) on the exact untrusted-download path this guards.
    """
    try:
        conn = sqlite3.connect(db_path)
        try:
            result = conn.execute("PRAGMA integrity_check").fetchone()
            if not result or result[0] != "ok":
                raise ValidationError(f"Integrity check failed: {result}")

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
    except sqlite3.Error as exc:
        raise ValidationError(f"Cannot open database: {exc}") from exc


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

    # SHA-256 is mandatory regardless of contract version: a manifest without
    # it would let the downloaded DB skip integrity checking entirely.
    sha = manifest.get("content_db_sha256", "")
    if not sha or len(sha) != 64:
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


def _release_tuple(version: str) -> tuple[int, ...]:
    """Parse a version string into its numeric release segment.

    Tolerates an optional leading ``v``/``V``, pre-release / dev / post
    suffixes, and build metadata (e.g. ``1.0.0-beta.3``, ``1.0.0rc1``,
    ``1.0.0b3``, ``1.0.0+ci.5``, ``v1.2.3``). Anything from the first ``-``
    or ``+`` is discarded; each ``.``-split segment contributes only its
    leading digits, and parsing stops at the first segment with no leading
    digits. So ``int()`` never sees ``"0rc1"``. This makes the fallback path
    consistent with comparing ``packaging``'s ``base_version``.
    """
    head = re.split(r"[-+]", str(version).strip(), maxsplit=1)[0]
    if head[:1] in ("v", "V"):
        head = head[1:]
    parts: list[int] = []
    for segment in head.split("."):
        m = re.match(r"\d+", segment)
        if not m:
            break
        parts.append(int(m.group()))
    return tuple(parts)


def _compatible_fallback(client_version: str, min_version: str) -> bool:
    """``packaging``-free compatibility check on the numeric release segment.

    Returns True if *client_version* is at least *min_version*, comparing
    release tuples numerically (so ``1.9.0`` < ``1.10.0``, not lexically).
    The shorter release tuple is zero-padded to the longer's length before
    comparison, so ``1.0`` is treated as equal to ``1.0.0``.
    """
    client = _release_tuple(client_version)
    floor = _release_tuple(min_version)
    width = max(len(client), len(floor))
    client += (0,) * (width - len(client))
    floor += (0,) * (width - len(floor))
    return client >= floor


def _compatible(client_version: str, min_version: str) -> bool:
    """True if *client_version* satisfies the *min_version* floor.

    Comparison uses the base/release version on BOTH sides, ignoring
    pre-release/dev/post suffixes: a pre-release of an allowed version
    (e.g. ``1.0.0-beta.3`` against floor ``1.0.0``) is accepted, while a
    genuinely older client (``0.9.0`` against ``1.0.0``) is rejected.
    """
    client_version = str(client_version)
    min_version = str(min_version)
    try:
        from packaging.version import Version
    except ImportError:
        return _compatible_fallback(client_version, min_version)
    return Version(Version(client_version).base_version) >= Version(
        Version(min_version).base_version
    )


def validate_client_compatibility(manifest: dict, client_version: str) -> None:
    """Raise ValidationError if the client version is too old for this release."""
    min_version = manifest.get("min_supported_client_version", "")
    if not min_version:
        return
    if not _compatible(client_version, min_version):
        raise ValidationError(
            f"Client version {client_version} is below minimum {min_version}"
        )
