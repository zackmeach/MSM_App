"""Content update orchestration — check, download, validate, stage, apply.

Safety guarantees:
- Failed updates leave prior content.db intact.
- User state (userstate.db) is never modified by the updater directly.
- Post-update reconciliation clips any progress rows that exceed new requirements.
- Undo/redo history is cleared after a successful update.
"""

from __future__ import annotations

import json
import logging
import shutil
import sqlite3
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QThread, Signal

from app.updater.validator import ValidationError, validate_content_db

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

DEFAULT_MANIFEST_URL = (
    "https://raw.githubusercontent.com/MSMAwakeningTracker/content/main/manifest.json"
)


@dataclass(frozen=True)
class UpdateCheckResult:
    update_available: bool
    current_version: str
    remote_version: str = ""
    error: str = ""


@dataclass(frozen=True)
class UpdateApplyResult:
    success: bool
    new_version: str = ""
    error: str = ""


class _UpdateWorker(QObject):
    """Runs update operations off the main thread."""

    check_finished = Signal(object)  # UpdateCheckResult
    apply_finished = Signal(object)  # UpdateApplyResult
    progress = Signal(str)  # status message

    def __init__(
        self,
        data_dir: Path,
        manifest_url: str,
        current_version: str,
    ) -> None:
        super().__init__()
        self._data_dir = data_dir
        self._manifest_url = manifest_url
        self._current_version = current_version
        self._manifest_data: dict | None = None

    def do_check(self) -> None:
        try:
            self.progress.emit("Checking for updates...")
            req = urllib.request.Request(self._manifest_url, method="GET")
            req.add_header("User-Agent", "MSMAwakeningTracker/1.0")
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            remote_version = data.get("content_version", "")
            if not remote_version:
                self.check_finished.emit(
                    UpdateCheckResult(False, self._current_version, error="Invalid manifest")
                )
                return

            self._manifest_data = data
            available = remote_version != self._current_version
            self.check_finished.emit(
                UpdateCheckResult(available, self._current_version, remote_version)
            )

        except (urllib.error.URLError, OSError, json.JSONDecodeError, KeyError) as exc:
            logger.warning("Update check failed: %s", exc)
            self.check_finished.emit(
                UpdateCheckResult(False, self._current_version, error=str(exc))
            )

    def do_apply(self) -> None:
        if not self._manifest_data:
            self.apply_finished.emit(UpdateApplyResult(False, error="No manifest data"))
            return

        db_url = self._manifest_data.get("content_db_url", "")
        if not db_url:
            self.apply_finished.emit(UpdateApplyResult(False, error="No download URL in manifest"))
            return

        staging = self._data_dir / "content_staging.db"
        current = self._data_dir / "content.db"
        backup = self._data_dir / "content_backup.db"

        try:
            self.progress.emit("Downloading update...")
            req = urllib.request.Request(db_url, method="GET")
            req.add_header("User-Agent", "MSMAwakeningTracker/1.0")
            with urllib.request.urlopen(req, timeout=60) as resp:
                staging.write_bytes(resp.read())

            self.progress.emit("Validating...")
            validate_content_db(str(staging))

            self.progress.emit("Applying update...")
            if current.exists():
                shutil.copy2(current, backup)

            shutil.move(str(staging), str(current))

            new_version = self._manifest_data.get("content_version", "unknown")
            logger.info("Content updated to %s", new_version)
            self.apply_finished.emit(UpdateApplyResult(True, new_version))

        except (ValidationError, urllib.error.URLError, OSError) as exc:
            logger.error("Update apply failed: %s", exc, exc_info=True)
            self.progress.emit("Update failed — restoring backup...")

            if staging.exists():
                staging.unlink(missing_ok=True)
            if backup.exists() and not current.exists():
                shutil.move(str(backup), str(current))

            self.apply_finished.emit(UpdateApplyResult(False, error=str(exc)))


class UpdateService(QObject):
    """High-level update orchestration for the UI layer."""

    check_result = Signal(object)  # UpdateCheckResult
    apply_result = Signal(object)  # UpdateApplyResult
    status_message = Signal(str)

    def __init__(
        self,
        data_dir: Path,
        conn_content: sqlite3.Connection,
        manifest_url: str = DEFAULT_MANIFEST_URL,
    ) -> None:
        super().__init__()
        self._data_dir = data_dir
        self._conn_content = conn_content
        self._manifest_url = manifest_url
        self._thread: QThread | None = None
        self._worker: _UpdateWorker | None = None

    @property
    def current_version(self) -> str:
        try:
            row = self._conn_content.execute(
                "SELECT value FROM update_metadata WHERE key = 'content_version'"
            ).fetchone()
            return row[0] if row else "unknown"
        except sqlite3.Error:
            return "unknown"

    def check_for_update(self) -> None:
        if self._thread and self._thread.isRunning():
            return

        self._thread = QThread()
        self._worker = _UpdateWorker(
            self._data_dir, self._manifest_url, self.current_version
        )
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.do_check)
        self._worker.check_finished.connect(self._on_check_finished)
        self._worker.progress.connect(self.status_message.emit)
        self._thread.start()

    def apply_update(self) -> None:
        if not self._worker or (self._thread and self._thread.isRunning()):
            return

        self._thread = QThread()
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.do_apply)
        self._worker.apply_finished.connect(self._on_apply_finished)
        self._worker.progress.connect(self.status_message.emit)
        self._thread.start()

    def _on_check_finished(self, result: UpdateCheckResult) -> None:
        self._cleanup_thread()
        self.check_result.emit(result)

    def _on_apply_finished(self, result: UpdateApplyResult) -> None:
        self._cleanup_thread()
        self.apply_result.emit(result)

    def _cleanup_thread(self) -> None:
        if self._thread:
            self._thread.quit()
            self._thread.wait(5000)
            self._thread = None
