"""MSM Fandom Wiki fetcher — extracts monster and egg data from wiki pages.

Fetches factual game data (monster names, types, egg requirements, breeding
times) from the My Singing Monsters Fandom Wiki. Stores all raw payloads
in the SourceCache for provenance tracking and deduplication.

This module handles parse failures defensively: unparseable pages produce
review items rather than crashes.

Image data is captured as metadata only — images are NOT downloaded.
See ``pipeline/SOURCE_POLICY.md`` for the full acquisition policy.
"""

from __future__ import annotations

import html
import logging
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from pipeline.raw.source_cache import CacheEntry, SourceCache

logger = logging.getLogger(__name__)

WIKI_BASE_URL = "https://mysingingmonsters.fandom.com"

# Fandom blocks non-browser User-Agents with HTTP 403.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
DEFAULT_REQUEST_DELAY = 1.0  # seconds between requests


@dataclass
class FetchResult:
    """Result of fetching data for a single monster or egg."""

    raw_payload: dict[str, Any] | None
    cache_entry: CacheEntry | None
    review_items: list[dict]
    source_reference: str


# ── Monster type classification ─────────────────────────────────────


# Known category page slugs on the wiki
CATEGORY_PAGES: dict[str, str] = {
    "wublin": "Category:Wublins",
    "celestial": "Category:Celestials",
    "amber": "Category:Amber_Island",
}

# Pages on category listings that are NOT monsters — used to filter noise.
_NON_MONSTER_PAGES: set[str] = {
    "Polarity", "Wublin Island", "Wublins",
    "Celestial Island", "Celestials", "Monster Names/Celestials",
    "Amber Island", "Islands", "Glowbes", "Vessels", "Zapping",
    "Colossals", "Island Skins", "Crucible", "Echoes of Eco",
    "Air Element", "Cold Element", "Earth Element", "Fire Element",
    "Plant Element", "Water Element",
}

# Prefixes that indicate Rare/Epic/Adult variants — skip these since
# the app tracks base monsters only.
_VARIANT_PREFIXES: tuple[str, ...] = ("Rare ", "Epic ", "Adult ")

# Monsters that should never appear in results (different mechanics).
EXCLUDED_MONSTERS: set[str] = {
    "Wubbox",  # Uses "boxing" mechanic — whole monsters, not eggs
}

# Monsters not in any standard category but that have wublin-inventory
# requirements.  Fetched individually by fetch_extra_monsters().
EXTRA_MONSTERS: dict[str, str] = {
    "Monculus": "wublin",  # Aux. Seasonal on Wublin Island
}

# Fallback classification if a monster's type can't be determined from
# which category page listed it.
KNOWN_MONSTER_TYPES: dict[str, str] = {
    # Wublins (base monsters on Wublin Island)
    "Zynth": "wublin", "Thwok": "wublin", "Dwumrohl": "wublin",
    "Zuuker": "wublin", "Tympa": "wublin", "Poewk": "wublin",
    "Brump": "wublin", "Gheegur": "wublin", "Creepuscule": "wublin",
    "Blipsqueak": "wublin", "Scargo": "wublin", "Astropod": "wublin",
    "Pixolotl": "wublin", "Bona-Petite": "wublin", "Dermit": "wublin",
    "Fleechwurm": "wublin", "Maulch": "wublin",
    "Screemu": "wublin", "Whajje": "wublin",
    "Monculus": "wublin",
    # Celestials (base monsters on Celestial Island)
    "Attmoz": "celestial", "Blasoom": "celestial", "Furnoss": "celestial",
    "Galvana": "celestial", "Glaishur": "celestial", "Hornacle": "celestial",
    "Loodvigg": "celestial", "Plixie": "celestial", "Scaratar": "celestial",
    "Syncopite": "celestial", "Torrt": "celestial", "Vhamp": "celestial",
    # Amber Island (Vessels — all 32 base monsters)
    "Barrb": "amber", "Bisonorus": "amber", "Boskus": "amber",
    "Bowhead": "amber", "Candelavra": "amber", "Drummidary": "amber",
    "Edamimi": "amber", "Floogull": "amber", "Flowah": "amber",
    "Flum Ox": "amber", "Glowl": "amber", "Gnarls": "amber",
    "Incisaur": "amber", "Kayna": "amber", "Krillby": "amber",
    "Phangler": "amber", "PongPing": "amber", "Repatillo": "amber",
    "Rootitoot": "amber", "Sneyser": "amber", "Sooza": "amber",
    "Stogg": "amber", "Thrumble": "amber", "Tiawa": "amber",
    "Tring": "amber", "Tuskski": "amber", "Viveine": "amber",
    "Whaddle": "amber", "Woolabee": "amber", "Wynq": "amber",
    "Yelmut": "amber", "Ziggurab": "amber",
}


