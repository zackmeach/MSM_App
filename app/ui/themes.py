"""Theme definitions and QSS stylesheet generator.

Each theme is a color dictionary.  ``build_stylesheet(theme, font_offset)``
produces the full QSS string that ``MainWindow.setStyleSheet()`` consumes.

Widgets that set inline styles for placeholder thumbnails should call
``placeholder_tones_3`` / ``placeholder_tones_2`` to get colors that
match the active theme.
"""

from __future__ import annotations

# ── Theme colour palettes ────────────────────────────────────────────

# Ink & Brass — refined dark default. Deep desaturated ink, brushed-brass
# accent (the single action colour: CTAs, active nav, in-progress bars).
_INK_AND_BRASS: dict[str, str] = {
    # surfaces
    "bg":              "#090d16",
    "bg_sunken":       "#060a12",
    "bg_low":          "#0f1420",
    "card":            "#131a27",
    "border":          "#1f2937",
    "interactive":     "#1a2333",
    "elevated":        "#243044",
    # accent
    "accent":          "#d8b15c",
    "accent_dark":     "#b8902f",
    "accent_hover_lt": "#e6c478",
    "accent_hover_dk": "#c89a3a",
    "accent_press_lt": "#c8a24a",
    "accent_press_dk": "#a07c1e",
    "accent_focus":    "#f0d28a",
    "cta_text":        "#1a1200",
    # text
    "text1":           "#e9e6df",
    "text2":           "#b3ab9c",
    "text3":           "#8b94a4",
    "text_muted":      "#8d96a3",
    "text_disabled":   "#3a4150",
    # semantic
    "success":         "#a6e3a1",
    "error":           "#ffb4ab",
    # decorative
    "gradient_center": "#111a2a",
    "dashed_border":   "#233244",
    "tip_border":      "#1f3043",
    "tip_bg_rgba":     "rgba(25, 33, 47, 0.85)",
    "icon_border":     "#2a3850",
    "card_hover_border": "#324056",
    "scroll_rgba":     "rgba(216, 177, 92, 51)",
    "scroll_hover_rgba": "rgba(216, 177, 92, 80)",
    "search_focus_rgba": "rgba(216, 177, 92, 0.4)",
    "thumb_fallback_bg": "#141d2e",
    "thumb_fallback_border": "#1f2c40",
    # font
    "font_family":     '"Bahnschrift", "Segoe UI", sans-serif',
}

# Umber Studio — warm dark. Brown-black surfaces, parchment text, muted
# ember/terracotta accent. Cozy, editorial counterpart to the cool default.
_UMBER_STUDIO: dict[str, str] = {
    # surfaces
    "bg":              "#15110d",
    "bg_sunken":       "#100c08",
    "bg_low":          "#1c1610",
    "card":            "#1f1814",
    "border":          "#322619",
    "interactive":     "#271e16",
    "elevated":        "#3a2c1f",
    # accent
    "accent":          "#cf7a4a",
    "accent_dark":     "#a85a30",
    "accent_hover_lt": "#e0925f",
    "accent_hover_dk": "#bd6a3a",
    "accent_press_lt": "#bd6c3e",
    "accent_press_dk": "#934d28",
    "accent_focus":    "#eda877",
    "cta_text":        "#1c0e04",
    # text
    "text1":           "#ece3d4",
    "text2":           "#c0b09a",
    "text3":           "#a8977f",
    "text_muted":      "#a89880",
    "text_disabled":   "#4a3f30",
    # semantic
    "success":         "#9bbf86",
    "error":           "#e8a08a",
    # decorative
    "gradient_center": "#1f1810",
    "dashed_border":   "#3a2c1c",
    "tip_border":      "#3a2c1c",
    "tip_bg_rgba":     "rgba(40, 30, 20, 0.85)",
    "icon_border":     "#4a3823",
    "card_hover_border": "#4a3826",
    "scroll_rgba":     "rgba(207, 122, 74, 51)",
    "scroll_hover_rgba": "rgba(207, 122, 74, 85)",
    "search_focus_rgba": "rgba(207, 122, 74, 0.4)",
    "thumb_fallback_bg": "#241b13",
    "thumb_fallback_border": "#3a2c1c",
    # font
    "font_family":     '"Bahnschrift", "Segoe UI", sans-serif',
}

