"""Content update orchestration — check, download, validate, stage, finalize.

The update flow has two phases:
  1. Worker thread: fetch manifest, download staged DB, validate it.
  2. Main thread (finalization): close old connection, replace content.db,
     reopen, rebind services, reconcile userstate, clear undo/redo.

Safety guarantees:
- Failed staging leaves prior content.db intact.
- Failed finalization restores the backup and reopens the prior connection.
- User state (userstate.db) is only modified during post-update reconciliation.
- Undo/redo history is cleared after a successful finalization.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import sqlite3
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QThread, Signal

from app.updater.validator import (
    ValidationError,
    validate_content_db,
    validate_client_compatibility,
    validate_checksum,
    validate_manifest_contract,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

DEFAULT_MANIFEST_URL = (
    "https://raw.githubusercontent.com/zackmeach/MSM_App/main/content/manifest.json"
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
    """Runs staging operations off the main thread."""

    check_finished = Signal(object)  # UpdateCheckResult
    staging_ready = Signal(str)  # new_version — staged DB validated and ready
    staging_failed = Signal(str)  # error message
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

            try:
                validate_manifest_contract(data)
                from app.ui.viewmodels import APP_VERSION

                validate_client_compatibility(data, APP_VERSION)
            except ValidationError as ve:
                self.check_finished.emit(
                    UpdateCheckResult(False, self._current_version, error=str(ve))
                )
                return

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

    def do_stage(self) -> None:
        """Download and validate the staged DB. Does NOT replace content.db."""
        if not self._manifest_data:
            self.staging_failed.emit("No manifest data")
            return

        db_url = self._manifest_data.get("content_db_url", "")
        if not db_url:
            self.staging_failed.emit("No download URL in manifest")
            return

        staging = self._data_dir / "content_staging.db"

        try:
            self.progress.emit("Downloading update...")
            req = urllib.request.Request(db_url, method="GET")
            req.add_header("User-Agent", "MSMAwakeningTracker/1.0")
            with urllib.request.urlopen(req, timeout=60) as resp:
                staging.write_bytes(resp.read())

            self.progress.emit("Validating...")

            from app.ui.viewmodels import APP_VERSION

            validate_client_compatibility(self._manifest_data, APP_VERSION)

            expected_sha = self._manifest_data.get("content_db_sha256", "")
            if expected_sha:
                validate_checksum(staging, expected_sha)

            validate_content_db(str(staging))

            new_version = self._manifest_data.get("content_version", "unknown")
            logger.info("Staged content DB validated: %s", new_version)
            self.staging_ready.emit(new_version)

        except (ValidationError, urllib.error.URLError, OSError) as exc:
            logger.error("Staging failed: %s", exc, exc_info=True)
            if staging.exists():
                staging.unlink(missing_ok=True)
            self.staging_failed.emit(str(exc))


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

    def rebind_content(self, conn_content: sqlite3.Connection) -> None:
        """Update the content connection after finalization."""
        self._conn_content = conn_content

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
        """Start the staging phase (download + validate) on a worker thread.

        When staging succeeds, ``staging_ready`` is emitted. The caller
        (MainWindow) is responsible for wiring that to the finalization path.
        """
        if not self._worker or (self._thread and self._thread.isRunning()):
            return

        self._thread = QThread()
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.do_stage)
        self._worker.staging_ready.connect(self._on_staging_ready)
        self._worker.staging_failed.connect(self._on_staging_failed)
        self._worker.progress.connect(self.status_message.emit)
        self._thread.start()

    # ── Finalization (called on main thread) ──────────────────────────

    def finalize_update(self, conn_content: sqlite3.Connection) -> sqlite3.Connection:
        """Replace content.db with staged DB and reopen.

        Closes *conn_content*, swaps the file, and returns a new connection.
        Raises on failure (caller must handle rollback).
        """
        staging = self._data_dir / "content_staging.db"
        current = self._data_dir / "content.db"
        backup = self._data_dir / "content_backup.db"

        self.status_message.emit("Applying update...")

        try:
            conn_content.close()
        except sqlite3.Error:
            pass

        _remove_wal_sidecars(current)

        if current.exists():
            shutil.copy2(current, backup)

        try:
            os.replace(str(staging), str(current))
        except OSError:
            shutil.move(str(staging), str(current))

        from app.bootstrap import open_content_db

        new_conn = open_content_db(current)
        return new_conn

    def rollback_update(self) -> sqlite3.Connection | None:
        """Restore backup and reopen the prior content connection.

        Returns the restored connection or None if backup is missing.
        """
        current = self._data_dir / "content.db"
        backup = self._data_dir / "content_backup.db"

        if not backup.exists():
            return None

        _remove_wal_sidecars(current)

        try:
            os.replace(str(backup), str(current))
        except OSError:
            shutil.move(str(backup), str(current))

        from app.bootstrap import open_content_db

        return open_content_db(current)

    def cleanup_staging_files(self) -> None:
        """Remove staging and backup files after a successful update."""
        for name in ("content_staging.db", "content_backup.db"):
            p = self._data_dir / name
            p.unlink(missing_ok=True)

    # ── Internal ──────────────────────────────────────────────────────

    def _on_check_finished(self, result: UpdateCheckResult) -> None:
        self._cleanup_thread()
        self.check_result.emit(result)

    def _on_staging_ready(self, new_version: str) -> None:
        self._cleanup_thread()
        self.apply_result.emit(UpdateApplyResult(True, new_version))

    def _on_staging_failed(self, error: str) -> None:
        self._cleanup_thread()
        self.status_message.emit("Update failed — your content is unchanged.")
        self.apply_result.emit(UpdateApplyResult(False, error=error))

    def _cleanup_thread(self) -> None:
        if self._thread:
            self._thread.quit()
            self._thread.wait(5000)
            self._thread = None


def _remove_wal_sidecars(db_path: Path) -> None:
    """Delete WAL and SHM sidecars for a SQLite DB so replacement is safe."""
    for suffix in ("-wal", "-shm"):
        sidecar = db_path.parent / (db_path.name + suffix)
        sidecar.unlink(missing_ok=True)
