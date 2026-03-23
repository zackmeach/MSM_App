"""Tests for the MSM Wiki fetcher module.

Uses mocked HTTP responses with sample wiki HTML to test parsing
without hitting the live wiki.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from pipeline.raw.source_cache import SourceCache
from pipeline.raw.wiki_fetcher import (
    FetchResult,
    _extract_monster_names_from_category,
    _is_base_monster,
    _parse_breeding_time,
    _parse_infobox_requirements,
    _parse_requirement_table,
    fetch_egg_data_from_requirements,
    fetch_monster_page,
)


# ── Sample HTML fixtures ────────────────────────────────────────────

CATEGORY_PAGE_HTML = """
<html><body>
<div class="category-page__members">
  <a class="category-page__member-link" title="Zynth" href="/wiki/Zynth">Zynth</a>
  <a class="category-page__member-link" title="Thwok" href="/wiki/Thwok">Thwok</a>
  <a class="category-page__member-link" title="Dwumrohl" href="/wiki/Dwumrohl">Dwumrohl</a>
  <a class="category-page__member-link" title="Category:Templates" href="/wiki/Category:Templates">Category:Templates</a>
  <a class="category-page__member-link" title="Rare Zynth" href="/wiki/Rare_Zynth">Rare Zynth</a>
  <a class="category-page__member-link" title="Epic Thwok" href="/wiki/Epic_Thwok">Epic Thwok</a>
  <a class="category-page__member-link" title="Wublin Island" href="/wiki/Wublin_Island">Wublin Island</a>
  <a class="category-page__member-link" title="Polarity" href="/wiki/Polarity">Polarity</a>
  <a class="category-page__member-link" title="Wublins" href="/wiki/Wublins">Wublins</a>
</div>
</body></html>
"""

CELESTIAL_CATEGORY_HTML = """
<html><body>
<div class="category-page__members">
  <a class="category-page__member-link" title="Attmoz" href="/wiki/Attmoz">Attmoz</a>
  <a class="category-page__member-link" title="Blasoom" href="/wiki/Blasoom">Blasoom</a>
  <a class="category-page__member-link" title="Adult Attmoz" href="/wiki/Adult_Attmoz">Adult Attmoz</a>
  <a class="category-page__member-link" title="Celestial Island" href="/wiki/Celestial_Island">Celestial Island</a>
  <a class="category-page__member-link" title="Celestials" href="/wiki/Celestials">Celestials</a>
  <a class="category-page__member-link" title="Monster Names/Celestials" href="/wiki/Monster_Names/Celestials">Monster Names/Celestials</a>
</div>
</body></html>
"""

# Realistic infobox HTML matching actual Fandom wiki structure
MONSTER_PAGE_HTML = """
<html><body>
<h1>Zynth</h1>
<div data-source="wublin inventory" class="pi-item pi-data">
  <h3 class="pi-data-label">Wublin Inventory</h3>
  <div class="pi-data-value pi-font"><span typeof="mw:File"><a href="/wiki/Pango" title="Pango"><img alt="Pango-egg" src="placeholder.gif" width="40" height="35" class="mw-file-element"></a></span><span style="margin-left: -7px;"><b><sup>x1</sup></b></span><span typeof="mw:File"><a href="/wiki/Oaktopus" title="Oaktopus"><img alt="Oaktopus-egg" src="placeholder.gif" width="40" height="35" class="mw-file-element"></a></span><span style="margin-left: -7px;"><b><sup>x1</sup></b></span><span typeof="mw:File"><a href="/wiki/Drumpler" title="Drumpler"><img alt="Drumpler-egg" src="placeholder.gif" width="40" height="35" class="mw-file-element"></a></span><span style="margin-left: -7px;"><b><sup>x3</sup></b></span></div>
</div>
</body></html>
"""

MONSTER_PAGE_NO_REQUIREMENTS = """
<html><body>
<h1>TestMonster</h1>
<p>This monster has no requirement table.</p>
</body></html>
"""

# Fallback table-based requirements (not used on live wiki, but kept for robustness)
TABLE_BASED_PAGE_HTML = """
<html><body>
<h1>TableMonster</h1>
<table class="requirements-table">
  <tr><td>Egg</td><td>Quantity</td></tr>
  <tr><td><a href="/wiki/Noggin">Noggin</a></td><td>2</td></tr>
  <tr><td><a href="/wiki/Mammott">Mammott</a></td><td>1</td></tr>
</table>
</body></html>
"""

MALFORMED_PAGE_HTML = """
<html><body>
<table>
  <tr><td>Total</td><td>6</td></tr>
  <tr><td>Element</td><td>Fire</td></tr>
