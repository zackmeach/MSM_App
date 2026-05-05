"""Audit egg_elements.json against the MSM Fandom Wiki.

For every egg in pipeline/normalized/eggs.json, this script:
  1. Looks up its current element entry in egg_elements.json (if any).
  2. Fetches the base monster's wiki page and parses element data.
  3. Compares wiki data against the current entry.
  4. Writes three output files to pipeline/curation/:
       element_audit_results.json  — full per-egg comparison
       element_candidates.json     — proposed egg_elements additions/corrections
       element_review_queue.json   — entries that need human review

Run:
  python scripts/audit_egg_elements.py          # audit only
  python scripts/audit_egg_elements.py --apply  # apply candidates to egg_elements.json

The --apply flag merges element_candidates.json INTO egg_elements.json.
Always inspect element_candidates.json first before applying.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.raw.source_cache import SourceCache  # noqa: E402
from pipeline.raw.wiki_fetcher import (  # noqa: E402
    KNOWN_BREEDING_TIMES,
    fetch_elements_for_egg,
)

NORMALIZED_DIR = ROOT / "pipeline" / "normalized"
CURATION_DIR = ROOT / "pipeline" / "curation"
CACHE_DIR = ROOT / "pipeline" / "raw" / "cache"

EGG_ELEMENTS_PATH = NORMALIZED_DIR / "egg_elements.json"
AUDIT_RESULTS_PATH = CURATION_DIR / "element_audit_results.json"
CANDIDATES_PATH = CURATION_DIR / "element_candidates.json"
REVIEW_QUEUE_PATH = CURATION_DIR / "element_review_queue.json"

DEFAULT_REQUEST_DELAY = 1.0


def _load_eggs() -> list[dict]:
    path = NORMALIZED_DIR / "eggs.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_egg_elements() -> dict[str, list[str]]:
    if not EGG_ELEMENTS_PATH.exists():
        return {}
    with open(EGG_ELEMENTS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("elements", {})


def _egg_display_name(egg: dict) -> str:
    """Return the display name used as the wiki page slug."""
    return egg.get("display_name", "").strip()


def _is_in_known_breeding_times(display_name: str) -> bool:
    """Return True if this egg appears in KNOWN_BREEDING_TIMES (wiki-scrape candidates)."""
    return display_name in KNOWN_BREEDING_TIMES


def _compare(current: list[str] | None, wiki: list[str]) -> str:
    """Classify the relationship between current and wiki element lists."""
    if not current and not wiki:
        return "both_empty"
    if not current:
        return "missing"
    if not wiki:
        return "wiki_parse_failed"
    if sorted(current) == sorted(wiki):
        return "match"
    return "mismatch"


def run_audit(delay: float = DEFAULT_REQUEST_DELAY) -> None:
    CURATION_DIR.mkdir(parents=True, exist_ok=True)
    cache = SourceCache(CACHE_DIR)

    eggs = _load_eggs()
    current_elements = _load_egg_elements()

    audit_results: list[dict] = []
    candidates: dict[str, list[str]] = {}
    review_items: list[dict] = []

    total = len(eggs)
    for idx, egg in enumerate(eggs, 1):
        content_key = egg.get("content_key", "")
        display_name = _egg_display_name(egg)
        current = current_elements.get(content_key)

        print(f"  [{idx:2d}/{total}] {content_key} ({display_name})", end=" ... ", flush=True)

        if not display_name:
            print("SKIP (no display_name)")
            audit_results.append({
                "content_key": content_key,
                "display_name": display_name,
                "status": "skipped",
                "reason": "no display_name",
                "current": current,
                "wiki": None,
            })
            continue

        if not _is_in_known_breeding_times(display_name):
            # Not a base monster with a simple wiki page — skip wiki fetch.
            print("SKIP (not in KNOWN_BREEDING_TIMES)")
            audit_results.append({
                "content_key": content_key,
                "display_name": display_name,
                "status": "skipped",
                "reason": "not in KNOWN_BREEDING_TIMES — may need manual entry",
                "current": current,
                "wiki": None,
            })
            continue

        if delay > 0:
            time.sleep(delay)

        wiki_elements, fetch_items = fetch_elements_for_egg(display_name, cache)

        if fetch_items:
            for item in fetch_items:
                item["content_key"] = content_key
            review_items.extend(fetch_items)

        status = _compare(current, wiki_elements)
        print(status.upper())

        entry: dict = {
            "content_key": content_key,
            "display_name": display_name,
            "status": status,
            "current": current,
            "wiki": wiki_elements or None,
        }

        if status == "missing" and wiki_elements:
            candidates[content_key] = wiki_elements
            entry["action"] = "add"
        elif status == "mismatch":
            # Always flag mismatches for human review; also add to candidates
            # so the user can choose to apply after inspecting.
            candidates[content_key] = wiki_elements
            entry["action"] = "correct"
            review_items.append({
                "content_key": content_key,
                "display_name": display_name,
                "issue_type": "element_mismatch",
                "severity": "warning",
                "current": current,
                "wiki": wiki_elements,
                "notes": (
                    f"Current: {current!r}  |  Wiki: {wiki_elements!r}  "
                    "— verify game data before applying"
                ),
            })
        elif status == "wiki_parse_failed" and not current:
            entry["action"] = "needs_manual_entry"
            review_items.append({
                "content_key": content_key,
                "display_name": display_name,
                "issue_type": "element_parse_failed",
                "severity": "warning",
                "notes": "Wiki fetch/parse failed and no current entry — add manually",
            })

        audit_results.append(entry)

    # ── Summaries ────────────────────────────────────────────────────
    counts: dict[str, int] = {}
    for r in audit_results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1

    print(f"\n  Summary:")
    for status, n in sorted(counts.items()):
        print(f"    {status:<22} {n}")
    print(f"  Candidates to apply: {len(candidates)}")
    print(f"  Review items:        {len(review_items)}")

    # ── Write outputs ────────────────────────────────────────────────
    with open(AUDIT_RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(audit_results, f, indent=2)
    print(f"\n  Audit results  -> {AUDIT_RESULTS_PATH}")

    candidates_doc = {
        "_comment": (
            "Wiki-sourced element candidates. Review before applying. "
            "Run: python scripts/audit_egg_elements.py --apply"
        ),
        "elements": candidates,
    }
    with open(CANDIDATES_PATH, "w", encoding="utf-8") as f:
        json.dump(candidates_doc, f, indent=2)
    print(f"  Candidates     -> {CANDIDATES_PATH}")

    with open(REVIEW_QUEUE_PATH, "w", encoding="utf-8") as f:
        json.dump(review_items, f, indent=2)
    print(f"  Review queue   -> {REVIEW_QUEUE_PATH}")


def apply_candidates() -> None:
    """Merge element_candidates.json into egg_elements.json."""
    if not CANDIDATES_PATH.exists():
        print("ERROR: element_candidates.json not found. Run audit first.")
        sys.exit(1)

    with open(CANDIDATES_PATH, encoding="utf-8") as f:
        candidates_doc = json.load(f)
    candidates: dict[str, list[str]] = candidates_doc.get("elements", {})

    if not candidates:
        print("No candidates to apply.")
        return

    with open(EGG_ELEMENTS_PATH, encoding="utf-8") as f:
        ee_doc = json.load(f)
    current: dict[str, list[str]] = ee_doc.get("elements", {})

    added = 0
    corrected = 0
    for key, elems in candidates.items():
        if key in current:
            if current[key] != elems:
                corrected += 1
        else:
            added += 1
        current[key] = elems

    ee_doc["elements"] = dict(sorted(current.items()))
    with open(EGG_ELEMENTS_PATH, "w", encoding="utf-8") as f:
        json.dump(ee_doc, f, indent=2)

    print(f"  Applied {added} new + {corrected} corrected entries to egg_elements.json")
    print(f"  Run: python scripts/seed_content_db.py  to rebuild content.db")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit egg element data against the MSM Fandom Wiki.",
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Apply element_candidates.json into egg_elements.json",
    )
    parser.add_argument(
        "--delay", type=float, default=DEFAULT_REQUEST_DELAY,
        help="Seconds between wiki requests (default: 1.0)",
    )
    args = parser.parse_args()

    if args.apply:
        print("Applying candidates to egg_elements.json...")
        apply_candidates()
        return 0

    print(f"\nAuditing {(NORMALIZED_DIR / 'eggs.json').name} against MSM wiki...")
    print(f"  (delay between requests: {args.delay}s)")
    print()
    run_audit(delay=args.delay)
    return 0


if __name__ == "__main__":
    sys.exit(main())
