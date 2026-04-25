"""Non-blocking audio playback for UI sound effects.

Uses ``QMediaPlayer + QAudioOutput`` so we can play both WAV (close.wav, ding.wav)
and OGG (click.ogg) without per-format fallbacks. Each effect is preloaded once
on construction; ``play_*`` methods restart playback from the start so rapid
successive clicks remain responsive.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

logger = logging.getLogger(__name__)


class AudioPlayer:
    """Plays short UI sound effects.

    Construct with the directory that contains the audio files. Effects are
    keyed internally by name; missing files are tolerated (logged at debug,
    play_* becomes a silent no-op).
    """

    def __init__(self, audio_dir: Path | None = None) -> None:
        self._players: dict[str, tuple[QMediaPlayer, QAudioOutput]] = {}
        if audio_dir is None:
            return

        self._load(audio_dir, "ding", "ding.wav", volume=0.8)
        self._load(audio_dir, "click", "click.ogg", volume=0.35)
        self._load(audio_dir, "closeout", "close.wav", volume=0.85)

    def _load(self, audio_dir: Path, key: str, filename: str, *, volume: float) -> None:
        path = audio_dir / filename
        if not path.exists():
            logger.debug("Audio file missing: %s", path)
            return
        try:
            output = QAudioOutput()
            output.setVolume(volume)
            player = QMediaPlayer()
            player.setAudioOutput(output)
            player.setSource(QUrl.fromLocalFile(str(path)))
            self._players[key] = (player, output)
        except Exception:
            logger.warning("Failed to load %s audio", key, exc_info=True)

    def _play(self, key: str) -> None:
        entry = self._players.get(key)
        if entry is None:
            return
        player, _ = entry
        try:
            # Rewind so a second click during playback restarts cleanly.
            player.stop()
            player.setPosition(0)
            player.play()
        except Exception:
            logger.warning("Failed to play %s", key, exc_info=True)

    def play_ding(self) -> None:
        self._play("ding")

    def play_click(self) -> None:
        self._play("click")

    def play_closeout(self) -> None:
        self._play("closeout")
