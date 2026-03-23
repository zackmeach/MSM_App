"""Review queue CLI — inspect, approve, and reject import review items.

Provides a maintainer interface for reviewing items flagged by the
import pipeline before content can be published.

Usage:
  python scripts/review_content.py --show           # display all items
  python scripts/review_content.py --check          # exit 0 if no blocking items
  python scripts/review_content.py --approve ID     # approve an item
  python scripts/review_content.py --reject ID      # reject (remove) an item
  python scripts/review_content.py --approve-all    # approve all non-blocking items
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.curation.review_queue import (  # noqa: E402
    has_blocking_items,
    load_review_queue,
    save_review_queue,
)

REVIEW_QUEUE_PATH = ROOT / "pipeline" / "curation" / "review_queue.json"


def _show(items: list[dict]) -> None:
    """Display review queue items."""
    if not items:
        print("  Review queue is empty.")
        return

    blocking = [i for i in items if i.get("blocking") and i.get("status") == "open"]
    non_blocking = [i for i in items if not i.get("blocking") or i.get("status") != "open"]

    if blocking:
        print(f"\n  BLOCKING ({len(blocking)}):")
        print(f"  {'─'*56}")
        for item in blocking:
            _print_item(item)

    if non_blocking:
        print(f"\n  NON-BLOCKING ({len(non_blocking)}):")
        print(f"  {'─'*56}")
        for item in non_blocking:
            _print_item(item)

    print(f"\n  Total: {len(items)} items ({len(blocking)} blocking)")


def _print_item(item: dict) -> None:
    """Print a single review item."""
    rid = item.get("review_id", "?")[:16]
    issue = item.get("issue_type", "?")
    status = item.get("status", "?")
    blocking = "BLOCK" if item.get("blocking") else "info"
    ref = item.get("source_reference", "")
    key = item.get("candidate_content_key", "")
    notes = item.get("notes", item.get("proposed_resolution", ""))

    status_marker = {"open": "*", "approved": "+", "rejected": "x"}.get(status, "?")
    print(f"  [{status_marker}] {rid}  {issue:<28} [{blocking}]")
    if key:
        print(f"      key: {key}")
    if ref:
        print(f"      src: {ref}")
    if notes:
        # Truncate long notes
        display = notes[:80] + "..." if len(notes) > 80 else notes
        print(f"      {display}")
    print()


def _approve(items: list[dict], review_id: str) -> bool:
    """Approve an item by ID. Returns True if found."""
    for item in items:
        if item.get("review_id", "").startswith(review_id):
            item["status"] = "approved"
            print(f"  Approved: {item.get('review_id')}")
            return True
    print(f"  Not found: {review_id}")
    return False


def _reject(items: list[dict], review_id: str) -> bool:
    """Reject (remove) an item by ID. Returns True if found."""
    for i, item in enumerate(items):
        if item.get("review_id", "").startswith(review_id):
            removed = items.pop(i)
            print(f"  Rejected and removed: {removed.get('review_id')}")
            return True
    print(f"  Not found: {review_id}")
    return False


def _approve_all_non_blocking(items: list[dict]) -> int:
    """Approve all non-blocking open items. Returns count."""
    count = 0
    for item in items:
        if not item.get("blocking") and item.get("status") == "open":
            item["status"] = "approved"
            count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Review, approve, or reject import review items.",
    )
    parser.add_argument(
        "--show", action="store_true",
        help="Display all review queue items",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Check if any blocking items exist (exit 0 if clean, 1 if blocked)",
    )
    parser.add_argument(
        "--approve", metavar="ID",
        help="Approve a review item by ID (prefix match)",
    )
    parser.add_argument(
        "--reject", metavar="ID",
        help="Reject and remove a review item by ID (prefix match)",
    )
    parser.add_argument(
        "--approve-all", action="store_true",
        help="Approve all non-blocking open items",
    )
    parser.add_argument(
        "--queue-path", default=str(REVIEW_QUEUE_PATH),
        help="Path to review queue JSON file",
    )
    args = parser.parse_args()

    queue_path = Path(args.queue_path)
    items = load_review_queue(queue_path)

    if args.show:
        _show(items)
        return 0

    if args.check:
        if has_blocking_items(items):
            blocking = [
                i for i in items
                if i.get("blocking") and i.get("status") == "open"
            ]
            print(f"  BLOCKED: {len(blocking)} blocking item(s) remain.")
            for item in blocking:
                rid = item.get("review_id", "?")[:16]
                issue = item.get("issue_type", "?")
                print(f"    - [{rid}] {issue}")
            return 1
        else:
            print("  CLEAN: No blocking items. Ready to publish.")
            return 0

    if args.approve:
        if _approve(items, args.approve):
            save_review_queue(queue_path, items)
        return 0

    if args.reject:
        if _reject(items, args.reject):
            save_review_queue(queue_path, items)
        return 0

    if args.approve_all:
        count = _approve_all_non_blocking(items)
        if count > 0:
            save_review_queue(queue_path, items)
            print(f"  Approved {count} non-blocking item(s).")
        else:
            print("  No non-blocking open items to approve.")
        return 0

    # Default: show
    _show(items)
    return 0


if __name__ == "__main__":
    sys.exit(main())
