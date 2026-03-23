"""Content importer — fetches source data, normalizes, and updates pipeline files.

Chains the full Layer 1 ingestion pipeline:
  1. Load existing normalized data
  2. Load overrides
  3. Fetch source data from the MSM Wiki (or other configured source)
  4. Normalize each fetched record
  5. Extract and merge egg data
  6. Detect requirement changes
  7. Write updated normalized files + review queue

This script never writes directly to the app DB — it only updates
the normalized JSON files under ``pipeline/normalized/``.

Run:  python scripts/import_content.py
      python scripts/import_content.py --dry-run
      python scripts/import_content.py --source wiki --delay 2.0
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.curation.overrides import load_overrides  # noqa: E402
from pipeline.curation.review_queue import save_review_queue  # noqa: E402
from pipeline.raw.normalizer import normalize_monster_payload, normalize_egg_payload  # noqa: E402
from pipeline.raw.source_cache import SourceCache  # noqa: E402
from pipeline.raw.wiki_fetcher import (  # noqa: E402
    fetch_monster_list,
    fetch_extra_monsters,
    fetch_egg_data_from_requirements,
)

NORMALIZED_DIR = ROOT / "pipeline" / "normalized"
OVERRIDES_PATH = ROOT / "pipeline" / "curation" / "overrides.yaml"
REVIEW_QUEUE_PATH = ROOT / "pipeline" / "curation" / "review_queue.json"
DEFAULT_CACHE_DIR = ROOT / "pipeline" / "raw" / ".cache"

MONSTER_TYPES = ["wublin", "celestial", "amber"]


def _load_existing_normalized() -> tuple[list[dict], list[dict], list[dict]]:
    """Load current normalized data, or empty lists if files don't exist."""
    monsters: list[dict] = []
    eggs: list[dict] = []
    requirements: list[dict] = []

    m_path = NORMALIZED_DIR / "monsters.json"
    e_path = NORMALIZED_DIR / "eggs.json"
    r_path = NORMALIZED_DIR / "requirements.json"

    if m_path.exists():
        with open(m_path, encoding="utf-8") as f:
            monsters = json.load(f)
    if e_path.exists():
        with open(e_path, encoding="utf-8") as f:
            eggs = json.load(f)
    if r_path.exists():
        with open(r_path, encoding="utf-8") as f:
            requirements = json.load(f)

    return monsters, eggs, requirements


def _build_key_index(records: list[dict]) -> dict[str, dict]:
    """Build a lookup from content_key to record."""
    return {r["content_key"]: r for r in records if "content_key" in r}


