"""Shared config for the Active Monsters section cards.

Both `InWorkPanel` (home page) and `CatalogActivePanel` (catalog page right
rail) render the same three monster-type sections. Keeping the labels,
glyphs, island icons, and empty-state copy in one place ensures the two
pages stay in sync — divergence here is a UX bug.
"""

from __future__ import annotations

from typing import TypedDict


class SectionConfig(TypedDict):
    label: str
    icon: str
    island: str
    empty_text: str


TYPE_ORDER: list[str] = ["wublin", "celestial", "amber"]


TYPE_CONFIG: dict[str, SectionConfig] = {
    "wublin": {
        "label": "Wublins",
        "icon": "ϟ",
        "island": "wublin-island",
        "empty_text": "All Wublins still slumbering on their pedestals…",
    },
    "celestial": {
        "label": "Celestials",
        "icon": "✦",
        "island": "celestial-island",
        "empty_text": "The Celestial realm awaits its first spark…",
    },
    "amber": {
        "label": "Amber Vessels",
        "icon": "◈",
        "island": "amber-island",
        "empty_text": "No amber echoes stirring in the deep…",
    },
}
