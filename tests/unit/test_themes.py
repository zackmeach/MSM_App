"""Unit tests for app.ui.themes — pure Python, no Qt dependency."""

from __future__ import annotations

import pytest

from app.ui.themes import (
    DEFAULT_THEME,
    FONT_SIZE_OPTIONS,
    THEMES,
    THEME_NAMES,
    build_stylesheet,
    element_icon_path,
    get_active_font_offset,
    get_active_theme,
    island_icon_path,
    placeholder_tones_2,
    placeholder_tones_3,
    scaled,
    set_active,
)


@pytest.fixture(autouse=True)
def _reset_active_theme():
    """Restore defaults after each test to avoid cross-test pollution."""
    set_active(DEFAULT_THEME, 0)
    yield
    set_active(DEFAULT_THEME, 0)


class TestSetActive:
    """set_active() stores theme name and font offset."""

    def test_default_state(self):
        assert get_active_theme() == DEFAULT_THEME
        assert get_active_font_offset() == 0

    def test_set_valid_theme(self):
        set_active("Classic Dark", 4)
        assert get_active_theme() == "Classic Dark"
        assert get_active_font_offset() == 4

    def test_invalid_theme_falls_back(self):
        set_active("Nonexistent Theme", 2)
        assert get_active_theme() == DEFAULT_THEME
        assert get_active_font_offset() == 2

    def test_negative_offset(self):
        set_active(DEFAULT_THEME, -3)
        assert get_active_font_offset() == -3


class TestScaled:
    """scaled() adds the active font offset to a base dimension."""

    def test_zero_offset(self):
        set_active(DEFAULT_THEME, 0)
        assert scaled(100) == 100

    def test_positive_offset(self):
        set_active(DEFAULT_THEME, 6)
        assert scaled(100) == 106

    def test_negative_offset(self):
        set_active(DEFAULT_THEME, -2)
        assert scaled(50) == 48


class TestPlaceholderTones:
    """placeholder_tones_3/2 return correct tuples for known types."""

    def test_tones_3_wublin(self):
        result = placeholder_tones_3("wublin")
        assert isinstance(result, tuple)
        assert len(result) == 3
        assert all(isinstance(c, str) for c in result)

    def test_tones_3_celestial(self):
        result = placeholder_tones_3("celestial")
        assert len(result) == 3

    def test_tones_3_amber(self):
        result = placeholder_tones_3("amber")
        assert len(result) == 3

    def test_tones_3_unknown_type_returns_fallback(self):
        result = placeholder_tones_3("unknown")
        assert len(result) == 3
        # Fallback uses theme's thumb_fallback_bg, thumb_fallback_border, accent
        t = THEMES[DEFAULT_THEME]
        assert result == (t["thumb_fallback_bg"], t["thumb_fallback_border"], t["accent"])

    def test_tones_2_wublin(self):
        result = placeholder_tones_2("wublin")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_tones_2_unknown_type_returns_fallback(self):
        result = placeholder_tones_2("unknown")
        t = THEMES[DEFAULT_THEME]
        assert result == (t["thumb_fallback_bg"], t["accent"])

    def test_tones_change_with_theme(self):
        set_active("Deep Island Night")
        tones_din = placeholder_tones_3("wublin")
        set_active("Classic Dark")
        tones_cd = placeholder_tones_3("wublin")
        assert tones_din != tones_cd


class TestBuildStylesheet:
    """build_stylesheet() produces a non-empty QSS string."""

    def test_returns_nonempty_string(self):
        qss = build_stylesheet()
        assert isinstance(qss, str)
        assert len(qss) > 100

    def test_contains_key_selectors(self):
        qss = build_stylesheet()
        assert "QMainWindow" in qss
        assert "#navBar" in qss
        assert "#catalogBadge" in qss
        assert "#eggRow" in qss

    def test_explicit_theme_overrides_active(self):
        set_active("Deep Island Night")
        qss = build_stylesheet(theme="Classic Dark")
        # Classic Dark uses a different bg color
        assert "#121317" in qss

    def test_explicit_offset_affects_sizes(self):
        qss_0 = build_stylesheet(font_offset=0)
        qss_6 = build_stylesheet(font_offset=6)
        # Font sizes should differ — 13+0=13 vs 13+6=19
        assert "13px" in qss_0
        assert "19px" in qss_6

    def test_all_themes_produce_valid_qss(self):
        for name in THEME_NAMES:
            qss = build_stylesheet(theme=name)
            assert len(qss) > 100, f"Theme '{name}' produced short QSS"


class TestAssetPathHelpers:
    """element_icon_path / island_icon_path return the canonical relative paths."""

    def test_element_icon_path_format(self):
        assert element_icon_path("natural-cold") == "images/elements/natural-cold.png"

    def test_element_icon_path_handles_arbitrary_keys(self):
        # The helper is a pure formatter — any key works, resolution happens elsewhere.
        assert element_icon_path("magical-faerie") == "images/elements/magical-faerie.png"

    def test_island_icon_path_format(self):
        assert island_icon_path("wublin-island") == "images/islands/wublin-island.png"
        assert island_icon_path("celestial-island") == "images/islands/celestial-island.png"
        assert island_icon_path("amber-island") == "images/islands/amber-island.png"


class TestFontSizeOptions:
    """FONT_SIZE_OPTIONS is structured correctly."""

    def test_has_at_least_three_options(self):
        assert len(FONT_SIZE_OPTIONS) >= 3

    def test_each_option_is_label_offset_pair(self):
        for label, offset in FONT_SIZE_OPTIONS:
            assert isinstance(label, str)
            assert isinstance(offset, int)

    def test_offsets_are_ascending(self):
        offsets = [o for _, o in FONT_SIZE_OPTIONS]
        assert offsets == sorted(offsets)
