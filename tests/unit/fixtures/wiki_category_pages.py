"""Committed, version-controlled fixtures for wgCategories element parsing.

These replace the previous reliance on the gitignored, non-reproducible
``pipeline/raw/cache/*.raw`` page dump. ``_parse_elements_from_categories``
only needs the page's RLCONF ``"wgCategories":[...]`` array, so each fixture
is a small synthetic HTML snippet that mirrors the real Fandom RLCONF blob
shape (verified against actual cached pages) while staying git-trackable and
fully deterministic.

Each fixture deliberately surrounds the real ``"<X> Element"`` categories
with realistic over-match trap noise:

  * adjacent ``"<X> Island"`` entries (e.g. ``"Cold Island"`` next to
    ``"Cold Element"``) — must NOT yield a phantom element,
  * a ``"Single/Double/Triple/Quad Element Monsters"`` count category —
    must NOT be captured as an element,
  * ``"Monsters"`` / ``"Natural Monsters"`` / ``"Magical Monsters"`` and
    other non-element categories that share substrings with elements.

The wiki category token for a schema element key is its human name plus
`` Element`` (mirrors ``_WIKI_ELEMENT_MAP`` in
``pipeline/raw/wiki_fetcher.py``): ``natural-cold`` -> ``"Cold Element"``,
``magical-light`` -> ``"Light Element"``, ``magical-bone`` ->
``"Bone Element"``, ``magical-faerie`` -> ``"Faerie Element"``,
``magical-psychic`` -> ``"Psychic Element"``, ``natural-fire`` ->
``"Fire Element"``, etc.
"""

from __future__ import annotations

# ── Ground truth element sets per monster (authoritative) ────────────
#
# Order-insensitive. Schema keys exactly as produced by
# ``_parse_elements_from_categories``.
EXPECTED_ELEMENTS: dict[str, set[str]] = {
    "Bulbo": {"natural-cold", "magical-light"},
    "Cybop": {"natural-air", "natural-earth"},
    "Dandidoo": {"natural-air", "natural-plant"},
    "Deedge": {"natural-air", "natural-plant", "natural-water", "natural-cold"},
    "Fiddlement": {"natural-cold", "natural-fire", "magical-light"},
    "Fwog": {"natural-earth", "natural-water"},
    "HippityHop": {"magical-faerie", "natural-earth"},
    "Mammott": {"natural-cold"},
    "Maw": {"natural-water", "natural-cold"},
    "Noggin": {"natural-earth"},
    "Oaktopus": {"natural-plant", "natural-water"},
    "PomPom": {"natural-air", "natural-earth", "natural-cold"},
    "Potbelly": {"natural-plant"},
    "Reedling": {"natural-air", "natural-plant", "natural-earth"},
    "Riff": {"natural-air", "natural-earth", "natural-water", "natural-cold"},
    "Sneyser": {"natural-air", "natural-water", "natural-cold", "natural-fire"},
    "Spunge": {"natural-air", "natural-plant", "natural-water"},
    "Spytrap": {"magical-light", "natural-plant", "natural-cold"},
    "Tapricorn": {"magical-psychic", "natural-plant", "natural-water"},
    "Tweedle": {"natural-air"},
    "Withur": {"natural-earth", "natural-water", "magical-bone"},
    "Wynq": {"natural-water", "natural-cold", "natural-fire"},
    "Yuggler": {"natural-fire", "magical-psychic"},
    "Ziggurab": {"natural-earth", "natural-cold", "natural-fire"},
}

# ── Schema key -> wiki category human name (mirrors _WIKI_ELEMENT_MAP) ─
_KEY_TO_WIKI_NAME: dict[str, str] = {
    "natural-plant": "Plant",
    "natural-cold": "Cold",
    "natural-air": "Air",
    "natural-water": "Water",
    "natural-earth": "Earth",
    "natural-fire": "Fire",
    "magical-bone": "Bone",
    "magical-faerie": "Faerie",
    "magical-light": "Light",
    "magical-psychic": "Psychic",
}

# Number word for the "<word> Element Monsters" count-category trap.
_COUNT_WORD = {1: "Single", 2: "Double", 3: "Triple", 4: "Quad"}


def _build_categories(monster: str, element_keys: set[str]) -> list[str]:
    """Build a realistic ``wgCategories`` list for one monster.

    Interleaves the genuine ``"<X> Element"`` categories with the
    over-match traps the parser must reject:

      * an ``"<X> Island"`` adjacent to every ``"<X> Element"``,
      * the ``"<word> Element Monsters"`` count category,
      * generic ``"Monsters"`` / ``"Natural Monsters"`` /
        ``"Magical Monsters"`` and other non-element noise.
    """
    element_names = [_KEY_TO_WIKI_NAME[k] for k in sorted(element_keys)]
    is_magical = any(k.startswith("magical-") for k in element_keys)

    cats: list[str] = ["Monsters"]
    cats.append("Magical Monsters" if is_magical else "Natural Monsters")
    # Count-category trap: e.g. "Triple Element Monsters".
    cats.append(f"{_COUNT_WORD[len(element_names)]} Element Monsters")

    for name in element_names:
        # Island trap sits directly next to the real Element category.
        cats.append(f"{name} Island")
        cats.append(f"{name} Element")

    # Additional realistic non-element trailing noise.
    cats += [
        "Gold Island",
        "Composer Island",
        "2x2 Sized Monsters",
        "Vocalist Monsters",
        "Monsters with costumes",
        f"{monster} Family",
    ]
    return cats


def _render_page(monster: str, categories: list[str]) -> str:
    """Render a minimal Fandom-shaped HTML page embedding RLCONF.

    The RLCONF JS blob and its ``"wgCategories"`` array match the real
    on-wiki structure (a flat JSON string array inside a ``<script>``
    that assigns ``window.RLCONF``), which is all
    ``_parse_elements_from_categories`` consumes.
    """
    cat_json = ",".join(f'"{c}"' for c in categories)
    return (
        "<!DOCTYPE html><html><head>"
        f"<title>{monster} | My Singing Monsters Wiki</title>"
        '<script>document.documentElement.className="client-js";'
        'RLCONF={"wgBreakFrames":false,'
        f'"wgPageName":"{monster}",'
        '"wgTitle":"' + monster + '",'
        f'"wgCategories":[{cat_json}],'
        '"wgPageContentLanguage":"en","wgIsArticle":true};'
        "</script></head>"
        f"<body><h1>{monster}</h1>"
        '<aside class="portable-infobox">'
        '<div data-source="element"></div></aside>'
        "</body></html>"
    )


# Synthetic page HTML keyed by monster name. Built deterministically from
# the authoritative ``EXPECTED_ELEMENTS`` map so the fixtures can never
# drift from the ground truth.
FIXTURE_PAGES: dict[str, str] = {
    monster: _render_page(monster, _build_categories(monster, keys))
    for monster, keys in EXPECTED_ELEMENTS.items()
}
