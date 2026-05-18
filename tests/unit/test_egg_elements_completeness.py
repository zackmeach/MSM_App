"""Regression test: every egg has complete, schema-valid element data.

Guards against the silent-ship failure mode where an egg is absent from
``egg_elements.json`` and simply renders with no element pips.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
SCHEMA = ROOT / "pipeline" / "schemas" / "egg_elements.schema.json"
EGGS = ROOT / "pipeline" / "normalized" / "eggs.json"
DATA = ROOT / "pipeline" / "normalized" / "egg_elements.json"

KNOWN_VALUES = {
    "egg:dandidoo": ["natural-plant", "natural-air"],
    "egg:phangler": ["natural-water", "natural-fire"],
    "egg:wimmzies": ["natural-fire", "magical-faerie"],
    "egg:noggin": ["natural-earth"],
    "egg:fwog": ["natural-water", "natural-earth"],
}


def _allowed_element_keys() -> set[str]:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    return set(
        schema["properties"]["elements"]["patternProperties"][
            "^egg:[a-z0-9-]+$"
        ]["items"]["enum"]
    )


def _elements_map() -> dict[str, list[str]]:
    return json.loads(DATA.read_text(encoding="utf-8")).get("elements", {})


def test_every_egg_has_non_empty_element_list():
    if not (EGGS.exists() and DATA.exists()):
        pytest.skip("eggs.json or egg_elements.json missing")
    eggs = json.loads(EGGS.read_text(encoding="utf-8"))
    elements_map = _elements_map()
    missing = [
        e["content_key"]
        for e in eggs
        if not e.get("is_deprecated", False)
        and (
            not elements_map.get(e["content_key"])
            or not isinstance(elements_map[e["content_key"]], list)
        )
    ]
    assert not missing, f"Eggs missing element data: {sorted(missing)}"


def test_every_element_key_is_in_schema_enum():
    if not (SCHEMA.exists() and DATA.exists()):
        pytest.skip("Schema or data file missing")
    allowed = _allowed_element_keys()
    unknown = sorted(
        f"{ck}:{el}"
        for ck, vals in _elements_map().items()
        for el in vals
        if el not in allowed
    )
    assert not unknown, f"Unknown element keys not in schema enum: {unknown}"


@pytest.mark.parametrize("content_key,expected", sorted(KNOWN_VALUES.items()))
def test_known_egg_element_values(content_key: str, expected: list[str]):
    if not DATA.exists():
        pytest.skip("egg_elements.json missing")
    got = _elements_map().get(content_key)
    assert got == expected, f"{content_key}: expected {expected}, got {got}"
