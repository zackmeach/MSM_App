"""Theme definitions and QSS stylesheet generator.

Each theme is a color dictionary.  ``build_stylesheet(theme, font_offset)``
produces the full QSS string that ``MainWindow.setStyleSheet()`` consumes.

Widgets that set inline styles for placeholder thumbnails should call
``placeholder_tones_3`` / ``placeholder_tones_2`` to get colors that
match the active theme.
"""

from __future__ import annotations

# ── Theme colour palettes ────────────────────────────────────────────

_DEEP_ISLAND_NIGHT: dict[str, str] = {
    # surfaces
    "bg":              "#0b1222",
    "bg_sunken":       "#070e1a",
    "bg_low":          "#101828",
    "card":            "#141c2a",
    "border":          "#1c2636",
    "interactive":     "#1a2435",
    "elevated":        "#22304a",
    # accent
    "accent":          "#f0c050",
    "accent_dark":     "#d4920a",
    "accent_hover_lt": "#f5d070",
    "accent_hover_dk": "#d9a020",
    "accent_press_lt": "#d4a830",
    "accent_press_dk": "#b87808",
    "accent_focus":    "#f8dc80",
    "cta_text":        "#1a0e00",
    # text
    "text1":           "#e8e4df",
    "text2":           "#b8b0a0",
    "text3":           "#8a92a2",
    "text_muted":      "#909aa5",
    "text_disabled":   "#3a4050",
    # semantic
    "success":         "#a6e3a1",
    "error":           "#ffb4ab",
    # decorative
    "gradient_center": "#101a2a",
    "dashed_border":   "#1e3040",
    "tip_border":      "#1c2e42",
    "tip_bg_rgba":     "rgba(26, 36, 53, 0.85)",
    "icon_border":     "#2a3850",
    "card_hover_border": "#2a3a52",
    "scroll_rgba":     "rgba(240, 192, 80, 51)",
    "scroll_hover_rgba": "rgba(240, 192, 80, 80)",
    "search_focus_rgba": "rgba(240, 192, 80, 0.4)",
    "thumb_fallback_bg": "#151e30",
    "thumb_fallback_border": "#1c2840",
    # font
    "font_family":     '"Bahnschrift", "Segoe UI", sans-serif',
}

_CLASSIC_DARK: dict[str, str] = {
    # surfaces
    "bg":              "#121317",
    "bg_sunken":       "#0d0e12",
    "bg_low":          "#1a1b20",
    "card":            "#1f1f24",
    "border":          "#252530",
    "interactive":     "#292a2e",
    "elevated":        "#343439",
    # accent
    "accent":          "#d0bcff",
    "accent_dark":     "#9f78ff",
    "accent_hover_lt": "#ddd0ff",
    "accent_hover_dk": "#b08aff",
    "accent_press_lt": "#bfa8ee",
    "accent_press_dk": "#8a6ae8",
    "accent_focus":    "#e9ddff",
    "cta_text":        "#330080",
    # text
    "text1":           "#e3e2e7",
    "text2":           "#cbc3d7",
    "text3":           "#a09aa8",
    "text_muted":      "#a8a0b0",
    "text_disabled":   "#494454",
    # semantic
    "success":         "#a6e3a1",
    "error":           "#ffb4ab",
    # decorative
    "gradient_center": "#1e1a28",
    "dashed_border":   "#2d2a38",
    "tip_border":      "#2d2842",
    "tip_bg_rgba":     "rgba(52, 52, 57, 0.82)",
    "icon_border":     "#3a3548",
    "card_hover_border": "#3d3a4a",
    "scroll_rgba":     "rgba(208, 188, 255, 51)",
    "scroll_hover_rgba": "rgba(208, 188, 255, 80)",
    "search_focus_rgba": "rgba(208, 188, 255, 0.4)",
    "thumb_fallback_bg": "#262332",
    "thumb_fallback_border": "#343046",
    # font
    "font_family":     '"Segoe UI", "Inter", sans-serif',
}

THEMES: dict[str, dict[str, str]] = {
    "Deep Island Night": _DEEP_ISLAND_NIGHT,
    "Classic Dark": _CLASSIC_DARK,
}

