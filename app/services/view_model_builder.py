"""Pure functions that build UI ViewModels from raw repo data.

Extracted from AppService so command orchestration and view derivation
can evolve independently. None of these functions hold connection state —
all inputs are passed explicitly.
"""

from __future__ import annotations

import sqlite3
from typing import Sequence

from app.assets import resolver
from app.domain.breed_list import derive_breed_list
from app.domain.models import (
    EggType,
    Monster,
    MonsterRequirement,
    MonsterType,
    SortOrder,
    TargetRequirementProgress,
)
from app.repositories import monster_repo
from app.services.viewmodels import (
    BreedListRowViewModel,
    ConsumerCardViewModel,
    InWorkMonsterRowViewModel,
    SettingsDataRowViewModel,
)


_TYPE_LABELS = {
    MonsterType.WUBLIN: "Wublin",
    MonsterType.CELESTIAL: "Celestial",
    MonsterType.AMBER: "Amber Vessel",
}

_DURATION_LABELS = {
    MonsterType.WUBLIN: "N/A",
    MonsterType.CELESTIAL: "Permanent",
    MonsterType.AMBER: "30 Days",
}


def build_breed_list_vms(
    progress: Sequence[TargetRequirementProgress],
    egg_types_map: dict[int, EggType],
    sort_order: SortOrder,
    consumer_cards_by_egg: dict[int, tuple[ConsumerCardViewModel, ...]],
) -> list[BreedListRowViewModel]:
    """Build the ordered list of BreedListRowViewModels."""
    rows = derive_breed_list(progress, egg_types_map, sort_order)
    return [
        BreedListRowViewModel(
            egg_type_id=r.egg_type_id,
            name=r.name,
            breeding_time_display=r.breeding_time_display,
            egg_image_path=resolver.resolve(r.egg_image_path),
            bred_count=r.bred_count,
            total_needed=r.total_needed,
            remaining=r.remaining,
            progress_fraction=r.bred_count / r.total_needed if r.total_needed else 0,
            elements=r.elements,
            consumer_cards=consumer_cards_by_egg.get(r.egg_type_id, ()),
        )
        for r in rows
    ]


def build_consumer_cards(
    conn_content: sqlite3.Connection,
    active_monster_ids: set[int],
    requirements_cache: dict[int, list[MonsterRequirement]],
) -> dict[int, tuple[ConsumerCardViewModel, ...]]:
    """For each egg type, the deduped list of active-target monsters that consume it."""
    if not active_monster_ids:
        return {}

    monsters = [
        monster_repo.fetch_monster_by_id(conn_content, mid)
        for mid in active_monster_ids
    ]
    monsters = [m for m in monsters if m is not None]
    monsters.sort(key=lambda m: m.name.lower())

    cards_by_egg: dict[int, list[ConsumerCardViewModel]] = {}
    seen: dict[int, set[int]] = {}

    for m in monsters:
        for req in requirements_cache.get(m.id, []):
            egg_seen = seen.setdefault(req.egg_type_id, set())
            if m.id in egg_seen:
                continue
            egg_seen.add(m.id)
            cards_by_egg.setdefault(req.egg_type_id, []).append(
                ConsumerCardViewModel(
                    monster_id=m.id,
                    name=m.name,
                    image_path=resolver.resolve(m.image_path),
                    monster_type=m.monster_type.value,
                    is_placeholder=m.is_placeholder,
                )
            )

    return {eid: tuple(cards) for eid, cards in cards_by_egg.items()}


def build_inwork_vms(
    conn_content: sqlite3.Connection,
    grouped: dict[int, int],
) -> dict[str, list[InWorkMonsterRowViewModel]]:
    """Build the in-work-by-type mapping from a {monster_id: count} dict."""
    by_type: dict[str, list[InWorkMonsterRowViewModel]] = {}
    for mid, count in grouped.items():
        m = monster_repo.fetch_monster_by_id(conn_content, mid)
        if m is None:
            continue
        display = f"{m.name} × {count}" if count > 1 else m.name
        by_type.setdefault(m.monster_type.value, []).append(
            InWorkMonsterRowViewModel(
                monster_id=m.id,
                name=m.name,
                monster_type=m.monster_type.value,
                image_path=resolver.resolve(m.image_path),
                is_placeholder=m.is_placeholder,
                count=count,
                display_name=display,
            )
        )
    return by_type


def build_settings_data_rows(
    monsters: Sequence[Monster],
    requirements_map: dict[int, list[MonsterRequirement]],
) -> list[SettingsDataRowViewModel]:
    """Build the rows displayed in the Settings → Data table."""
    rows: list[SettingsDataRowViewModel] = []
    for monster in monsters:
        requirements = requirements_map.get(monster.id, [])
        eggs_required = sum(req.quantity for req in requirements)
        rows.append(
            SettingsDataRowViewModel(
                monster_id=monster.id,
                monster_name=monster.name,
                monster_type=monster.monster_type.value,
                monster_type_label=_TYPE_LABELS[monster.monster_type],
                image_path=resolver.resolve(monster.image_path),
                is_placeholder=monster.is_placeholder,
                eggs_required_display=_format_egg_total(eggs_required),
                duration_display=_DURATION_LABELS[monster.monster_type],
            )
        )
    return rows


def _format_egg_total(total: int) -> str:
    unit = "Egg" if total == 1 else "Eggs"
    return f"{total} {unit}"
