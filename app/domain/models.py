"""Core domain dataclasses and enums."""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True)
class Monster:
    id: int
    name: str
    monster_type: MonsterType
    image_path: str
    is_placeholder: bool
    wiki_slug: str
    is_deprecated: bool = False


@dataclass(frozen=True)
class EggType:
    id: int
    name: str
    breeding_time_seconds: int
    breeding_time_display: str
    egg_image_path: str
    is_placeholder: bool = True


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


@dataclass(frozen=True)
class TargetRequirementProgress:
    active_target_id: int
    egg_type_id: int
    required_count: int
    satisfied_count: int

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


@dataclass(frozen=True)
class ReconciliationResult:
    """Delta produced by reconcile(); describes what changed."""

    deleted_progress_rows: list[tuple[int, int]]
    clipped_rows: list[tuple[int, int, int]]
    prior_snapshot: list[TargetRequirementProgress]
