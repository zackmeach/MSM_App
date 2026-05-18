"""Tests for wgCategories-based element parsing in the wiki fetcher.

Validates ``_parse_elements_from_categories`` against committed,
version-controlled fixtures in ``tests/unit/fixtures/`` — small synthetic
pages whose RLCONF ``"wgCategories"`` array mirrors the real Fandom shape
and includes over-match trap noise. This makes the suite fully
deterministic and reproducible on a fresh clone or in CI: it never reads
the gitignored ``pipeline/raw/cache/`` page dump.

No network access — all input is in-process fixture strings.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pipeline.raw.wiki_fetcher import (
    ELEMENT_ORDER,
    _parse_elements_from_categories,
)

from tests.unit.fixtures.wiki_category_pages import (
    EXPECTED_ELEMENTS,
    FIXTURE_PAGES,
)


@pytest.mark.parametrize(
    "name",
    sorted(EXPECTED_ELEMENTS),
    ids=sorted(EXPECTED_ELEMENTS),
)
def test_parse_elements_from_categories_matches_ground_truth(name: str):
    """Each committed fixture parses to exactly its known element set."""
    html_text = FIXTURE_PAGES[name]
    parsed = _parse_elements_from_categories(html_text)

    assert parsed, f"{name}: parsed no elements (expected non-empty)"
    assert sorted(parsed) == sorted(EXPECTED_ELEMENTS[name]), (
        f"{name}: expected {sorted(EXPECTED_ELEMENTS[name])}, "
        f"got {sorted(parsed)}"
    )


class TestElementOrderDeterminism:
    """ELEMENT_ORDER produces a stable canonical ordering."""

    def test_scrambled_categories_return_canonical_order(self):
        # Categories deliberately out of canonical order, plus over-match
        # traps: "Cold Island" must not be captured as the Cold element,
        # and "Triple Element Monsters" must not be captured at all.
        scrambled = (
            'window.RLCONF = {"wgCategories":["Monsters",'
            '"Triple Element Monsters",'
            '"Fire Element","Cold Island","Air Element",'
            '"Plant Element","Earth Element"],"wgFoo":1};'
        )
        parsed = _parse_elements_from_categories(scrambled)

        assert parsed == [
            "natural-plant",
            "natural-air",
            "natural-earth",
            "natural-fire",
        ]

    def test_order_is_independent_of_input_order(self):
        a = _parse_elements_from_categories(
            '"wgCategories":["Water Element","Plant Element","Air Element"]'
        )
        b = _parse_elements_from_categories(
            '"wgCategories":["Air Element","Water Element","Plant Element"]'
        )
        assert a == b == ["natural-plant", "natural-water", "natural-air"]

    def test_element_order_leads_with_naturals_then_magicals(self):
        assert ELEMENT_ORDER[:10] == (
            "natural-plant", "natural-cold", "natural-water",
            "natural-air", "natural-earth", "natural-fire",
            "magical-bone", "magical-faerie", "magical-light",
            "magical-psychic",
        )

    def test_element_order_has_no_duplicates(self):
        assert len(ELEMENT_ORDER) == len(set(ELEMENT_ORDER))

    def test_empty_when_no_categories_blob(self):
        assert _parse_elements_from_categories("<html>no blob</html>") == []


class TestOverMatchTraps:
    """The parser must reject categories that merely resemble elements."""

    def test_island_adjacent_to_element_yields_no_phantom(self):
        # "Cold Island" sits right next to "Cold Element"; only the
        # genuine element must be captured.
        html_text = (
            '"wgCategories":["Cold Island","Cold Element",'
            '"Plant Island","Plant Element"]'
        )
        assert _parse_elements_from_categories(html_text) == [
            "natural-plant",
            "natural-cold",
        ]

    def test_count_category_not_captured(self):
        # None of the "<word> Element Monsters" count categories may be
        # mistaken for an element.
        for word in ("Single", "Double", "Triple", "Quad"):
            html_text = (
                f'"wgCategories":["{word} Element Monsters",'
                '"Earth Element"]'
            )
            assert _parse_elements_from_categories(html_text) == [
                "natural-earth"
            ]

    def test_generic_monster_categories_ignored(self):
        html_text = (
            '"wgCategories":["Monsters","Natural Monsters",'
            '"Magical Monsters","Water Element"]'
        )
        assert _parse_elements_from_categories(html_text) == [
            "natural-water"
        ]


def test_cached_pages_spot_check_if_present():
    """If real cached wiki pages happen to exist, spot-check a few.

    This is purely opportunistic. The committed fixtures above are the
    authoritative, CI-safe coverage. When ``pipeline/raw/cache/`` is
    absent (fresh clone / CI), this skips cleanly so it never fails.
    """
    cache_dir = (
        Path(__file__).resolve().parent.parent.parent
        / "pipeline" / "raw" / "cache"
    )
    if not cache_dir.is_dir():
        pytest.skip("pipeline/raw/cache absent — committed fixtures cover this")

    checked = 0
    for name, expected in EXPECTED_ELEMENTS.items():
        matches = sorted(cache_dir.glob(f"fandom_wiki_{name}_elements_*.raw"))
        if not matches:
            continue
        html_text = matches[0].read_text(encoding="utf-8", errors="replace")
        parsed = _parse_elements_from_categories(html_text)
        assert sorted(parsed) == sorted(expected), (
            f"{name} (cached): expected {sorted(expected)}, "
            f"got {sorted(parsed)}"
        )
        checked += 1

    if checked == 0:
        pytest.skip("no matching cached pages for known monsters")