# ── Breeding time lookup ────────────────────────────────────────────

# Authoritative breeding times for all known egg types.
# (seconds, display_string) — sourced from MSM Fandom Wiki.
KNOWN_BREEDING_TIMES: dict[str, tuple[int, str]] = {
    # ── Single-element (Natural Island starters) ──
    "Noggin":       (5,      "5s"),
    "Toe Jammer":   (60,     "1m"),
    "Mammott":      (120,    "2m"),
    "Potbelly":     (7200,   "2h"),
    "Tweedle":      (14400,  "4h"),
    # ── Two-element (Natural Islands — 30m tier) ──
    "Drumpler":     (1800,   "30m"),
    "Fwog":         (1800,   "30m"),
    "Maw":          (1800,   "30m"),
    # ── Two-element (Natural Islands — 8h tier) ──
    "Shrubb":       (28800,  "8h"),
    "Furcorn":      (28800,  "8h"),
    "Pango":        (28800,  "8h"),
    "Oaktopus":     (28800,  "8h"),
    # ── Three-element (Natural Islands — 8h tier) ──
    "Cybop":        (28800,  "8h"),
    "Quibble":      (28800,  "8h"),
    "Dandidoo":     (28800,  "8h"),
    "T-Rox":        (28800,  "8h"),
    # ── Three-element (Natural Islands — 12h tier) ──
    "Scups":        (43200,  "12h"),
    "Reedling":     (43200,  "12h"),
    "Pummel":       (43200,  "12h"),
    "Congle":       (43200,  "12h"),
    "Spunge":       (43200,  "12h"),
    "Clamble":      (43200,  "12h"),
    "PomPom":       (43200,  "12h"),
    "Bowgart":      (43200,  "12h"),
    "Thumpies":     (43200,  "12h"),
    # ── Four-element (Natural Islands) ──
    "Entbrat":      (86400,  "24h"),
    "Deedge":       (86400,  "24h"),
    "Shellbeat":    (86400,  "24h"),
    "Quarrister":   (86400,  "24h"),
    "Riff":         (86400,  "24h"),
    # ── Amber Island two-element ──
    "Kayna":        (25200,  "7h"),
    "Glowl":        (36000,  "10h"),
    "Flowah":       (36000,  "10h"),
    "Stogg":        (36000,  "10h"),
    "Phangler":     (36000,  "10h"),
    "Boskus":       (36000,  "10h"),
    # ── Amber Island three-element ──
    "Floogull":     (72000,  "20h"),
    "Barrb":        (72000,  "20h"),
    "Repatillo":    (72000,  "20h"),
    "Woolabee":     (72000,  "20h"),
    "Whaddle":      (72000,  "20h"),
    "Wynq":         (72000,  "20h"),
    "Sooza":        (72000,  "20h"),
    "Rootitoot":    (72000,  "20h"),
    "Thrumble":     (72000,  "20h"),
    "Ziggurab":     (72000,  "20h"),
    # ── Amber Island five-element ──
    "Tring":        (144000, "1d 16h"),
    "Sneyser":      (144000, "1d 16h"),
    # ── Fire / Magical two-element (9h) ──
    "Bonkers":      (32400,  "9h"),
    "Bulbo":        (32400,  "9h"),
    "Denchuhs":     (32400,  "9h"),
    "Gob":          (32400,  "9h"),
    "Hawlo":        (32400,  "9h"),
    "HippityHop":   (32400,  "9h"),
    "Peckidna":     (32400,  "9h"),
    "Pluckbill":    (32400,  "9h"),
    "Poppette":     (32400,  "9h"),
    "Squot":        (32400,  "9h"),
    "Wimmzies":     (32400,  "9h"),
    "Yuggler":      (32400,  "9h"),
    # ── Fire / Magical three-element (16h) ──
    "Banjaw":       (57600,  "16h"),
    "Bridg-it":     (57600,  "16h"),
    "Cantorell":    (57600,  "16h"),
    "Clavi Gnat":   (57600,  "16h"),
    "Fiddlement":   (57600,  "16h"),
    "Periscorp":    (57600,  "16h"),
    "Rooba":        (57600,  "16h"),
    "Spytrap":      (57600,  "16h"),
    "Tapricorn":    (57600,  "16h"),
    "TooToo":       (57600,  "16h"),
    "Uuduk":        (57600,  "16h"),
    "Withur":       (57600,  "16h"),
    # ── Fire / Magical four-element (1d 8h) ──
    "Blow't":       (115200, "1d 8h"),
    "Gloptic":      (115200, "1d 8h"),
    "Pladdie":      (115200, "1d 8h"),
    "Plinkajou":    (115200, "1d 8h"),
}