def _classify_change(
    existing: dict | None,
    candidate: dict,
    compare_fields: list[str],
) -> str:
    """Classify a candidate record as unchanged, new, or modified."""
    if existing is None:
        return "new"

    for field in compare_fields:
        if existing.get(field) != candidate.get(field):
            return "modified"

    return "unchanged"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import content from external sources into normalized pipeline data.",
    )
    parser.add_argument(
        "--source", default="wiki", choices=["wiki"],
        help="Data source to fetch from (default: wiki)",
    )
    parser.add_argument(
        "--cache-dir", default=str(DEFAULT_CACHE_DIR),
        help="Directory for raw source cache",
    )
    parser.add_argument(
        "--output-dir", default=str(NORMALIZED_DIR),
        help="Directory to write normalized output files",
    )
    parser.add_argument(
        "--review-output", default=str(REVIEW_QUEUE_PATH),
        help="Path to write review queue JSON",
    )
    parser.add_argument(
        "--overrides", default=str(OVERRIDES_PATH),
        help="Path to overrides YAML file",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would change without writing files",
    )
    parser.add_argument(
        "--delay", type=float, default=1.0,
        help="Delay between HTTP requests in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--monsters-only", action="store_true",
        help="Only import monster data (skip eggs/requirements)",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    cache_dir = Path(args.cache_dir)

    # ── Step 1: Load existing data ───────────────────────────────────
    print(f"\n{'='*60}")
    print("  Step 1: Loading existing normalized data")
    print(f"{'='*60}")

    existing_monsters, existing_eggs, existing_requirements = _load_existing_normalized()
    monster_index = _build_key_index(existing_monsters)
    egg_index = _build_key_index(existing_eggs)
    # Track keys seen within this import batch only — NOT pre-populated
    # with existing keys. The normalizer uses this to detect duplicates
    # within one import run. Change detection against existing data
    # happens separately via _classify_change().
    import_batch_keys: set[str] = set()

    print(f"  Existing monsters:     {len(existing_monsters)}")
    print(f"  Existing eggs:         {len(existing_eggs)}")
    print(f"  Existing requirements: {len(existing_requirements)}")

    # ── Step 2: Load overrides ───────────────────────────────────────
    print(f"\n{'='*60}")
    print("  Step 2: Loading overrides")
    print(f"{'='*60}")

    overrides = load_overrides(Path(args.overrides))
    print(f"  Total overrides: {overrides.total}")

    # Build override lookup for the normalizer
    override_map: dict[str, dict] = {}
    for ov in overrides.identity_overrides:
        selector = ov.get("target_selector", "")
        if selector:
            override_map[selector] = ov

    # ── Step 3: Fetch source data ────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  Step 3: Fetching from source: {args.source}")
    print(f"{'='*60}")

    cache = SourceCache(cache_dir)
    all_fetch_results = []
    all_review_items: list[dict] = []

    for mtype in MONSTER_TYPES:
        print(f"\n  Fetching {mtype} monsters...")
        results = fetch_monster_list(mtype, cache, delay=args.delay)
        all_fetch_results.extend(results)

        for r in results:
            all_review_items.extend(r.review_items)
            if r.raw_payload:
                name = r.raw_payload.get("name", "?")
                reqs = len(r.raw_payload.get("requirements", []))
                print(f"    {name}: {reqs} requirements")
            elif r.review_items:
                print(f"    [!] {r.source_reference}: {len(r.review_items)} review item(s)")

    # Fetch monsters not in any standard category (e.g. Monculus)
    print(f"\n  Fetching extra monsters...")
    extra_results = fetch_extra_monsters(cache, delay=args.delay)
    all_fetch_results.extend(extra_results)
    for r in extra_results:
        all_review_items.extend(r.review_items)
        if r.raw_payload:
            name = r.raw_payload.get("name", "?")
            reqs = len(r.raw_payload.get("requirements", []))
            print(f"    {name}: {reqs} requirements")

    print(f"\n  Total monsters fetched: {len([r for r in all_fetch_results if r.raw_payload])}")
    print(f"  Total review items from fetch: {len(all_review_items)}")

    # ── Step 4: Normalize fetched records ────────────────────────────
    print(f"\n{'='*60}")
    print("  Step 4: Normalizing fetched records")
    print(f"{'='*60}")

    new_monsters: list[dict] = []
    new_requirements: list[dict] = []
    stats = {"unchanged": 0, "new": 0, "modified": 0, "failed": 0}

    for result in all_fetch_results:
        if not result.raw_payload or not result.cache_entry:
            stats["failed"] += 1
            continue

        record, norm_review = normalize_monster_payload(
            result.raw_payload,
            source_category="fandom",
            source_reference=result.source_reference,
            content_hash=result.cache_entry.content_hash,
            retrieved_at_utc=result.cache_entry.retrieved_at_utc,
            existing_keys=import_batch_keys,
            overrides=override_map,
        )
        all_review_items.extend(norm_review)

        if record is None:
            stats["failed"] += 1
            continue

        # Classify the change
        change_type = _classify_change(
            monster_index.get(record["content_key"]),
            record,
            compare_fields=["display_name", "monster_type"],
        )

        if change_type == "new":
            stats["new"] += 1
            all_review_items.append({
                "issue_type": "new_entity",
                "severity": "warning",
                "source_reference": result.source_reference,
                "blocking": False,
                "candidate_content_key": record["content_key"],
                "notes": f"New monster discovered: {record['display_name']} ({record['monster_type']})",
                "status": "open",
            })
        elif change_type == "modified":
            stats["modified"] += 1
            all_review_items.append({
                "issue_type": "field_change",
                "severity": "warning",
                "source_reference": result.source_reference,
                "blocking": True,
                "candidate_content_key": record["content_key"],
                "notes": f"Monster data changed: {record['display_name']}",
                "status": "open",
            })
        else:
            stats["unchanged"] += 1

        new_monsters.append(record)
        import_batch_keys.add(record["content_key"])

        # Extract requirements from the raw payload
        for req in result.raw_payload.get("requirements", []):
            egg_name = req.get("egg_name", "")
            quantity = req.get("quantity", 0)
            if egg_name and quantity > 0:
                from app.domain.models import egg_content_key as make_egg_key
                new_requirements.append({
                    "monster_key": record["content_key"],
                    "egg_key": make_egg_key(egg_name),
                    "quantity": quantity,
                    "source_fingerprint": record["source_fingerprint"],
                    "provenance": record["provenance"],
                    "overrides_applied": [],
                })

    print(f"  Unchanged: {stats['unchanged']}")
    print(f"  New:       {stats['new']}")
    print(f"  Modified:  {stats['modified']}")
    print(f"  Failed:    {stats['failed']}")

    # ── Step 5: Extract and merge egg data ────────────────────────────
    if not args.monsters_only:
        print(f"\n{'='*60}")
        print("  Step 5: Extracting and merging egg data")
        print(f"{'='*60}")

        # Extract eggs from wiki-fetched requirements
        raw_eggs = fetch_egg_data_from_requirements(all_fetch_results)

        # Use a stable timestamp for all derived egg records
        now_utc = datetime.now(timezone.utc).isoformat()

        new_eggs: list[dict] = []
        for raw_egg in raw_eggs:
            egg_record, egg_review = normalize_egg_payload(
                raw_egg,
                source_category="fandom",
                source_reference=f"derived/egg/{raw_egg['name']}",
                content_hash="derived",
                retrieved_at_utc=now_utc,
            )
            all_review_items.extend(egg_review)
            if egg_record:
                new_eggs.append(egg_record)

        # Merge with existing eggs: preserve breeding times from existing data
        # where the wiki-derived egg has no breeding time.
        merged_eggs: list[dict] = []
        seen_keys: set[str] = set()

        for egg in new_eggs:
            key = egg["content_key"]
            existing_egg = egg_index.get(key)
            if existing_egg:
                # Prefer existing breeding time if new one is zero
                if egg.get("breeding_time_seconds", 0) == 0:
                    egg["breeding_time_seconds"] = existing_egg.get(
                        "breeding_time_seconds", 0,
                    )
                    egg["breeding_time_display"] = existing_egg.get(
                        "breeding_time_display", "",
                    )
            seen_keys.add(key)
            merged_eggs.append(egg)

        # Keep existing eggs not discovered in this import run
        for existing_egg in existing_eggs:
            ekey = existing_egg.get("content_key", "")
            if ekey and ekey not in seen_keys:
                merged_eggs.append(existing_egg)
                seen_keys.add(ekey)

        new_eggs = merged_eggs
        print(f"  Egg types extracted: {len(raw_eggs)}")
        print(f"  Eggs after merge:    {len(new_eggs)}")

        # Check for eggs with missing breeding times
        zero_bt = [e["display_name"] for e in new_eggs if e.get("breeding_time_seconds", 0) == 0]
        if zero_bt:
            print(f"  WARNING: {len(zero_bt)} eggs with unknown breeding time: {', '.join(zero_bt)}")
    else:
        new_eggs = list(existing_eggs)

    # ── Step 6: Requirement change detection ─────────────────────────
    print(f"\n{'='*60}")
    print("  Step 6: Checking requirement changes")
    print(f"{'='*60}")

    # Build requirement index from existing data
    existing_req_index: dict[str, dict] = {}
    for req in existing_requirements:
        key = f"{req.get('monster_key')}:{req.get('egg_key')}"
        existing_req_index[key] = req

    req_changes = 0
    for req in new_requirements:
        key = f"{req['monster_key']}:{req['egg_key']}"
        existing = existing_req_index.get(key)
        if existing and existing.get("quantity") != req["quantity"]:
            req_changes += 1
            all_review_items.append({
                "issue_type": "requirement_change",
                "severity": "warning",
                "source_reference": f"{req['monster_key']}/{req['egg_key']}",
                "blocking": True,
                "notes": f"Quantity changed: {existing.get('quantity')} -> {req['quantity']}",
                "status": "open",
            })

    print(f"  Requirement changes detected: {req_changes}")

    # ── Step 7: Write outputs ────────────────────────────────────────
    blocking_count = sum(1 for item in all_review_items if item.get("blocking") and item.get("status") == "open")

    print(f"\n{'='*60}")
    print("  Summary")
    print(f"{'='*60}")
    print(f"  Monsters:      {len(new_monsters)} ({stats['new']} new, {stats['modified']} modified)")
    print(f"  Eggs:          {len(new_eggs)}")
    print(f"  Requirements:  {len(new_requirements)}")
    print(f"  Review items:  {len(all_review_items)} ({blocking_count} blocking)")

    if args.dry_run:
        print(f"\n  DRY RUN — no files written.")
        if blocking_count:
            print(f"  {blocking_count} blocking item(s) would need resolution before publish.")
        return 0

    print(f"\n{'='*60}")
    print("  Writing output files")
    print(f"{'='*60}")

    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "monsters.json", "w", encoding="utf-8") as f:
        json.dump(new_monsters, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"  Wrote {output_dir / 'monsters.json'}")

    if not args.monsters_only:
        with open(output_dir / "eggs.json", "w", encoding="utf-8") as f:
            json.dump(new_eggs, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"  Wrote {output_dir / 'eggs.json'}")

    with open(output_dir / "requirements.json", "w", encoding="utf-8") as f:
        json.dump(new_requirements, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"  Wrote {output_dir / 'requirements.json'}")

    # Write review queue
    review_path = Path(args.review_output)
    save_review_queue(review_path, all_review_items)
    print(f"  Wrote {review_path}")

    if blocking_count:
        print(f"\n  WARNING: {blocking_count} blocking review item(s).")
        print("  Run: python scripts/review_content.py --show")
        print("  Resolve before publishing.")

    print(f"\n{'='*60}")
    print("  IMPORT COMPLETE")
    print(f"{'='*60}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