THEME_NAMES: list[str] = list(THEMES.keys())

DEFAULT_THEME = "Deep Island Night"

# ── Per-type placeholder tones ───────────────────────────────────────

_PLACEHOLDER_3: dict[str, dict[str, tuple[str, str, str]]] = {
    "Deep Island Night": {
        "wublin":    ("#0e2228", "#1a4050", "#45e9d0"),
        "celestial": ("#2a2510", "#504010", "#ffba20"),
        "amber":     ("#2e201a", "#5a3525", "#ff8a65"),
    },
    "Classic Dark": {
        "wublin":    ("#1a2e31", "#275058", "#45e9d0"),
        "celestial": ("#352d12", "#5c4810", "#ffba20"),
        "amber":     ("#38251f", "#6a3b2d", "#ff8a65"),
    },
}

_PLACEHOLDER_2: dict[str, dict[str, tuple[str, str]]] = {
    "Deep Island Night": {
        "wublin":    ("#0e2228", "#45e9d0"),
        "celestial": ("#2a2510", "#ffba20"),
        "amber":     ("#2e201a", "#ff8a65"),
    },
    "Classic Dark": {
        "wublin":    ("#1a2e31", "#45e9d0"),
        "celestial": ("#352d12", "#ffba20"),
        "amber":     ("#38251f", "#ff8a65"),
    },
}

# ── Active theme state ───────────────────────────────────────────────

_active_theme: str = DEFAULT_THEME
_active_font_offset: int = 0


def set_active(theme: str, font_offset: int = 0) -> None:
    """Set the active theme and font-size offset."""
    global _active_theme, _active_font_offset
    _active_theme = theme if theme in THEMES else DEFAULT_THEME
    _active_font_offset = font_offset


def get_active_theme() -> str:
    return _active_theme


def get_active_font_offset() -> int:
    return _active_font_offset


def placeholder_tones_3(monster_type: str) -> tuple[str, str, str]:
    """(bg, border, fg) for the active theme."""
    t = THEMES[_active_theme]
    fallback = (t["thumb_fallback_bg"], t["thumb_fallback_border"], t["accent"])
    return _PLACEHOLDER_3.get(_active_theme, {}).get(monster_type, fallback)


def placeholder_tones_2(monster_type: str) -> tuple[str, str]:
    """(bg, fg) for the active theme."""
    t = THEMES[_active_theme]
    fallback = (t["thumb_fallback_bg"], t["accent"])
    return _PLACEHOLDER_2.get(_active_theme, {}).get(monster_type, fallback)


# ── Element-sigil asset helpers ──────────────────────────────────────

def element_icon_path(element_key: str) -> str:
    """Relative path under resources/ for an element sigil PNG.

    The path is resolved (cache > bundle > placeholder) by ``app.assets.resolver``.
    """
    return f"images/elements/{element_key}.png"


def island_icon_path(island_key: str) -> str:
    """Relative path under resources/ for an island/map icon PNG.

    Used for the Active Monsters section headers (wublin-island, celestial-island,
    amber-island).
    """
    return f"images/islands/{island_key}.png"


# ── Font-size helpers ────────────────────────────────────────────────

FONT_SIZE_OPTIONS: list[tuple[str, int]] = [
    ("Small",        0),
    ("Default",     +2),
    ("Large",       +4),
    ("Extra Large", +6),
]


def scaled(base: int) -> int:
    """Scale a fixed pixel dimension by the active font offset."""
    return base + _active_font_offset


def _sz(base: int) -> str:
    """Return a px font-size string adjusted by the active offset."""
    return f"{base + _active_font_offset}px"


# ── Stylesheet generator ────────────────────────────────────────────

