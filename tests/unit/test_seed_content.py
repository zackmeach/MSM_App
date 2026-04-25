"""Tests for content seed metadata behavior."""

from __future__ import annotations

from pipeline.version import load_content_version


def test_version_file_present_and_nonempty():
    v = load_content_version()
    assert v
    assert v != "0.0.0-dev", "Production seed should have a real version"


def test_version_is_semver_shaped():
    v = load_content_version()
    parts = v.split(".")
    assert len(parts) >= 2, f"Expected dotted version, got {v!r}"
    int(parts[0])
    int(parts[1])
