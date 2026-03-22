"""Export the current seeded content as normalized baseline JSON files.

Reads the existing ``scripts/seed_content_db.py`` data structures and writes:
  - ``pipeline/normalized/monsters.json``
  - ``pipeline/normalized/eggs.json``
  - ``pipeline/normalized/requirements.json``
  - ``pipeline/normalized/assets.json``
  - ``pipeline/normalized/aliases.json``
  - ``pipeline/normalized/deprecations.json``

Run:  python -m pipeline.export_baseline
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.domain.models import canonical_slug, monster_content_key, egg_content_key  # noqa: E402
from pipeline.schemas.normalized import (  # noqa: E402
    save_json_records,
    validate_monsters_file,
    validate_eggs_file,
    validate_requirements_file,
)

NORMALIZED_DIR = ROOT / "pipeline" / "normalized"
SEED_TIMESTAMP = "2026-03-22T00:00:00Z"
SEED_SOURCE = "seed_content_db"
SEED_SOURCE_URL = "https://example.invalid/seed"
SEED_FINGERPRINT = ""


def _provenance() -> dict:
    return {
        "factual_source": SEED_SOURCE,
        "retrieved_at_utc": SEED_TIMESTAMP,
        "raw_snapshot_id": "seed-baseline",
    }


def _asset_path_for_monster(name: str, mtype: str) -> str:
    slug = canonical_slug(name)
    if mtype == "amber":
        return f"images/monsters/{slug}_amber.png"
    return f"images/monsters/{slug}.png"


def _asset_path_for_egg(name: str) -> str:
    slug = canonical_slug(name)
    return f"images/eggs/{slug}_egg.png"


def export() -> None:
    from scripts.seed_content_db import EGG_TYPES, MONSTERS, REQUIREMENTS

    now = datetime.now(timezone.utc).isoformat()

    # ── Monsters ─────────────────────────────────────────────────────
    monsters: list[dict] = []
    for name, mtype, image_path, wiki_slug in MONSTERS:
        key = monster_content_key(mtype, name)
        monsters.append({
            "content_key": key,
            "display_name": name,
            "monster_type": mtype,
            "source_slug": wiki_slug,
            "source_url": SEED_SOURCE_URL,
            "source_fingerprint": SEED_FINGERPRINT,
            "wiki_slug": wiki_slug,
            "image_path": image_path,
            "is_placeholder": True,
            "asset_source": "generated_placeholder",
            "asset_sha256": "",
            "is_deprecated": False,
            "deprecated_at_utc": None,
            "deprecation_reason": None,
            "provenance": _provenance(),
            "overrides_applied": [],
        })

    # ── Eggs ─────────────────────────────────────────────────────────
    eggs: list[dict] = []
    for name, time_s, time_d, egg_path in EGG_TYPES:
        key = egg_content_key(name)
        eggs.append({
            "content_key": key,
            "display_name": name,
            "breeding_time_seconds": time_s,
            "breeding_time_display": time_d,
            "source_slug": name,
            "source_url": SEED_SOURCE_URL,
            "source_fingerprint": SEED_FINGERPRINT,
            "egg_image_path": egg_path,
            "is_placeholder": True,
            "asset_source": "generated_placeholder",
            "asset_sha256": "",
            "is_deprecated": False,
            "deprecated_at_utc": None,
            "deprecation_reason": None,
            "provenance": _provenance(),
            "overrides_applied": [],
        })

    # ── Requirements ─────────────────────────────────────────────────
    monster_type_map = {name: mtype for name, mtype, _, _ in MONSTERS}
    requirements: list[dict] = []
    for monster_name, reqs in REQUIREMENTS.items():
        mtype = monster_type_map[monster_name]
        mk = monster_content_key(mtype, monster_name)
        for egg_name, qty in reqs:
            ek = egg_content_key(egg_name)
            requirements.append({
                "monster_key": mk,
                "egg_key": ek,
                "quantity": qty,
                "source_fingerprint": SEED_FINGERPRINT,
                "provenance": _provenance(),
                "overrides_applied": [],
            })

    # ── Assets (placeholder entries for each entity) ─────────────────
    assets: list[dict] = []
    for m in monsters:
        assets.append({
            "entity_type": "monster",
            "content_key": m["content_key"],
            "relative_path": m["image_path"],
            "sha256": "",
            "byte_size": 0,
            "asset_source": "generated_placeholder",
            "status": "placeholder",
            "is_placeholder": True,
            "license_basis": "internal_generated_placeholder",
            "source_reference": "seed baseline",
            "generated_at_utc": now,
        })
    for e in eggs:
        assets.append({
            "entity_type": "egg",
            "content_key": e["content_key"],
            "relative_path": e["egg_image_path"],
            "sha256": "",
            "byte_size": 0,
            "asset_source": "generated_placeholder",
            "status": "placeholder",
            "is_placeholder": True,
            "license_basis": "internal_generated_placeholder",
            "source_reference": "seed baseline",
            "generated_at_utc": now,
        })

    # ── Aliases (empty baseline) ─────────────────────────────────────
    aliases: list[dict] = []

    # ── Deprecations (empty baseline) ────────────────────────────────
    deprecations: list[dict] = []

    # ── Write out ────────────────────────────────────────────────────
    save_json_records(NORMALIZED_DIR / "monsters.json", monsters)
    save_json_records(NORMALIZED_DIR / "eggs.json", eggs)
    save_json_records(NORMALIZED_DIR / "requirements.json", requirements)
    save_json_records(NORMALIZED_DIR / "assets.json", assets)
    save_json_records(NORMALIZED_DIR / "aliases.json", aliases)
    save_json_records(NORMALIZED_DIR / "deprecations.json", deprecations)

    # ── Validate ─────────────────────────────────────────────────────
    m_result = validate_monsters_file(monsters)
    e_result = validate_eggs_file(eggs)
    mk_set = {m["content_key"] for m in monsters}
    ek_set = {e["content_key"] for e in eggs}
    r_result = validate_requirements_file(requirements, mk_set, ek_set)

    errors = m_result.errors + e_result.errors + r_result.errors
    if errors:
        print(f"VALIDATION FAILED — {len(errors)} error(s):")
        for err in errors:
            print(f"  [{err.record_index}] {err.field}: {err.message}")
        sys.exit(1)

    print(f"Exported normalized baseline to {NORMALIZED_DIR}")
    print(f"  Monsters:     {len(monsters)}")
    print(f"  Eggs:         {len(eggs)}")
    print(f"  Requirements: {len(requirements)}")
    print(f"  Assets:       {len(assets)}")
    print(f"  Aliases:      {len(aliases)}")
    print(f"  Deprecations: {len(deprecations)}")


if __name__ == "__main__":
    export()