def build_stylesheet(theme: str | None = None, font_offset: int | None = None) -> str:
    """Return the full QSS string for the given (or active) theme + font size."""
    name = theme if theme and theme in THEMES else _active_theme
    offset = font_offset if font_offset is not None else _active_font_offset
    t = THEMES[name]

    # local size helper using the provided offset
    def sz(base: int) -> str:
        return f"{base + offset}px"

    return f"""
        /* ── Base surfaces ── */
        QMainWindow {{ background-color: {t['bg']}; }}
        QWidget {{
            color: {t['text1']};
            font-family: {t['font_family']};
            font-size: {sz(13)};
        }}
        #pageStack, #pageCanvas, #catalogBrowserPanel, #activeRailPanel,
        #settingsScrollContent, #activeRailContent, #catalogGridContainer,
        #breedListContainer {{
            background-color: {t['bg']};
        }}
        #pageScrollViewport, #activeRailViewport, #catalogGridViewport,
        #breedListViewport {{
            background-color: {t['bg']};
        }}

        /* ── Navigation bar ── */
        #navBar {{
            background-color: {t['bg']};
            border-bottom: 1px solid {t['card']};
            min-height: {56 + offset * 2}px;
            max-height: {56 + offset * 2}px;
        }}
        #appTitle {{
            font-size: {sz(16)};
            font-weight: 700;
            color: {t['text1']};
            padding: 0 4px;
            letter-spacing: -0.3px;
        }}
        #navBtn {{
            background: transparent;
            color: {t['text3']};
            border: none;
            border-bottom: 2px solid transparent;
            border-radius: 0;
            padding: 18px 12px 16px 12px;
            font-size: {sz(13)};
            font-weight: 600;
        }}
        #navBtn:hover {{
            color: {t['text1']};
            background: transparent;
        }}
        #navBtn[active="true"] {{
            color: {t['accent']};
            border-bottom: 2px solid {t['accent']};
        }}
        #navBtn:focus {{
            color: {t['accent']};
        }}

        /* ── Utility buttons (undo / redo) ── */
        #utilityBtn {{
            background-color: transparent;
            color: {t['text_muted']};
            border: none;
            border-radius: 4px;
            padding: 6px 12px;
            font-size: {sz(12)};
        }}
        #utilityBtn:hover {{
            background-color: {t['interactive']};
            color: {t['text2']};
        }}
        #utilityBtn:disabled {{
            color: {t['text_disabled']};
            background: transparent;
        }}
        #utilityBtn:focus {{ border: 1px solid {t['accent']}; }}

        /* ── Panel titles ── */
        #panelTitle {{
            font-size: {sz(22)};
            font-weight: 800;
            color: {t['text1']};
            letter-spacing: -0.3px;
        }}
        #activeBadge {{
            background-color: {t['bg_low']};
            color: {t['text_muted']};
            border: 1px solid {t['border']};
            border-radius: 12px;
            padding: 4px 12px;
            font-size: {sz(12)};
        }}

        /* ── Breed List: empty state ── */
        #emptyStateContainer {{
            background: qradialgradient(
                cx:0.5, cy:0.5, radius:0.7, fx:0.5, fy:0.5,
                stop:0 {t['gradient_center']}, stop:1 {t['bg_low']});
            border: none;
            border-radius: 12px;
        }}
        #emptyStateIcon {{
            background-color: {t['interactive']};
            border: 1px solid {t['icon_border']};
            border-radius: 40px;
            color: {t['accent']};
            font-size: {sz(28)};
        }}
        #emptyStateTitle {{
            font-size: {sz(20)};
            font-weight: 700;
            color: {t['text1']};
        }}
        #emptyStateSubtitle {{
            font-size: {sz(14)};
            color: {t['text2']};
        }}

        /* ── Primary CTA button ── */
        #primaryBtn {{
            background-color: qlineargradient(
                spread:pad, x1:0, y1:0, x2:1, y2:1,
                stop:0 {t['accent']}, stop:1 {t['accent_dark']});
            color: {t['cta_text']};
            border: none;
            border-radius: 12px;
            padding: 12px 28px;
            font-size: {sz(14)};
            font-weight: 700;
        }}
        #primaryBtn:hover {{
            background-color: qlineargradient(
                spread:pad, x1:0, y1:0, x2:1, y2:1,
                stop:0 {t['accent_hover_lt']}, stop:1 {t['accent_hover_dk']});
        }}
        #primaryBtn:pressed {{
            background-color: qlineargradient(
                spread:pad, x1:0, y1:0, x2:1, y2:1,
                stop:0 {t['accent_press_lt']}, stop:1 {t['accent_press_dk']});
        }}
        #primaryBtn:focus {{ border: 2px solid {t['accent_focus']}; }}

        /* ── In-Work section cards ── */
        #sectionCard {{
            background-color: {t['card']};
            border: 1px solid {t['border']};
            border-radius: 12px;
        }}
        #sectionIcon {{
            background-color: {t['elevated']};
            border-radius: 12px;
            font-size: {sz(20)};
            min-width: 56px; max-width: 56px;
            min-height: 56px; max-height: 56px;
            padding: 0px;
        }}
        #sectionLabel {{
            font-size: {sz(16)};
            font-weight: 700;
            color: {t['text1']};
        }}
        #sectionBadge {{
            color: {t['text_muted']};
            font-size: {sz(11)};
            font-weight: 700;
            letter-spacing: 2px;
            /* Qt's sizeHint doesn't include trailing letter-spacing, so
               the last letter clips at the right edge without padding. */
            padding-right: 4px;
        }}
        #sectionBody {{
            background-color: {t['bg_sunken']};
            border: 1px dashed {t['dashed_border']};
            border-radius: 12px;
            min-height: 96px;
        }}
        #sectionEmptyText {{
            color: {t['text_muted']};
            font-size: {sz(13)};
            font-style: italic;
            padding: 4px 0;
        }}

        /* ── Getting Started card ── */
        #gettingStartedCard {{
            background-color: {t['tip_bg_rgba']};
            border: 1px solid {t['tip_border']};
            border-radius: 12px;
        }}
        #gettingStartedIcon {{
            background: transparent;
            font-size: {sz(20)};
            min-width: 24px; max-width: 24px;
            min-height: 24px; max-height: 24px;
        }}
        #gettingStartedTitle {{
            font-size: {sz(13)};
            font-weight: 700;
            color: {t['text1']};
        }}
        #gettingStartedText {{
            font-size: {sz(12)};
            color: {t['text2']};
        }}

        /* ── Egg row (Breed List) ── */
        #eggRow {{
            background-color: {t['card']};
            border: 1px solid {t['border']};
            border-radius: 10px;
        }}
        #eggRow:hover {{
            background-color: {t['interactive']};
            border: 1px solid {t['card_hover_border']};
        }}
        #eggIconContainer {{
            background-color: {t['elevated']};
            border-radius: 8px;
        }}
        #eggName {{
            font-weight: 600;
            font-size: {sz(14)};
            color: {t['text1']};
        }}
        #eggTime {{ color: {t['text2']}; font-size: {sz(12)}; }}
        #eggCounter {{
            font-size: {sz(13)};
            color: {t['accent']};
            font-weight: 500;
        }}

        /* ── In-work entry ── */
        #inworkEntry {{
            background-color: transparent;
            border-radius: 8px;
            border-left: 3px solid transparent;
        }}
        #inworkEntry:hover {{
            background-color: {t['interactive']};
            border-left: 3px solid {t['accent']};
        }}
        #inworkEntryName {{
            font-size: {sz(13)};
            color: {t['text1']};
        }}

        /* ── Standard buttons ── */
        QPushButton {{
            background-color: {t['interactive']};
            color: {t['text1']};
            border: none;
            border-radius: 6px;
            padding: 6px 16px;
            font-size: {sz(13)};
        }}
        QPushButton:hover {{ background-color: {t['elevated']}; }}
        QPushButton:pressed {{ background-color: {t['text_disabled']}; }}
        QPushButton:focus {{ border: 1px solid {t['accent']}; }}
        QPushButton:disabled {{
            background-color: {t['bg_low']};
            color: {t['text_disabled']};
        }}

        /* ── Form controls ── */
        QComboBox {{
            background-color: {t['interactive']};
            color: {t['text1']};
            border: 1px solid {t['elevated']};
            border-radius: 4px;
            padding: 4px 8px;
        }}
        QComboBox:focus {{ border: 1px solid {t['accent']}; }}
        QComboBox::drop-down {{ border: none; width: 24px; }}
        QComboBox::down-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid {t['text2']};
            width: 0; height: 0;
            margin-right: 6px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {t['interactive']};
            color: {t['text1']};
            selection-background-color: {t['elevated']};
        }}

        QLineEdit {{
            background-color: {t['interactive']};
            color: {t['text1']};
            border: 1px solid {t['elevated']};
            border-radius: 4px;
            padding: 6px 10px;
        }}
        QLineEdit:focus {{ border: 1px solid {t['accent']}; }}

        /* ── Scroll area ── */
        QScrollArea {{ border: none; background: transparent; }}
        QScrollBar:vertical {{
            background: transparent;
            width: 6px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {t['scroll_rgba']};
            border-radius: 3px;
            min-height: 20px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {t['scroll_hover_rgba']};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        QScrollBar:horizontal {{
            background: transparent;
            height: 6px;
            margin: 0;
        }}
        QScrollBar::handle:horizontal {{
            background: {t['scroll_rgba']};
            border-radius: 3px;
            min-width: 20px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {t['scroll_hover_rgba']};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: transparent;
        }}

        /* ── Catalog: subtitle ── */
        #catalogSubtitle {{
            color: {t['text2']};
            font-size: {sz(13)};
        }}

        /* ── Catalog: search ── */
        #catalogSearchRow {{
            background-color: {t['card']};
            border: 1px solid {t['border']};
            border-radius: 12px;
            min-height: 46px;
        }}
        #catalogSearchIcon {{
            color: {t['text_muted']};
            font-size: {sz(16)};
            min-width: 18px;
        }}
        #catalogSearch {{
            background-color: transparent;
            border: none;
            padding: 10px 0;
            font-size: {sz(13)};
            color: {t['text1']};
        }}
        #catalogSearchRow:focus-within {{
            border: 1px solid {t['search_focus_rgba']};
        }}

        /* ── Catalog: tab buttons ── */
        #catalogTabBtn {{
            background: transparent;
            color: {t['text3']};
            border: none;
            border-bottom: 2px solid transparent;
            border-radius: 0;
            padding: 8px 18px 8px 2px;
            font-size: {sz(13)};
            font-weight: 700;
        }}
        #catalogTabBtn:hover {{
            color: {t['text1']};
            background: transparent;
        }}
        #catalogTabBtn[active="true"] {{
            color: {t['accent']};
            border-bottom: 2px solid {t['accent']};
        }}

        /* ── Catalog: monster card ── */
        #catalogCard {{
            background-color: {t['card']};
            border: 1px solid {t['border']};
            border-radius: 12px;
        }}
        #catalogCard:hover {{
            background-color: {t['interactive']};
            border: 1px solid {t['card_hover_border']};
        }}
        #catalogCardImage {{
            background-color: {t['bg_sunken']};
            border-radius: 12px;
        }}
        #catalogCardName {{
            font-size: {sz(15)};
            font-weight: 700;
            color: {t['text1']};
        }}

        /* ── Catalog: no-results ── */
        #catalogNoResults {{
            color: {t['text_muted']};
            font-size: {sz(14)};
            padding: 48px 0;
        }}

        /* ── Progress bar ── */
        QProgressBar {{
            background-color: {t['interactive']};
            border: none;
            border-radius: 4px;
            max-height: 8px;
            min-height: 8px;
        }}
        QProgressBar::chunk {{
            background-color: {t['success']};
            border-radius: 4px;
        }}

        /* ── Toast notification ── */
        #toast {{
            background-color: {t['elevated']};
            color: {t['text1']};
            border: 1px solid {t['accent']};
            border-radius: 8px;
            padding: 8px 20px;
            font-size: {sz(13)};
            font-weight: 500;
        }}

        /* ── Tooltip ── */
        QToolTip {{
            background-color: {t['interactive']};
            color: {t['text1']};
            border: 1px solid {t['elevated']};
            padding: 4px 8px;
        }}

        /* ── Settings: page subtitle ── */
        #settingsSubtitle {{
            color: {t['text2']};
            font-size: {sz(13)};
        }}

        /* ── Settings: card surfaces ── */
        #settingsCard {{
            background-color: {t['card']};
            border: 1px solid {t['border']};
            border-radius: 12px;
        }}
        #settingsCardLow {{
            background-color: {t['bg_low']};
            border: 1px solid {t['border']};
            border-radius: 12px;
        }}
        #settingsCardIcon {{
            background-color: {t['elevated']};
            border-radius: 8px;
            font-size: {sz(18)};
            min-width: 40px; max-width: 40px;
            min-height: 40px; max-height: 40px;
        }}
        #settingsCardTitle {{
            font-size: {sz(16)};
            font-weight: 700;
            color: {t['text1']};
        }}
        #settingsSupportingText {{
            color: {t['text2']};
            font-size: {sz(13)};
        }}

        /* ── Settings: info rows ── */
        #settingsInfoLabel {{
            color: {t['text2']};
            font-size: {sz(11)};
            font-weight: 600;
            letter-spacing: 1px;
        }}
        #settingsInfoValue {{
            font-size: {sz(14)};
            font-weight: 700;
            color: {t['accent']};
        }}
        #settingsInfoDivider {{
            background-color: {t['border']};
            max-height: 1px;
            min-height: 1px;
        }}

        /* ── Settings: status strip ── */
        #settingsStatusStrip {{
            background-color: {t['bg_sunken']};
            border: 1px solid {t['border']};
            border-radius: 12px;
        }}
        #settingsStatusBadge {{
            font-size: {sz(10)};
            font-weight: 700;
            letter-spacing: 2px;
        }}
        #settingsStatusBadge[tone="neutral"] {{ color: {t['text_muted']}; }}
        #settingsStatusBadge[tone="accent"]  {{ color: {t['accent']}; }}
        #settingsStatusBadge[tone="success"] {{ color: {t['success']}; }}
        #settingsStatusBadge[tone="error"]   {{ color: {t['error']}; }}

        #settingsStatusDot {{
            border-radius: 4px;
        }}
        #settingsStatusDot[tone="neutral"] {{ background-color: {t['text_muted']}; }}
        #settingsStatusDot[tone="accent"]  {{ background-color: {t['accent']}; }}
        #settingsStatusDot[tone="success"] {{ background-color: {t['success']}; }}
        #settingsStatusDot[tone="error"]   {{ background-color: {t['error']}; }}

        /* ── Settings: disclaimer ── */
        #settingsDisclaimerText {{
            color: {t['text2']};
            font-size: {sz(11)};
            line-height: 1.6;
        }}

        /* ── Settings: data table ── */
        #settingsDataCard {{
            background-color: {t['card']};
            border: 1px solid {t['border']};
            border-radius: 12px;
        }}
        #settingsDataTable {{
            background-color: transparent;
            border: none;
            gridline-color: transparent;
            outline: 0;
        }}
        #settingsDataTable::item {{
            border-bottom: 1px solid {t['border']};
            padding: 10px 12px;
        }}
        #settingsDataTable QTableCornerButton::section {{
            background-color: {t['interactive']};
            border: none;
        }}
        #settingsDataTable QHeaderView::section {{
            background-color: {t['interactive']};
            color: {t['text_muted']};
            border: none;
            border-bottom: 1px solid {t['border']};
            padding: 10px 12px;
            font-size: {sz(12)};
            font-weight: 700;
        }}
        #settingsDataThumbFallback {{
            background-color: {t['thumb_fallback_bg']};
            border: 1px solid {t['thumb_fallback_border']};
            border-radius: 8px;
            color: {t['accent']};
            font-size: {sz(12)};
            font-weight: 700;
        }}

        /* ── MonsterCard (compact in-work cards) ── */
        #monsterCard {{
            background-color: {t['interactive']}; border-radius: 8px;
        }}
        #monsterCard:hover {{ background-color: {t['elevated']}; }}
        #cardLabel {{ font-size: {sz(11)}; color: {t['text1']}; }}

        /* ── Catalog: active-count badge ── */
        #catalogBadge {{
            background-color: {t['accent']};
            color: {t['cta_text']};
            font-size: {sz(10)};
            font-weight: 700;
            border-radius: {(20 + offset) // 2}px;
            min-width: {20 + offset}px;
            max-height: {20 + offset}px;
            min-height: {20 + offset}px;
            padding: 0 5px;
        }}
    """
