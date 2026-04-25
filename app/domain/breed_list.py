"""Pure derivation of the visible Breed List from persisted state."""

from __future__ import annotations

from typing import Sequence

from app.domain.models import (
    BreedListRow,
    EggType,
    SortOrder,
    TargetRequirementProgress,
)


def derive_breed_list(
    progress_rows: Sequence[TargetRequirementProgress],
    egg_types: dict[int, EggType],
    sort_order: SortOrder = SortOrder.TIME_DESC,
) -> list[BreedListRow]:
    """Aggregate per-target progress into visible Breed List rows.

    Only rows with remaining > 0 are included.
    """
    totals: dict[int, int] = {}
    satisfied: dict[int, int] = {}

    for p in progress_rows:
        totals[p.egg_type_id] = totals.get(p.egg_type_id, 0) + p.required_count
        satisfied[p.egg_type_id] = satisfied.get(p.egg_type_id, 0) + p.satisfied_count

    rows: list[BreedListRow] = []
    for egg_id, total in totals.items():
        bred = satisfied.get(egg_id, 0)
        remaining = total - bred
        if remaining <= 0:
            continue
        et = egg_types.get(egg_id)
        if et is None:
            continue
        rows.append(
            BreedListRow(
                egg_type_id=egg_id,
                name=et.name,
                breeding_time_seconds=et.breeding_time_seconds,
                breeding_time_display=et.breeding_time_display,
                egg_image_path=et.egg_image_path,
                total_needed=total,
                bred_count=bred,
                remaining=remaining,
                elements=et.elements,
            )
        )

    return sorted(rows, key=_sort_key(sort_order))


def _sort_key(order: SortOrder):
    if order == SortOrder.TIME_DESC:
        return lambda r: (-r.breeding_time_seconds, r.name)
    if order == SortOrder.TIME_ASC:
        return lambda r: (r.breeding_time_seconds, r.name)
    if order == SortOrder.REMAINING_DESC:
        return lambda r: (-r.remaining, r.name)
    if order == SortOrder.NAME_ASC:
        return lambda r: r.name.lower()
    return lambda r: (-r.breeding_time_seconds, r.name)
