"""Tests for AudioPlayer — exposes ding/click/closeout API and tolerates missing files."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.audio_player import AudioPlayer


# ── These tests construct AudioPlayer which uses Qt multimedia.  Skip if
#    QApplication can't be created in this environment. ─────────────────

pytest.importorskip("PySide6.QtMultimedia")


@pytest.fixture(scope="module", autouse=True)
def _qapp():
    """Ensure a QApplication exists for QMediaPlayer construction."""
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


class TestAudioPlayerAPI:
    def test_no_audio_dir_constructs_silently(self):
        player = AudioPlayer(audio_dir=None)
        assert player._players == {}
        # All play methods are no-ops on missing files.
        player.play_ding()
        player.play_click()
        player.play_closeout()

    def test_missing_files_construct_silently(self, tmp_path: Path):
        player = AudioPlayer(audio_dir=tmp_path)
        assert player._players == {}
        player.play_click()  # no-op, no exception

    def test_loads_present_files(self):
        audio_dir = Path(__file__).resolve().parent.parent.parent / "resources" / "audio"
        if not audio_dir.exists():
            pytest.skip("resources/audio not bundled in this checkout")
        player = AudioPlayer(audio_dir=audio_dir)
        # All three sounds should be loaded if their files exist.
        for fname, key in [("ding.wav", "ding"), ("click.ogg", "click"), ("close.wav", "closeout")]:
            if (audio_dir / fname).exists():
                assert key in player._players, f"Expected {key} loaded from {fname}"

    def test_play_methods_exist(self):
        player = AudioPlayer(audio_dir=None)
        assert callable(player.play_ding)
        assert callable(player.play_click)
        assert callable(player.play_closeout)
