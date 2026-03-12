"""IncrementEggCommand — allocates one egg click to the oldest unsatisfied target."""

from __future__ import annotations

import logging
import sqlite3

from app.commands.base import Command
from app.db.connection import transaction
from app.domain.breed_list import derive_breed_list
from app.repositories import target_repo

logger = logging.getLogger(__name__)


class IncrementEggCommand(Command):
    def __init__(
        self,
        egg_type_id: int,
        conn_userstate: sqlite3.Connection,
    ) -> None:
        self._egg_type_id = egg_type_id
        self._conn = conn_userstate

        self._allocated_target_id: int | None = None
        self._prior_satisfied: int | None = None
        self.was_completion: bool = False
        self.completed_egg_type_id: int | None = None

    def execute(self) -> None:
        rows = target_repo.fetch_progress_for_egg(self._conn, self._egg_type_id)

        eligible = [r for r in rows if r.satisfied_count < r.required_count]
        if not eligible:
            raise RuntimeError(f"No unsatisfied target for egg_type {self._egg_type_id}")

        chosen = eligible[0]
        self._allocated_target_id = chosen.active_target_id
        self._prior_satisfied = chosen.satisfied_count

        with transaction(self._conn):
            new_val = target_repo.increment_progress(
                self._conn, chosen.active_target_id, self._egg_type_id
            )

        agg_remaining = self._compute_aggregate_remaining()
        if agg_remaining == 0:
            self.was_completion = True
            self.completed_egg_type_id = self._egg_type_id

        logger.info(
            "Increment egg=%d target=%d %d->%d remaining=%d",
            self._egg_type_id, chosen.active_target_id,
            self._prior_satisfied, new_val, agg_remaining,
        )

    def undo(self) -> None:
        if self._allocated_target_id is None or self._prior_satisfied is None:
            return
        with transaction(self._conn):
            target_repo.set_progress(
                self._conn, self._allocated_target_id,
                self._egg_type_id, self._prior_satisfied,
            )
        self.was_completion = False
        self.completed_egg_type_id = None
        logger.info("Undo increment egg=%d target=%d", self._egg_type_id, self._allocated_target_id)

    def _compute_aggregate_remaining(self) -> int:
        rows = target_repo.fetch_progress_for_egg(self._conn, self._egg_type_id)
        return sum(r.required_count - r.satisfied_count for r in rows)