# Daylight — light theme. Warm paper, white cards, deep-slate text, one
# confident deep-teal accent. Note: needs its own light placeholder tints
# below (the dark fallbacks would render as dark boxes on paper).
_DAYLIGHT: dict[str, str] = {
    # surfaces
    "bg":              "#f5f2ea",
    "bg_sunken":       "#ece7da",
    "bg_low":          "#efebe0",
    "card":            "#ffffff",
    "border":          "#e4ded0",
    "interactive":     "#eeeae0",
    "elevated":        "#e9e3d4",
    # accent
    "accent":          "#0f766e",
    "accent_dark":     "#0b5d56",
    "accent_hover_lt": "#138f85",
    "accent_hover_dk": "#0d6760",
    "accent_press_lt": "#0d645d",
    "accent_press_dk": "#094c46",
    "accent_focus":    "#14a89c",
    "cta_text":        "#ffffff",
    # text
    "text1":           "#232a32",
    "text2":           "#5b6470",
    "text3":           "#6c7480",
    "text_muted":      "#76808c",
    "text_disabled":   "#b8bcc2",
    # semantic
    "success":         "#3f9142",
    "error":           "#c0392b",
    # decorative
    "gradient_center": "#ece7da",
    "dashed_border":   "#cfc8b6",
    "tip_border":      "#d8d0bd",
    "tip_bg_rgba":     "rgba(255, 255, 255, 0.85)",
    "icon_border":     "#ddd6c4",
    "card_hover_border": "#cfc7b4",
    "scroll_rgba":     "rgba(35, 42, 50, 40)",
    "scroll_hover_rgba": "rgba(35, 42, 50, 70)",
    "search_focus_rgba": "rgba(15, 118, 110, 0.4)",
    "thumb_fallback_bg": "#eee9db",
    "thumb_fallback_border": "#ddd6c4",
    # font
    "font_family":     '"Segoe UI", "Inter", sans-serif',
}

THEMES: dict[str, dict[str, str]] = {
    "Ink & Brass": _INK_AND_BRASS,
    "Umber Studio": _UMBER_STUDIO,
    "Daylight": _DAYLIGHT,
}

THEME_NAMES: list[str] = list(THEMES.keys())

DEFAULT_THEME = "Ink & Brass"

# ── Per-type placeholder tones ───────────────────────────────────────

_PLACEHOLDER_3: dict[str, dict[str, tuple[str, str, str]]] = {
    "Ink & Brass": {
        "wublin":    ("#0e2228", "#1a4050", "#45e9d0"),
        "celestial": ("#2a2510", "#504010", "#ffba20"),
        "amber":     ("#2e201a", "#5a3525", "#ff8a65"),
    },
    "Umber Studio": {
        "wublin":    ("#13241f", "#2a4a40", "#4fd8c0"),
        "celestial": ("#2a2210", "#504010", "#ffba20"),
        "amber":     ("#2e1d14", "#5a3525", "#ff9568"),
    },
    "Daylight": {
        "wublin":    ("#d9efec", "#a9d6cf", "#0f766e"),
        "celestial": ("#f3ead2", "#d9c89a", "#9a7b1f"),
        "amber":     ("#f6e0d6", "#e0b29c", "#b65535"),
    },
}

