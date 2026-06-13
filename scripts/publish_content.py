"""Publish pipeline — builds content.db, validates, and generates release artifacts.

Chains the full Layer 2 pipeline:
  1. Check review queue for blocking items
  2. Load normalized data from pipeline/normalized/
  3. Build content.db via db_builder
  4. Diff against baseline (if provided)
  5. Run publish validation checks
  6. Generate manifest, diff report, and validation report
  7. Write all artifacts to output directory

The desktop app updater consumes the output manifest.json + content.db.
This script does NOT scrape external sources — it only transforms
already-normalized data into publishable artifacts.

Run:  python scripts/publish_content.py --content-version 1.0.0
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.build.db_builder import build_content_db  # noqa: E402
from pipeline.curation.review_queue import has_blocking_items, load_review_queue  # noqa: E402
from pipeline.diff.engine import compute_diff  # noqa: E402
from pipeline.publish.artifacts import (  # noqa: E402
    generate_diff_report,
    generate_manifest,
    generate_validation_report,
    write_artifact,
)
from pipeline.validation.checks import run_publish_validation  # noqa: E402

NORMALIZED_DIR = ROOT / "pipeline" / "normalized"
REVIEW_QUEUE_PATH = ROOT / "pipeline" / "curation" / "review_queue.json"
DEFAULT_BASE_URL = "https://raw.githubusercontent.com/zackmeach/MSM_App/main/content"


def _load_normalized() -> tuple[list[dict], list[dict], list[dict], list[dict], dict[str, list[str]]]:
    """Load monsters, eggs, requirements, assets, and egg elements from normalized JSON."""
    required_paths = {
        "monsters": NORMALIZED_DIR / "monsters.json",
        "eggs": NORMALIZED_DIR / "eggs.json",
        "requirements": NORMALIZED_DIR / "requirements.json",
        "assets": NORMALIZED_DIR / "assets.json",
    }
    missing = [name for name, p in required_paths.items() if not p.exists()]
    if missing:
        print(f"ERROR: Missing normalized files: {', '.join(missing)}")
        sys.exit(1)

    loaded = {}
    for name, p in required_paths.items():
        with open(p, encoding="utf-8") as f:
            loaded[name] = json.load(f)

    egg_elements: dict[str, list[str]] = {}
    ee_path = NORMALIZED_DIR / "egg_elements.json"
    if ee_path.exists():
        with open(ee_path, encoding="utf-8") as f:
            ee_raw = json.load(f)
        egg_elements = ee_raw.get("elements", {})

    return loaded["monsters"], loaded["eggs"], loaded["requirements"], loaded["assets"], egg_elements


def _extract_baseline_records(
    db_path: Path,
) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    """Extract normalized-shaped records from a baseline content.db.

    Returns (monsters, eggs, requirements, assets) keyed/shaped the way
    compute_diff expects, so the diff report reflects real changes instead
    of claiming everything is new.
    """
    import sqlite3

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        monsters = [
            {
                "content_key": r[0],
                "display_name": r[1],
                "monster_type": r[2],
                "wiki_slug": r[3],
                "image_path": r[4],
                "is_placeholder": bool(r[5]),
                "is_deprecated": bool(r[6]),
                "deprecation_reason": r[7],
                "source_fingerprint": r[8],
                "asset_source": r[9],
            }
            for r in conn.execute(
                "SELECT content_key, name, monster_type, wiki_slug, image_path, "
                "is_placeholder, is_deprecated, deprecation_reason, source_fingerprint, "
                "asset_source FROM monsters WHERE content_key != ''"
            )
        ]
        eggs = [
            {
                "content_key": r[0],
                "display_name": r[1],
                "breeding_time_seconds": r[2],
                "breeding_time_display": r[3],
                "egg_image_path": r[4],
                "is_placeholder": bool(r[5]),
                "is_deprecated": bool(r[6]),
                "deprecation_reason": r[7],
                "source_fingerprint": r[8],
                "asset_source": r[9],
            }
            for r in conn.execute(
                "SELECT content_key, name, breeding_time_seconds, breeding_time_display, "
                "egg_image_path, is_placeholder, is_deprecated, deprecation_reason, "
                "source_fingerprint, asset_source FROM egg_types WHERE content_key != ''"
            )
        ]
        requirements = [
            {"monster_key": r[0], "egg_key": r[1], "quantity": r[2]}
            for r in conn.execute(
                "SELECT m.content_key, e.content_key, mr.quantity "
                "FROM monster_requirements mr "
                "JOIN monsters m ON mr.monster_id = m.id "
                "JOIN egg_types e ON mr.egg_type_id = e.id "
                "WHERE m.content_key != '' AND e.content_key != ''"
            )
        ]
        assets = [
            {
                "entity_type": r[0],
                "content_key": r[1],
                "relative_path": r[2],
                "sha256": r[3],
                "status": "placeholder" if r[4] else "official",
                "is_placeholder": bool(r[4]),
            }
            for r in conn.execute(
                "SELECT 'monster', content_key, image_path, asset_sha256, is_placeholder "
                "FROM monsters WHERE image_path != '' "
                "UNION ALL "
                "SELECT 'egg', content_key, egg_image_path, asset_sha256, is_placeholder "
                "FROM egg_types WHERE egg_image_path != ''"
            )
        ]
        return monsters, eggs, requirements, assets
    finally:
        conn.close()


def _baseline_version(db_path: Path) -> str:
    """Read content_version from the baseline DB, '0.0.0' on failure."""
    import sqlite3

    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            row = conn.execute(
                "SELECT value FROM update_metadata WHERE key = 'content_version'"
            ).fetchone()
            return row[0] if row and row[0] else "0.0.0"
        finally:
            conn.close()
    except sqlite3.Error:
        return "0.0.0"


def _git_sha() -> str:
    """Get current git SHA, or 'unknown' if not in a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        return result.stdout.strip()[:12] if result.returncode == 0 else "unknown"
    except FileNotFoundError:
        return "unknown"


