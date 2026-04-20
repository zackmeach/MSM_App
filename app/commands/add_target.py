"""AddTargetCommand — adds a monster to the In-Work panel."""

from __future__ import annotations

import logging
import sqlite3

from app.commands.base import Command
from app.db.connection import transaction
from app.domain.models import MonsterRequirement, TargetRequirementProgress
from app.repositories import monster_repo, target_repo

logger = logging.getLogger(__name__)


class AddTargetCommand(Command):
    def __init__(
        self,
        monster_id: int,
        conn_content: sqlite3.Connection,
        conn_userstate: sqlite3.Connection,
        requirements_cache: dict[int, list[MonsterRequirement]],
    ) -> None:
        self._monster_id = monster_id
        self._conn_content = conn_content
        self._conn_userstate = conn_userstate
        self._requirements_cache = requirements_cache
        self._inserted_target_id: int | None = None
        self._materialized_rows: list[TargetRequirementProgress] = []

    def execute(self) -> None:
        monster = monster_repo.fetch_monster_by_id(self._conn_content, self._monster_id)
        if monster is None or monster.is_deprecated:
            raise RuntimeError(f"Monster {self._monster_id} not found or deprecated")

        reqs = self._requirements_cache.get(self._monster_id, [])
        if not reqs:
            raise RuntimeError(f"Monster {self._monster_id} has no requirements")

        egg_types = monster_repo.fetch_egg_types_map(self._conn_content)
        egg_keys = {
            req.egg_type_id: egg_types[req.egg_type_id].content_key
            for req in reqs
            if req.egg_type_id in egg_types
        }

        with transaction(self._conn_userstate):
            self._inserted_target_id = target_repo.insert_target(
                self._conn_userstate,
                self._monster_id,
                monster.content_key,
            )
            target_repo.materialize_progress(
                self._conn_userstate,
                self._inserted_target_id,
                reqs,
                egg_keys=egg_keys,
            )

        logger.info("AddTarget: monster_id=%d target_id=%d", self._monster_id, self._inserted_target_id)

    def undo(self) -> None:
        if self._inserted_target_id is None:
            return
        with transaction(self._conn_userstate):
            target_repo.delete_progress_for_target(self._conn_userstate, self._inserted_target_id)
            target_repo.delete_target(self._conn_userstate, self._inserted_target_id)

        logger.info("Undo AddTarget: target_id=%d", self._inserted_target_id)
