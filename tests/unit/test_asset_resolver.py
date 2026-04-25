"""Tests for asset resolver — three-tier path resolution (cache > bundle > placeholder)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.assets import resolver


@pytest.fixture(autouse=True)
def _reset_resolver_state():
    """Reset module globals between tests so state doesn't leak."""
    resolver._BUNDLE_DIR = None
    resolver._CACHE_DIR = None
    resolver._PLACEHOLDER_PATH = None
    yield
    resolver._BUNDLE_DIR = None
    resolver._CACHE_DIR = None
    resolver._PLACEHOLDER_PATH = None


@pytest.fixture
def staged_dirs(tmp_path: Path):
    """Create cache + bundle dirs with a known asset in each."""
    bundle = tmp_path / "bundle"
    cache = tmp_path / "cache"
    (bundle / "images").mkdir(parents=True)
    (cache / "images").mkdir(parents=True)
    (bundle / "images" / "ui").mkdir()
    (bundle / "images" / "ui" / "placeholder.png").write_bytes(b"placeholder")
    return bundle, cache


class TestConfigure:
    def test_configure_sets_globals(self, tmp_path: Path):
        resolver.configure(bundle_dir=tmp_path / "b", cache_dir=tmp_path / "c")
        assert resolver._BUNDLE_DIR == tmp_path / "b"
        assert resolver._CACHE_DIR == tmp_path / "c"


class TestResolveCacheTier:
    def test_cache_takes_priority_over_bundle(self, staged_dirs):
        bundle, cache = staged_dirs
        (bundle / "images" / "egg.png").write_bytes(b"bundled")
        (cache / "images" / "egg.png").write_bytes(b"cached")
        resolver.configure(bundle_dir=bundle, cache_dir=cache)
        result = resolver.resolve("images/egg.png")
        assert result == str(cache / "images" / "egg.png")


class TestResolveBundleTier:
    def test_bundle_used_when_cache_missing(self, staged_dirs):
        bundle, cache = staged_dirs
        (bundle / "images" / "egg.png").write_bytes(b"bundled")
        resolver.configure(bundle_dir=bundle, cache_dir=cache)
        result = resolver.resolve("images/egg.png")
        assert result == str(bundle / "images" / "egg.png")


class TestResolvePlaceholderTier:
    def test_falls_back_to_placeholder_when_neither_exists(self, staged_dirs):
        bundle, cache = staged_dirs
        resolver.configure(bundle_dir=bundle, cache_dir=cache)
        result = resolver.resolve("images/missing.png")
        assert result == str(bundle / "images" / "ui" / "placeholder.png")

    def test_empty_path_returns_placeholder_immediately(self, staged_dirs):
        bundle, cache = staged_dirs
        resolver.configure(bundle_dir=bundle, cache_dir=cache)
        result = resolver.resolve("")
        assert result == str(bundle / "images" / "ui" / "placeholder.png")

    def test_returns_empty_string_when_no_placeholder_bundled(self, tmp_path: Path):
        bundle = tmp_path / "bundle_no_placeholder"
        bundle.mkdir()
        cache = tmp_path / "cache"
        cache.mkdir()
        resolver.configure(bundle_dir=bundle, cache_dir=cache)
        result = resolver.resolve("images/anything.png")
        assert result == ""


class TestResolveWithoutConfigure:
    def test_unconfigured_resolver_returns_empty_for_missing(self):
        result = resolver.resolve("images/anything.png")
        assert result == ""