_PLACEHOLDER_2: dict[str, dict[str, tuple[str, str]]] = {
    "Ink & Brass": {
        "wublin":    ("#0e2228", "#45e9d0"),
        "celestial": ("#2a2510", "#ffba20"),
        "amber":     ("#2e201a", "#ff8a65"),
    },
    "Umber Studio": {
        "wublin":    ("#13241f", "#4fd8c0"),
        "celestial": ("#2a2210", "#ffba20"),
        "amber":     ("#2e1d14", "#ff9568"),
    },
    "Daylight": {
        "wublin":    ("#e3f1ee", "#0f766e"),
        "celestial": ("#f4ecd8", "#9a7b1f"),
        "amber":     ("#f8e6dc", "#b65535"),
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

    # ── Radius scale (by element role, not one-size-fits-all) ──
    r_lg = "10px"   # cards, panels, large containers
    r_md = "8px"    # inputs, icon tiles, buttons, inner surfaces
    r_sm = "6px"    # chips, small utility controls

    # Per-type faint wash behind catalog thumbnails (reuses placeholder tones).
    _pt2 = _PLACEHOLDER_2.get(name, _PLACEHOLDER_2[DEFAULT_THEME])

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
            border-radius: {r_sm};
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
            border-radius: {r_sm};
            padding: 4px 12px;
            font-size: {sz(12)};
        }}

        /* ── Breed List: empty state ── */
        #emptyStateContainer {{
            background: qradialgradient(
                cx:0.5, cy:0.5, radius:0.7, fx:0.5, fy:0.5,
                stop:0 {t['gradient_center']}, stop:1 {t['bg_low']});
            border: none;
            border-radius: {r_lg};
        }}
        #emptyStateIcon {{
            background-color: {t['interactive']};
            border: 1px solid {t['icon_border']};
            border-radius: 40px;
            color: {t['accent']};
            font-size: {sz(28)};
        }}
        #emptyStateTitle {{
            font-size: {sz(22)};
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
            border-radius: {r_md};
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
            border-radius: {r_lg};
        }}
        #sectionIcon {{
            background-color: {t['elevated']};
            border-radius: {r_md};
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
            letter-spacing: 1px;
            /* trailing pad: Qt sizeHint omits letter-spacing */
            padding-right: 2px;
        }}
        #sectionBody {{
            background-color: {t['bg_sunken']};
            border: 1px solid {t['border']};
            border-radius: {r_lg};
            min-height: 96px;
        }}
        #sectionBody[populated="false"] {{
            border: 1px dashed {t['dashed_border']};
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
            border-radius: {r_lg};
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
            border-radius: {r_lg};
        }}
        #eggRow:hover {{
            background-color: {t['interactive']};
            border: 1px solid {t['card_hover_border']};
        }}
        #eggIconContainer {{
            background-color: {t['elevated']};
            border-radius: {r_md};
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
            border: 1px solid transparent;
            border-radius: {r_md};
        }}
        #inworkEntry:hover {{
            background-color: {t['interactive']};
            border: 1px solid {t['card_hover_border']};
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
            border-radius: {r_md};
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
            border-radius: {r_md};
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
            border-radius: {r_md};
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
            border-radius: {r_lg};
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
            background-color: transparent;
            border: 1px solid transparent;
            border-radius: {r_lg};
        }}
        #catalogCard:hover {{
            background-color: {t['card']};
            border: 1px solid {t['border']};
        }}
        #catalogCardImage {{
            background-color: {t['bg_sunken']};
            border-radius: {r_md};
        }}
        #catalogCardImage[mtype="wublin"] {{ background-color: {_pt2['wublin'][0]}; }}
        #catalogCardImage[mtype="celestial"] {{ background-color: {_pt2['celestial'][0]}; }}
        #catalogCardImage[mtype="amber"] {{ background-color: {_pt2['amber'][0]}; }}
        #catalogCardName {{
            font-size: {sz(14)};
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
            background-color: {t['bg_sunken']};
            border: none;
            border-radius: 4px;
            max-height: 8px;
            min-height: 8px;
        }}
        QProgressBar::chunk {{
            background-color: {t['accent']};
            border-radius: 4px;
        }}
        QProgressBar[complete="true"]::chunk {{
            background-color: {t['success']};
        }}

        /* ── Toast notification ── */
        #toast {{
            background-color: {t['elevated']};
            color: {t['text1']};
            border: 1px solid {t['accent']};
            border-radius: {r_md};
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
            border-radius: {r_lg};
        }}
        #settingsCardLow {{
            background-color: {t['bg_low']};
            border: 1px solid {t['border']};
            border-radius: {r_lg};
        }}
        #settingsCardIcon {{
            background-color: {t['elevated']};
            border-radius: {r_md};
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
            color: {t['text1']};
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
            border-radius: {r_lg};
        }}
        #settingsStatusBadge {{
            font-size: {sz(11)};
            font-weight: 700;
            letter-spacing: 1px;
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
            border-radius: {r_lg};
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
            border-radius: {r_md};
            color: {t['accent']};
            font-size: {sz(12)};
            font-weight: 700;
        }}

        /* ── MonsterCard (compact in-work cards) ── */
        #monsterCard {{
            background-color: {t['interactive']}; border-radius: {r_md};
        }}
        #monsterCard:hover {{ background-color: {t['elevated']}; }}
        #cardLabel {{ font-size: {sz(11)}; color: {t['text1']}; }}

        /* ── Catalog: active-count badge ── */
        #catalogBadge {{
            background-color: {t['accent']};
            color: {t['cta_text']};
            font-size: {sz(11)};
            font-weight: 700;
            border-radius: {(20 + offset) // 2}px;
            min-width: {20 + offset}px;
            max-height: {20 + offset}px;
            min-height: {20 + offset}px;
            padding: 0 5px;
        }}
    """
