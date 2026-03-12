"""Non-blocking audio playback for the completion ding."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QSoundEffect

logger = logging.getLogger(__name__)


class AudioPlayer:
    def __init__(self, ding_path: Path | None = None) -> None:
        self._effect: QSoundEffect | None = None
        if ding_path and ding_path.exists():
            try:
                self._effect = QSoundEffect()
                self._effect.setSource(QUrl.fromLocalFile(str(ding_path)))
                self._effect.setVolume(0.8)
            except Exception:
                logger.warning("Failed to load ding audio", exc_info=True)
                self._effect = None
        else:
            logger.debug("No ding audio file at %s", ding_path)

    def play_ding(self) -> None:
        if self._effect is not None:
            try:
                self._effect.play()
            except Exception:
                logger.warning("Failed to play ding", exc_info=True)
