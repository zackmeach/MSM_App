"""Core domain dataclasses and enums."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class MonsterType(str, Enum):
    WUBLIN = "wublin"
    CELESTIAL = "celestial"
    AMBER = "amber"


class SortOrder(str, Enum):
    TIME_DESC = "time_desc"
    TIME_ASC = "time_asc"
    REMAINING_DESC = "remaining_desc"
    NAME_ASC = "name_asc"


# ── Stable identity helpers ──────────────────────────────────────────

_SLUG_RE = re.compile(r"[^a-z0-9-]")
_MULTI_HYPHEN = re.compile(r"-{2,}")


def canonical_slug(name: str) -> str:
    """Derive a canonical slug from a display name.

    Rules (from frozen spec):
      - lowercase ASCII only
      - spaces collapse to ``-``
      - punctuation removed except hyphen
      - no consecutive hyphens
      - leading/trailing hyphens stripped
    """
    s = name.lower().replace(" ", "-")
    s = _SLUG_RE.sub("", s)
    s = _MULTI_HYPHEN.sub("-", s)
    return s.strip("-")


def monster_content_key(monster_type: str, name: str) -> str:
    return f"monster:{monster_type}:{canonical_slug(name)}"


def egg_content_key(name: str) -> str:
    return f"egg:{canonical_slug(name)}"


# ── Domain models ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class Monster:
    id: int
    name: str
    monster_type: MonsterType
    image_path: str
    is_placeholder: bool
    wiki_slug: str
    is_deprecated: bool = False
    content_key: str = ""
    source_fingerprint: str = ""
    asset_source: str = "generated_placeholder"
    asset_sha256: str = ""
    deprecated_at_utc: str | None = None
    deprecation_reason: str | None = None


@dataclass(frozen=True)
class EggType:
    id: int
    name: str
    breeding_time_seconds: int
    breeding_time_display: str
    egg_image_path: str
    is_placeholder: bool = True
    content_key: str = ""
    is_deprecated: bool = False
    deprecated_at_utc: str | None = None
    deprecation_reason: str | None = None
    source_fingerprint: str = ""
    asset_source: str = "generated_placeholder"
    asset_sha256: str = ""
    elements: tuple[str, ...] = ()


@dataclass(frozen=True)
class MonsterRequirement:
    monster_id: int
    egg_type_id: int
    quantity: int


@dataclass(frozen=True)
class ActiveTarget:
    id: int
    monster_id: int
    added_at: str
    monster_key: str = ""


@dataclass(frozen=True)
class TargetRequirementProgress:
    active_target_id: int
    egg_type_id: int
    required_count: int
    satisfied_count: int
    egg_key: str = ""

    @property
    def remaining(self) -> int:
        return self.required_count - self.satisfied_count


@dataclass(frozen=True)
class BreedListRow:
    """Derived view of one egg-type row in the visible Breed List."""

    egg_type_id: int
    name: str
    breeding_time_seconds: int
    breeding_time_display: str
    egg_image_path: str
    total_needed: int
    bred_count: int
    remaining: int
    elements: tuple[str, ...] = ()
