"""Tests for breed_list derivation and sort orders."""

from __future__ import annotations

import pytest

from app.domain.breed_list import derive_breed_list
from app.domain.models import EggType, SortOrder, TargetRequirementProgress


def _egg(eid: int, name: str, seconds: int) -> EggType:
    return EggType(id=eid, name=name, breeding_time_seconds=seconds,
                   breeding_time_display=f"{seconds}s", egg_image_path="", is_placeholder=True)


_EGGS = {
    1: _egg(1, "Mammott", 1800),
    2: _egg(2, "Bowgart", 30600),
    3: _egg(3, "Tweedle", 1800),
}


class TestDerivation:
    def test_empty_progress_returns_empty_list(self):
        assert derive_breed_list([], _EGGS) == []

    def test_single_target_aggregation(self):
        progress = [
            TargetRequirementProgress(1, 1, 4, 1),  # Mammott: need 4, have 1
            TargetRequirementProgress(1, 2, 2, 0),  # Bowgart: need 2, have 0
        ]
        rows = derive_breed_list(progress, _EGGS)
        assert len(rows) == 2
        mammott = next(r for r in rows if r.egg_type_id == 1)
        assert mammott.total_needed == 4
        assert mammott.bred_count == 1
        assert mammott.remaining == 3

    def test_multi_target_aggregation(self):
        progress = [
            TargetRequirementProgress(1, 1, 4, 2),  # target 1: Mammott 4, bred 2
            TargetRequirementProgress(2, 1, 3, 1),  # target 2: Mammott 3, bred 1
        ]
        rows = derive_breed_list(progress, _EGGS)
        assert len(rows) == 1
        assert rows[0].total_needed == 7
        assert rows[0].bred_count == 3
        assert rows[0].remaining == 4

    def test_completed_rows_excluded(self):
        progress = [
            TargetRequirementProgress(1, 1, 4, 4),  # fully satisfied
            TargetRequirementProgress(1, 2, 2, 0),
        ]
        rows = derive_breed_list(progress, _EGGS)
        assert len(rows) == 1
        assert rows[0].egg_type_id == 2

    def test_all_completed_returns_empty(self):
        progress = [
            TargetRequirementProgress(1, 1, 4, 4),
            TargetRequirementProgress(1, 2, 2, 2),
        ]
        rows = derive_breed_list(progress, _EGGS)
        assert rows == []


class TestSorting:
    def _make_progress(self):
        return [
            TargetRequirementProgress(1, 1, 4, 1),  # Mammott 1800s, remaining 3
            TargetRequirementProgress(1, 2, 2, 0),  # Bowgart 30600s, remaining 2
            TargetRequirementProgress(1, 3, 5, 2),  # Tweedle 1800s, remaining 3
        ]

    def test_sort_time_desc(self):
        rows = derive_breed_list(self._make_progress(), _EGGS, SortOrder.TIME_DESC)
        assert rows[0].name == "Bowgart"

    def test_sort_time_asc(self):
        rows = derive_breed_list(self._make_progress(), _EGGS, SortOrder.TIME_ASC)
        assert rows[0].name == "Mammott"

    def test_sort_remaining_desc(self):
        rows = derive_breed_list(self._make_progress(), _EGGS, SortOrder.REMAINING_DESC)
        assert rows[0].remaining >= rows[1].remaining

    def test_sort_name_asc(self):
        rows = derive_breed_list(self._make_progress(), _EGGS, SortOrder.NAME_ASC)
        names = [r.name for r in rows]
        assert names == sorted(names, key=str.lower)