# ── Fetch primitives ────────────────────────────────────────────────


def _fetch_url(url: str, *, timeout: int = 30) -> bytes:
    """Fetch a URL and return raw bytes."""
    req = urllib.request.Request(url)
    req.add_header("User-Agent", USER_AGENT)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _make_review_item(
    issue_type: str,
    source_reference: str,
    notes: str,
    *,
    blocking: bool = False,
) -> dict:
    return {
        "issue_type": issue_type,
        "severity": "error" if blocking else "warning",
        "source_reference": source_reference,
        "blocking": blocking,
        "notes": notes,
    }


# ── Page parsing ────────────────────────────────────────────────────


def _extract_text(html_content: str) -> str:
    """Strip HTML tags and decode entities."""
    text = re.sub(r"<[^>]+>", "", html_content)
    return html.unescape(text).strip()


def _parse_infobox_field(page_html: str, field_name: str) -> str | None:
    """Extract raw HTML content of a wiki infobox field by data-source name."""
    pattern = rf'data-source="{re.escape(field_name)}"[^>]*>.*?<div[^>]*class="pi-data-value[^"]*"[^>]*>(.*?)</div>'
    match = re.search(pattern, page_html, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def _parse_infobox_requirements(page_html: str) -> list[dict[str, Any]]:
    """Extract egg requirements from the 'wublin inventory' infobox field.

    The wiki stores requirements as a sequence of:
      <a ... title="MonsterName"><img alt="MonsterName-egg" ...></a>
      <span ...><b><sup>xN</sup></b></span>

    This parser extracts the monster/egg name from the link title and
    the quantity from the <sup>xN</sup> tag.
    """
    # Get the raw HTML of the wublin inventory field
    inventory_html = _parse_infobox_field(page_html, "wublin inventory")
    if not inventory_html:
        return []

    requirements: list[dict[str, Any]] = []

    # Pattern: title="EggName" followed (with intervening HTML) by <sup>xN</sup>
    pattern = re.compile(
        r'title="([^"]+)"[^>]*>'
        r'<img[^>]*alt="[^"]*-?egg[^"]*"'
        r'[\s\S]*?'
        r'<sup>x(\d+)</sup>',
        re.IGNORECASE,
    )
    for match in pattern.finditer(inventory_html):
        egg_name = html.unescape(match.group(1)).strip()
        quantity = int(match.group(2))

        if egg_name and quantity > 0:
            requirements.append({"egg_name": egg_name, "quantity": quantity})

    return requirements


def _parse_requirement_table(page_html: str) -> list[dict[str, Any]]:
    """Extract egg requirements — tries infobox first, falls back to table rows.

    The primary source is the 'wublin inventory' infobox field. If that
    is not present, falls back to scanning for <tr><td>...<td>N</td>
    table rows (for pages with a different layout).
    """
    # Primary: infobox-based extraction (works on live wiki)
    requirements = _parse_infobox_requirements(page_html)
    if requirements:
        return requirements

    # Fallback: table-row extraction (for alternate page layouts)
    table_pattern = re.compile(
        r'<tr[^>]*>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(\d+)</td>',
        re.IGNORECASE,
    )
    for match in table_pattern.finditer(page_html):
        egg_name = _extract_text(match.group(1)).strip()
        quantity_str = match.group(2).strip()

        if not egg_name or not quantity_str:
            continue

        # Filter out non-egg entries (headers, labels, etc.)
        if any(skip in egg_name.lower() for skip in ["total", "element", "island", "level"]):
            continue

        try:
            quantity = int(quantity_str)
            if quantity > 0:
                requirements.append({"egg_name": egg_name, "quantity": quantity})
        except ValueError:
            continue

    return requirements


def _parse_breeding_time(time_str: str | None) -> tuple[int, str]:
    """Parse a breeding time string like '8h' or '24h' into seconds and display.

    Returns (seconds, display_string).
    """
    if not time_str:
        return 0, ""

    time_str = time_str.strip().lower()
    total_seconds = 0
    parts = []

    hours_match = re.search(r"(\d+)\s*h", time_str)
    minutes_match = re.search(r"(\d+)\s*m", time_str)
    seconds_match = re.search(r"(\d+)\s*s", time_str)

    if hours_match:
        h = int(hours_match.group(1))
        total_seconds += h * 3600
        parts.append(f"{h}h")
    if minutes_match:
        m = int(minutes_match.group(1))
        total_seconds += m * 60
        parts.append(f"{m}m")
    if seconds_match:
        s = int(seconds_match.group(1))
        total_seconds += s
        parts.append(f"{s}s")

    # Try plain number as seconds
    if total_seconds == 0:
        try:
            total_seconds = int(time_str)
            parts = [f"{total_seconds}s"]
        except ValueError:
            pass

    return total_seconds, " ".join(parts)


# ── Public API ──────────────────────────────────────────────────────


def _is_base_monster(name: str) -> bool:
    """Return True if this is a base monster (not a variant or non-monster page)."""
    if name in _NON_MONSTER_PAGES:
        return False
    if name in EXCLUDED_MONSTERS:
        return False
    if any(name.startswith(prefix) for prefix in _VARIANT_PREFIXES):
        return False
    if name.startswith("Category:") or name.startswith("Template:"):
        return False
    return True


def fetch_monster_list(
    monster_type: str,
    cache: SourceCache,
    *,
    delay: float = DEFAULT_REQUEST_DELAY,
) -> list[FetchResult]:
    """Fetch the list of monsters for a given type from the wiki.

    Returns a list of FetchResults, one per monster found on the
    category page. Each result contains the raw payload (or None if
    the page couldn't be parsed) and any review items.
    """
    if monster_type not in CATEGORY_PAGES:
        return [FetchResult(
            raw_payload=None,
            cache_entry=None,
            review_items=[_make_review_item(
                "source_payload_incomplete",
                f"category/{monster_type}",
                f"Unknown monster type: {monster_type}",
                blocking=True,
            )],
            source_reference=f"category/{monster_type}",
        )]

    category_slug = CATEGORY_PAGES[monster_type]
    source_ref = f"wiki/{category_slug}"

    try:
        url = f"{WIKI_BASE_URL}/wiki/{category_slug}"
        raw_bytes = _fetch_url(url)
        entry = cache.store("fandom", source_ref, raw_bytes)
    except (urllib.error.URLError, OSError) as exc:
        return [FetchResult(
            raw_payload=None,
            cache_entry=None,
            review_items=[_make_review_item(
                "source_fetch_failed",
                source_ref,
                f"Failed to fetch category page: {exc}",
                blocking=True,
            )],
            source_reference=source_ref,
        )]

    page_text = raw_bytes.decode("utf-8", errors="replace")

    # Extract monster names from category page links
    monster_names = _extract_monster_names_from_category(page_text)
    if not monster_names:
        return [FetchResult(
            raw_payload=None,
            cache_entry=entry,
            review_items=[_make_review_item(
                "source_payload_incomplete",
                source_ref,
                "No monster names found on category page",
                blocking=True,
            )],
            source_reference=source_ref,
        )]

    results: list[FetchResult] = []
    for name in monster_names:
        if delay > 0:
            time.sleep(delay)
        result = fetch_monster_page(name, monster_type, cache)
        results.append(result)

    return results


def fetch_extra_monsters(
    cache: SourceCache,
    *,
    delay: float = DEFAULT_REQUEST_DELAY,
) -> list[FetchResult]:
    """Fetch monsters not listed in any standard category page.

    These are monsters like Monculus that have wublin-inventory
    requirements but don't appear in Category:Wublins.
    """
    results: list[FetchResult] = []
    for name, mtype in EXTRA_MONSTERS.items():
        if delay > 0:
            time.sleep(delay)
        result = fetch_monster_page(name, mtype, cache)
        results.append(result)
    return results


def _extract_monster_names_from_category(page_html: str) -> list[str]:
    """Extract base monster names from a wiki category page.

    Filters out:
    - Category/Template pages
    - Rare/Epic/Adult variants
    - Known non-monster pages (islands, elements, game features)
    - Excluded monsters (Wubbox, etc.)
    """
    names: list[str] = []
    # Category pages list members as links in the category content area
    pattern = re.compile(
        r'class="category-page__member-link"[^>]*title="([^"]+)"',
        re.IGNORECASE,
    )
    for match in pattern.finditer(page_html):
        title = html.unescape(match.group(1)).strip()
        if _is_base_monster(title):
            names.append(title)

    return sorted(set(names))


def fetch_monster_page(
    monster_name: str,
    monster_type: str,
    cache: SourceCache,
) -> FetchResult:
    """Fetch and parse a single monster's wiki page.

    Returns a FetchResult with the raw payload (suitable for passing
    to the normalizer) and any review items.
    """
    wiki_slug = monster_name.replace(" ", "_")
    source_ref = f"wiki/{wiki_slug}"

    try:
        url = f"{WIKI_BASE_URL}/wiki/{wiki_slug}"
        raw_bytes = _fetch_url(url)
        entry = cache.store("fandom", source_ref, raw_bytes)
    except (urllib.error.URLError, OSError) as exc:
        return FetchResult(
            raw_payload=None,
            cache_entry=None,
            review_items=[_make_review_item(
                "source_fetch_failed",
                source_ref,
                f"Failed to fetch page for '{monster_name}': {exc}",
                blocking=True,
            )],
            source_reference=source_ref,
        )

    page_html = raw_bytes.decode("utf-8", errors="replace")
    review_items: list[dict] = []

    # Parse requirements from the page (infobox first, table fallback)
    requirements = _parse_requirement_table(page_html)
    if not requirements:
        review_items.append(_make_review_item(
            "source_payload_incomplete",
            source_ref,
            f"No requirements found for '{monster_name}'",
            blocking=False,
        ))

    # Determine monster type — use provided type, fall back to known list
    resolved_type = monster_type
    if not resolved_type:
        resolved_type = KNOWN_MONSTER_TYPES.get(monster_name, "")
    if not resolved_type:
        review_items.append(_make_review_item(
            "source_payload_incomplete",
            source_ref,
            f"Cannot determine monster type for '{monster_name}'",
            blocking=True,
        ))

    # Build raw payload matching the normalizer's expected input format
    raw_payload: dict[str, Any] = {
        "name": monster_name,
        "monster_type": resolved_type,
        "wiki_slug": wiki_slug,
        "source_url": f"{WIKI_BASE_URL}/wiki/{wiki_slug}",
        "is_placeholder": True,
        "asset_source": "generated_placeholder",
        "requirements": requirements,
    }

    return FetchResult(
        raw_payload=raw_payload,
        cache_entry=entry,
        review_items=review_items,
        source_reference=source_ref,
    )


def fetch_egg_data_from_requirements(
    all_monster_results: list[FetchResult],
) -> list[dict[str, Any]]:
    """Extract unique egg types from fetched monster requirements.

    Builds egg payloads from the requirement data gathered across all
    monster pages. Looks up breeding times from KNOWN_BREEDING_TIMES.
    """
    seen_eggs: dict[str, dict[str, Any]] = {}

    for result in all_monster_results:
        if not result.raw_payload or "requirements" not in result.raw_payload:
            continue
        for req in result.raw_payload["requirements"]:
            egg_name = req.get("egg_name", "").strip()
            if egg_name and egg_name not in seen_eggs:
                bt_seconds, bt_display = KNOWN_BREEDING_TIMES.get(
                    egg_name, (0, ""),
                )
                seen_eggs[egg_name] = {
                    "name": egg_name,
                    "breeding_time_seconds": bt_seconds,
                    "breeding_time_display": bt_display,
                    "source_slug": egg_name,
                    "source_url": "",
                    "is_placeholder": True,
                    "asset_source": "generated_placeholder",
                }

    return list(seen_eggs.values())