</table>
</body></html>
"""

# Higher quantities like Thwok's real data
THWOK_PAGE_HTML = """
<html><body>
<h1>Thwok</h1>
<div data-source="wublin inventory" class="pi-item pi-data">
  <h3 class="pi-data-label">Wublin Inventory</h3>
  <div class="pi-data-value pi-font"><span typeof="mw:File"><a href="/wiki/Entbrat" title="Entbrat"><img alt="Entbrat-egg" src="placeholder.gif" width="40" height="35"></a></span><span><b><sup>x1</sup></b></span><span typeof="mw:File"><a href="/wiki/Bowgart" title="Bowgart"><img alt="Bowgart-egg" src="placeholder.gif" width="40" height="35"></a></span><span><b><sup>x4</sup></b></span></div>
</div>
</body></html>
"""


# ── Tests ───────────────────────────────────────────────────────────


class TestExtractMonsterNames:
    """Test category page parsing."""

    def test_extracts_base_monster_names(self):
        names = _extract_monster_names_from_category(CATEGORY_PAGE_HTML)
        assert "Zynth" in names
        assert "Thwok" in names
        assert "Dwumrohl" in names

    def test_skips_category_pages(self):
        names = _extract_monster_names_from_category(CATEGORY_PAGE_HTML)
        assert "Category:Templates" not in names
        assert all(not n.startswith("Category:") for n in names)

    def test_skips_rare_epic_variants(self):
        names = _extract_monster_names_from_category(CATEGORY_PAGE_HTML)
        assert "Rare Zynth" not in names
        assert "Epic Thwok" not in names

    def test_skips_non_monster_pages(self):
        names = _extract_monster_names_from_category(CATEGORY_PAGE_HTML)
        assert "Wublin Island" not in names
        assert "Polarity" not in names
        assert "Wublins" not in names

    def test_celestial_filtering(self):
        names = _extract_monster_names_from_category(CELESTIAL_CATEGORY_HTML)
        assert "Attmoz" in names
        assert "Blasoom" in names
        assert "Adult Attmoz" not in names
        assert "Celestial Island" not in names
        assert "Celestials" not in names
        assert "Monster Names/Celestials" not in names

    def test_deduplicates_names(self):
        doubled_html = CATEGORY_PAGE_HTML + CATEGORY_PAGE_HTML
        names = _extract_monster_names_from_category(doubled_html)
        assert len(names) == len(set(names))

    def test_empty_page(self):
        names = _extract_monster_names_from_category("<html><body></body></html>")
        assert names == []


class TestIsBaseMonster:
    """Test the base monster filter."""

    def test_base_monster(self):
        assert _is_base_monster("Zynth") is True

    def test_rare_variant(self):
        assert _is_base_monster("Rare Zynth") is False

    def test_epic_variant(self):
        assert _is_base_monster("Epic Thwok") is False

    def test_adult_variant(self):
        assert _is_base_monster("Adult Attmoz") is False

    def test_non_monster_page(self):
        assert _is_base_monster("Wublin Island") is False
        assert _is_base_monster("Air Element") is False

    def test_category_page(self):
        assert _is_base_monster("Category:Wublins") is False


class TestParseInfoboxRequirements:
    """Test infobox-based requirement extraction (primary parser)."""

    def test_parses_zynth_requirements(self):
        reqs = _parse_infobox_requirements(MONSTER_PAGE_HTML)
        assert len(reqs) == 3

        egg_names = {r["egg_name"] for r in reqs}
        assert "Pango" in egg_names
        assert "Oaktopus" in egg_names
        assert "Drumpler" in egg_names

        drumpler = next(r for r in reqs if r["egg_name"] == "Drumpler")
        assert drumpler["quantity"] == 3

    def test_parses_higher_quantities(self):
        reqs = _parse_infobox_requirements(THWOK_PAGE_HTML)
        assert len(reqs) == 2

        entbrat = next(r for r in reqs if r["egg_name"] == "Entbrat")
        assert entbrat["quantity"] == 1

        bowgart = next(r for r in reqs if r["egg_name"] == "Bowgart")
        assert bowgart["quantity"] == 4

    def test_no_infobox(self):
        reqs = _parse_infobox_requirements(MONSTER_PAGE_NO_REQUIREMENTS)
        assert reqs == []


class TestParseRequirementTable:
    """Test the combined parser (infobox + table fallback)."""

    def test_prefers_infobox(self):
        """When infobox is present, use it instead of table fallback."""
        reqs = _parse_requirement_table(MONSTER_PAGE_HTML)
        assert len(reqs) == 3
        egg_names = {r["egg_name"] for r in reqs}
        assert "Pango" in egg_names

    def test_falls_back_to_table(self):
        """When no infobox, falls back to table row extraction."""
        reqs = _parse_requirement_table(TABLE_BASED_PAGE_HTML)
        assert len(reqs) == 2
        egg_names = {r["egg_name"] for r in reqs}
        assert "Noggin" in egg_names
        assert "Mammott" in egg_names

    def test_no_requirements(self):
        reqs = _parse_requirement_table(MONSTER_PAGE_NO_REQUIREMENTS)
        assert reqs == []

    def test_filters_non_egg_rows(self):
        reqs = _parse_requirement_table(MALFORMED_PAGE_HTML)
        egg_names = {r["egg_name"] for r in reqs}
        assert "Total" not in egg_names
        assert "Element" not in egg_names


class TestParseBreedingTime:
    """Test breeding time string parsing."""

    def test_hours(self):
        seconds, display = _parse_breeding_time("8h")
        assert seconds == 28800
        assert "8h" in display

    def test_hours_and_minutes(self):
        seconds, display = _parse_breeding_time("8h 30m")
        assert seconds == 30600

    def test_minutes(self):
        seconds, display = _parse_breeding_time("30m")
        assert seconds == 1800

    def test_seconds(self):
        seconds, display = _parse_breeding_time("5s")
        assert seconds == 5

    def test_empty(self):
        seconds, display = _parse_breeding_time("")
        assert seconds == 0

    def test_none(self):
        seconds, display = _parse_breeding_time(None)
        assert seconds == 0


class TestFetchMonsterPage:
    """Test fetching and parsing a single monster page."""

    @patch("pipeline.raw.wiki_fetcher._fetch_url")
    def test_successful_fetch(self, mock_fetch, tmp_path):
        mock_fetch.return_value = MONSTER_PAGE_HTML.encode("utf-8")
        cache = SourceCache(tmp_path / "cache")

        result = fetch_monster_page("Zynth", "wublin", cache)

        assert result.raw_payload is not None
        assert result.raw_payload["name"] == "Zynth"
        assert result.raw_payload["monster_type"] == "wublin"
        assert result.raw_payload["wiki_slug"] == "Zynth"
        assert result.raw_payload["is_placeholder"] is True
        assert len(result.raw_payload["requirements"]) == 3
        assert result.cache_entry is not None

    @patch("pipeline.raw.wiki_fetcher._fetch_url")
    def test_no_requirements_generates_review_item(self, mock_fetch, tmp_path):
        mock_fetch.return_value = MONSTER_PAGE_NO_REQUIREMENTS.encode("utf-8")
        cache = SourceCache(tmp_path / "cache")

        result = fetch_monster_page("TestMonster", "wublin", cache)

        assert result.raw_payload is not None
        assert len(result.review_items) >= 1
        assert any(
            r["issue_type"] == "source_payload_incomplete"
            for r in result.review_items
        )

    @patch("pipeline.raw.wiki_fetcher._fetch_url")
    def test_fetch_failure_generates_review_item(self, mock_fetch, tmp_path):
        mock_fetch.side_effect = OSError("Network error")
        cache = SourceCache(tmp_path / "cache")

        result = fetch_monster_page("Zynth", "wublin", cache)

        assert result.raw_payload is None
        assert len(result.review_items) == 1
        assert result.review_items[0]["issue_type"] == "source_fetch_failed"
        assert result.review_items[0]["blocking"] is True

    @patch("pipeline.raw.wiki_fetcher._fetch_url")
    def test_cache_stores_payload(self, mock_fetch, tmp_path):
        mock_fetch.return_value = MONSTER_PAGE_HTML.encode("utf-8")
        cache = SourceCache(tmp_path / "cache")

        result = fetch_monster_page("Zynth", "wublin", cache)

        assert result.cache_entry is not None
        assert result.cache_entry.source_category == "fandom"
        assert "Zynth" in result.cache_entry.source_reference

        # Verify it's actually in the cache
        cached = cache.get("fandom", "wiki/Zynth")
        assert cached is not None
        assert cached.content_hash == result.cache_entry.content_hash


class TestFetchEggData:
    """Test egg extraction from monster requirements."""

    def test_extracts_unique_eggs(self):
        results = [
            FetchResult(
                raw_payload={
                    "name": "Zynth",
                    "monster_type": "wublin",
                    "requirements": [
                        {"egg_name": "Pango", "quantity": 1},
                        {"egg_name": "Oaktopus", "quantity": 1},
                    ],
                },
                cache_entry=None,
                review_items=[],
                source_reference="wiki/Zynth",
            ),
            FetchResult(
                raw_payload={
                    "name": "Thwok",
                    "monster_type": "wublin",
                    "requirements": [
                        {"egg_name": "Pango", "quantity": 3},  # same egg, different quantity
                        {"egg_name": "Tweedle", "quantity": 2},
                    ],
                },
                cache_entry=None,
                review_items=[],
                source_reference="wiki/Thwok",
            ),
        ]

        eggs = fetch_egg_data_from_requirements(results)
        egg_names = {e["name"] for e in eggs}

        assert "Pango" in egg_names
        assert "Oaktopus" in egg_names
        assert "Tweedle" in egg_names
        assert len(eggs) == 3  # unique eggs only

    def test_skips_results_without_payload(self):
        results = [
            FetchResult(
                raw_payload=None,
                cache_entry=None,
                review_items=[{"issue_type": "fetch_failed"}],
                source_reference="wiki/Failed",
            ),
        ]
        eggs = fetch_egg_data_from_requirements(results)
        assert eggs == []
