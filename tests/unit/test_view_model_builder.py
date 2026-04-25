"""Tests for view_model_builder pure functions."""

from __future__ import annotations

import pytest

from app.domain.models import SortOrder, TargetRequirementProgress
from app.repositories import monster_repo
from app.services import view_model_builder as vmb


@pytest.fixture
def egg_types_map(content_conn):
    return monster_repo.fetch_egg_types_map(content_conn)


@pytest.fixture
def requirements_cache(content_conn):
    return monster_repo.fetch_all_requirements(content_conn)


class TestBuildConsumerCards:
    def test_empty_active_returns_empty_dict(self, content_conn, requirements_cache):
        result = vmb.build_consumer_cards(content_conn, set(), requirements_cache)
        assert result == {}

    def test_cards_keyed_by_egg_id(self, content_conn, requirements_cache, id_maps):
        # Zynth (in conftest seed) requires Bowgart, Clamble, PomPom, Thumpies
        zynth_id = id_maps["monsters"]["Zynth"]
        result = vmb.build_consumer_cards(content_conn, {zynth_id}, requirements_cache)
        bowgart_id = id_maps["eggs"]["Bowgart"]
        assert bowgart_id in result
        assert any(c.name == "Zynth" for c in result[bowgart_id])

    def test_consumer_dedup_per_egg(self, content_conn, requirements_cache, id_maps):
        zynth_id = id_maps["monsters"]["Zynth"]
        result = vmb.build_consumer_cards(content_conn, {zynth_id}, requirements_cache)
        for cards in result.values():
            ids = [c.monster_id for c in cards]
            assert len(ids) == len(set(ids)), "Cards should be deduped by monster_id"

    def test_multiple_consumers_share_an_egg(
        self, content_conn, requirements_cache, id_maps
    ):
        # Both Zynth and Poewk require Bowgart in the seed.
        zynth_id = id_maps["monsters"]["Zynth"]
        poewk_id = id_maps["monsters"]["Poewk"]
        bowgart_id = id_maps["eggs"]["Bowgart"]
        result = vmb.build_consumer_cards(
            content_conn, {zynth_id, poewk_id}, requirements_cache
        )
        names = {c.name for c in result[bowgart_id]}
        assert names == {"Zynth", "Poewk"}


class TestBuildBreedListVMs:
    def test_empty_progress_returns_empty_list(self, egg_types_map):
        result = vmb.build_breed_list_vms([], egg_types_map, SortOrder.TIME_DESC, {})
        assert result == []

    def test_passes_consumer_cards_through(self, egg_types_map, id_maps):
        bowgart_id = id_maps["eggs"]["Bowgart"]
        progress = [TargetRequirementProgress(1, bowgart_id, 4, 1, "")]
        cards = {bowgart_id: ()}
        rows = vmb.build_breed_list_vms(
            progress, egg_types_map, SortOrder.TIME_DESC, cards
        )
        assert len(rows) == 1
        assert rows[0].consumer_cards == ()
