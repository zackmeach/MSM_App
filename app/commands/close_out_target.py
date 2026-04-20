"""CloseOutTargetCommand — removes one active target instance."""

from __future__ import annotations

import logging
import sqlite3

from app.commands.base import Command
from app.db.connection import transaction
from app.domain.models import TargetRequirementProgress
from app.repositories import target_repo

logger = logging.getLogger(__name__)


class CloseOutTargetCommand(Command):
    def __init__(
        self,
        active_target_id: int,
        conn_userstate: sqlite3.Connection,
    ) -> None:
        self._target_id = active_target_id
        self._conn = conn_userstate
        self._monster_id: int | None = None
        self._added_at: str | None = None
        self._monster_key: str = ""
        self._snapshot: list[TargetRequirementProgress] = []

    def execute(self) -> None:
        target = target_repo.fetch_target_by_id(self._conn, self._target_id)
        if target is None:
            raise RuntimeError(f"Active target {self._target_id} not found")

        self._monster_id = target.monster_id
        self._added_at = target.added_at
        self._monster_key = target.monster_key

        with transaction(self._conn):
            self._snapshot = target_repo.delete_progress_for_target(
                self._conn, self._target_id
            )
            target_repo.delete_target(self._conn, self._target_id)

        logger.info("CloseOut: target_id=%d monster_id=%d", self._target_id, self._monster_id)

    def undo(self) -> None:
        if self._monster_id is None or self._added_at is None:
            return
        with transaction(self._conn):
            target_repo.insert_target_with_id(
                self._conn,
                self._target_id,
                self._monster_id,
                self._added_at,
                self._monster_key,
            )
            target_repo.restore_progress_rows(self._conn, self._snapshot)

        logger.info("Undo CloseOut: target_id=%d restored", self._target_id)