def _build_id() -> str:
    """Generate a build ID from the current timestamp."""
    return f"build-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build and publish content artifacts from normalized data.",
    )
    parser.add_argument(
        "--content-version", default=None,
        help=(
            "Semver version string for this content release. "
            "Defaults to pipeline/normalized/version.txt."
        ),
    )
    parser.add_argument(
        "--output-dir", default="content",
        help="Directory to write artifacts to (default: content/)",
    )
    parser.add_argument(
        "--baseline-db", default=None,
        help="Path to prior content.db for ID preservation and diffing",
    )
    parser.add_argument(
        "--base-url", default=DEFAULT_BASE_URL,
        help="Base URL for artifact download links in the manifest",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Validate only — do not write output artifacts",
    )
    args = parser.parse_args()

    from pipeline.version import load_content_version
    content_version = args.content_version or load_content_version()
    output_dir = Path(args.output_dir)
    baseline_db = Path(args.baseline_db) if args.baseline_db else None
    base_url = args.base_url
    dry_run = args.dry_run

    # ── Step 1: Check review queue ───────────────────────────────────
    print(f"\n{'='*60}")
    print("  Step 1: Checking review queue")
    print(f"{'='*60}")

    review_items = load_review_queue(REVIEW_QUEUE_PATH)
    if has_blocking_items(review_items):
        blocking = [
            item for item in review_items
            if item.get("blocking") and item.get("status") == "open"
        ]
        print(f"ERROR: {len(blocking)} blocking review item(s) found.")
        for item in blocking:
            rid = item.get("review_id", "?")
            issue = item.get("issue_type", "?")
            ref = item.get("source_reference", "?")
            print(f"  - [{rid}] {issue}: {ref}")
        print("\nResolve blocking items before publishing.")
        print("  Run: python scripts/review_content.py --show")
        return 1
    print(f"  Review queue clean ({len(review_items)} items, 0 blocking)")

    # ── Step 2: Load normalized data ─────────────────────────────────
    print(f"\n{'='*60}")
    print("  Step 2: Loading normalized data")
    print(f"{'='*60}")

    monsters, eggs, requirements, assets, egg_elements = _load_normalized()
    print(f"  Monsters:     {len(monsters)}")
    print(f"  Eggs:         {len(eggs)}")
    print(f"  Requirements: {len(requirements)}")
    print(f"  Assets:       {len(assets)}")
    print(f"  Egg elements: {len(egg_elements)} mappings")

    # ── Step 3: Build content.db ─────────────────────────────────────
    print(f"\n{'='*60}")
    print("  Step 3: Building content.db")
    print(f"{'='*60}")

    build_dir = output_dir / "_build"
    build_dir.mkdir(parents=True, exist_ok=True)
    built_db_path = build_dir / "content.db"

    result = build_content_db(
        built_db_path,
        monsters, eggs, requirements,
        content_version=content_version,
        baseline_db_path=baseline_db,
        egg_elements=egg_elements,
    )
    print(f"  DB path:      {result.db_path}")
    print(f"  Monsters:     {result.monster_count}")
    print(f"  Eggs:         {result.egg_count}")
    print(f"  Requirements: {result.requirement_count}")
    print(f"  Egg elements: {result.element_count} rows")
    print(f"  IDs preserved: {result.id_preserved}, reassigned: {result.id_reassigned}")

    # ── Step 4: Diff against baseline ────────────────────────────────
    print(f"\n{'='*60}")
    print("  Step 4: Computing diff")
    print(f"{'='*60}")

    if baseline_db:
        print(f"  Baseline: {baseline_db}")
        (
            baseline_monsters,
            baseline_eggs,
            baseline_requirements,
            baseline_assets,
        ) = _extract_baseline_records(baseline_db)
        previous_version = _baseline_version(baseline_db)
        print(
            f"  Extracted: {len(baseline_monsters)} monsters, "
            f"{len(baseline_eggs)} eggs, {len(baseline_requirements)} reqs "
            f"(version {previous_version})"
        )
    else:
        print("  No baseline provided — all content will appear as 'new'")
        baseline_monsters = []
        baseline_eggs = []
        baseline_requirements = []
        baseline_assets = []
        previous_version = "0.0.0"
    diff_result = compute_diff(
        baseline_monsters, monsters,
        baseline_eggs, eggs,
        baseline_requirements, requirements,
        baseline_assets, assets,
        previous_version, content_version,
    )
    s = diff_result.summary
    print(f"  New monsters:     {s.new_monsters}")
    print(f"  Changed monsters: {s.changed_monsters}")
    print(f"  New eggs:         {s.new_eggs}")
    print(f"  Changed eggs:     {s.changed_eggs}")
    print(f"  Req changes:      {s.requirement_changes}")

    # ── Step 5: Run publish validation ───────────────────────────────
    print(f"\n{'='*60}")
    print("  Step 5: Running publish validation")
    print(f"{'='*60}")

    checks = run_publish_validation(
        built_db_path,
        assets,
        review_items,
        eggs_path=NORMALIZED_DIR / "eggs.json",
        egg_elements_path=NORMALIZED_DIR / "egg_elements.json",
        schema_path=ROOT / "pipeline" / "schemas" / "egg_elements.schema.json",
    )
    blockers = [c for c in checks if c.status == "fail" and c.blocking_level == "publish_blocker"]
    warnings = [c for c in checks if c.status == "warn"]

    for check in checks:
        icon = "PASS" if check.status == "pass" else ("FAIL" if check.status == "fail" else "WARN")
        print(f"  [{icon}] {check.check_id}: {check.message}")

    if blockers:
        print(f"\nERROR: {len(blockers)} publish blocker(s) found. Cannot publish.")
        return 1

    if warnings:
        print(f"\n  {len(warnings)} warning(s) — proceeding anyway.")

    # ── Step 6: Generate artifacts ───────────────────────────────────
    if dry_run:
        print(f"\n{'='*60}")
        print("  DRY RUN — skipping artifact generation")
        print(f"{'='*60}")
        print(f"\n  Version {content_version} validated successfully.")
        print("  Re-run without --dry-run to write artifacts.")
        # Clean up build directory
        shutil.rmtree(build_dir, ignore_errors=True)
        return 0

    print(f"\n{'='*60}")
    print("  Step 6: Generating artifacts")
    print(f"{'='*60}")

    bid = _build_id()
    sha = _git_sha()

    manifest = generate_manifest(
        content_version, built_db_path,
        schema_version=2,
        build_id=bid,
        git_sha=sha,
        base_url=base_url,
    )

    diff_report = generate_diff_report(diff_result, bid, review_items)
    validation_report = generate_validation_report(content_version, bid, checks)

    # Write artifacts to output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    write_artifact(output_dir / "manifest.json", manifest)
    write_artifact(output_dir / "diff-report.json", diff_report)
    write_artifact(output_dir / "validation-report.json", validation_report)

    # Copy built content.db to output
    final_db = output_dir / "content.db"
    shutil.copy2(built_db_path, final_db)

    # Clean up build directory
    shutil.rmtree(build_dir, ignore_errors=True)

    # ── Summary ──────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("  PUBLISH COMPLETE")
    print(f"{'='*60}")
    print(f"  Version:       {content_version}")
    print(f"  Build ID:      {bid}")
    print(f"  Git SHA:       {sha}")
    print(f"  Output:        {output_dir}")
    print(f"  manifest.json: {(output_dir / 'manifest.json').stat().st_size} bytes")
    print(f"  content.db:    {final_db.stat().st_size} bytes")
    print(f"  DB URL:        {manifest['content_db_url']}")
    print(f"  DB SHA-256:    {manifest['content_db_sha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
