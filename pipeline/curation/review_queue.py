"""Manual review queue loader and validator."""

from __future__ import annotations

import json
from pathlib import Path

from pipeline.schemas.normalized import ValidationResult, validate_review_item


def load_review_queue(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array")
    return data


def save_review_queue(path: Path, items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
        f.write("\n")


def validate_review_queue(items: list[dict]) -> ValidationResult:
    r = ValidationResult()
    seen_ids: set[str] = set()
    for i, item in enumerate(items):
        validate_review_item(item, idx=i, result=r)
        rid = item.get("review_id", "")
        if rid:
            if rid in seen_ids:
                r.add(i, "review_id", f"duplicate review_id '{rid}'")
            seen_ids.add(rid)
    return r


def has_blocking_items(items: list[dict]) -> bool:
    return any(
        item.get("blocking") and item.get("status") == "open"
        for item in items
    )
