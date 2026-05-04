"""Application service — command orchestration, state derivation, event dispatch."""

from __future__ import annotations

import logging
import sqlite3
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

from app.assets import resolver
from app.db.connection import transaction
from app.domain.models import SortOrder
from app.repositories import monster_repo, settings_repo, target_repo
from app.services import view_model_builder as vmb
from app.ui.viewmodels import (
    AppStateViewModel,
    MonsterCatalogItemViewModel,
    SettingsDataRowViewModel,
    SettingsViewModel,
)

if TYPE_CHECKING:
    from app.commands.base import Command

logger = logging.getLogger(__name__)


class AppService(QObject):
    state_changed = Signal(AppStateViewModel)
    completion_event = Signal(int)  # egg_type_id
    target_added = Signal(str)  # monster name
    error_occurred = Signal(str)

    def __init__(
        self,
        conn_content: sqlite3.Connection,
        conn_userstate: sqlite3.Connection,
    ) -> None:
        super().__init__()
        self._conn_content = conn_content
        self._conn_userstate = conn_userstate

        self._undo_stack: list[Command] = []
        self._redo_stack: list[Command] = []

        self._requirements_cache = monster_repo.fetch_all_requirements(conn_content)
        self._egg_types_map = monster_repo.fetch_egg_types_map(conn_content)

        self._sort_order = SortOrder(
            settings_repo.get(conn_userstate, "breed_list_sort_order", "time_desc")
        )

    # ── Command execution ────────────────────────────────────────────

    def execute_command(self, cmd: Command) -> bool:
        try:
            cmd.execute()
        except Exception as exc:
            logger.error("Command failed: %s", exc, exc_info=True)
            self.error_occurred.emit(str(exc))
            return False

        self._undo_stack.append(cmd)
        self._redo_stack.clear()

        was_completion = getattr(cmd, "was_completion", False)
        completed_egg = getattr(cmd, "completed_egg_type_id", None)
        if was_completion and completed_egg is not None:
            self.completion_event.emit(completed_egg)

        self._emit_state()
        return True

    def undo(self) -> None:
        if not self._undo_stack:
            return
        cmd = self._undo_stack.pop()
        try:
            cmd.undo()
        except Exception as exc:
            logger.error("Undo failed: %s", exc, exc_info=True)
            self._undo_stack.append(cmd)
            self.error_occurred.emit(str(exc))
            return
        self._redo_stack.append(cmd)
        self._emit_state()

    def redo(self) -> None:
        if not self._redo_stack:
            return
        cmd = self._redo_stack.pop()
        try:
            cmd.execute()
        except Exception as exc:
            logger.error("Redo failed: %s", exc, exc_info=True)
            self._redo_stack.append(cmd)
            self.error_occurred.emit(str(exc))
            return
        self._undo_stack.append(cmd)

        was_completion = getattr(cmd, "was_completion", False)
        completed_egg = getattr(cmd, "completed_egg_type_id", None)
        if was_completion and completed_egg is not None:
            self.completion_event.emit(completed_egg)

        self._emit_state()

    # ── Add / Close-out / Increment handlers ─────────────────────────

    def handle_add_target(self, monster_id: int) -> None:
        from app.commands.add_target import AddTargetCommand

        cmd = AddTargetCommand(
            monster_id=monster_id,
            conn_content=self._conn_content,
            conn_userstate=self._conn_userstate,
            requirements_cache=self._requirements_cache,
        )
        if not self.execute_command(cmd):
            return

        m = monster_repo.fetch_monster_by_id(self._conn_content, monster_id)
        if m is not None:
            self.target_added.emit(m.name)

    def handle_close_out(self, monster_id: int) -> None:
        from app.commands.close_out_target import CloseOutTargetCommand

        target = target_repo.fetch_newest_target_for_monster(
            self._conn_userstate, monster_id
        )
        if target is None:
            return
        cmd = CloseOutTargetCommand(
            active_target_id=target.id,
            conn_userstate=self._conn_userstate,
        )
        self.execute_command(cmd)

    def handle_increment_egg(self, egg_type_id: int) -> None:
        from app.commands.increment_egg import IncrementEggCommand

        cmd = IncrementEggCommand(
            egg_type_id=egg_type_id,
            conn_userstate=self._conn_userstate,
        )
        self.execute_command(cmd)

    def rebind_content(self, conn_content: sqlite3.Connection) -> None:
        """Swap the content DB connection and refresh all caches.

        Called after a successful content update replaces content.db on disk
        and reopens the connection.
        """
        self._conn_content = conn_content
        self._requirements_cache = monster_repo.fetch_all_requirements(conn_content)
        self._egg_types_map = monster_repo.fetch_egg_types_map(conn_content)

    def reconcile_after_content_update(self) -> None:
        """Reconcile user state against the (just-rebound) content DB.

        Walks every active target:
          - Drop targets whose monster_key no longer exists or is deprecated.
          - Re-link targets whose numeric monster_id changed but content_key still resolves.
          - Insert progress rows for newly-required eggs.
          - Clip satisfied_count to the new required quantity.
          - Update progress identity (egg_type_id + egg_key) when egg IDs shifted.
          - Delete progress rows for eggs no longer required.

        Must be called AFTER rebind_content() so the new requirements_cache and
        egg_types_map are in scope.
        """
        targets = target_repo.fetch_all_targets(self._conn_userstate)
        requirements_map = self._requirements_cache
        egg_keys_by_id = {egg.id: egg.content_key for egg in self._egg_types_map.values()}

        with self._conn_userstate:
            for target in targets:
                if not target.monster_key:
                    logger.warning(
                        "Dropping target %s during reconciliation — missing monster_key",
                        target.id,
                    )
                    target_repo.delete_progress_for_target(self._conn_userstate, target.id)
                    target_repo.delete_target(self._conn_userstate, target.id)
                    continue

                monster = monster_repo.fetch_monster_by_key(
                    self._conn_content, target.monster_key
                )
                if monster is None or monster.is_deprecated:
                    target_repo.delete_progress_for_target(self._conn_userstate, target.id)
                    target_repo.delete_target(self._conn_userstate, target.id)
                    continue

                if monster.id != target.monster_id:
                    target_repo.update_target_identity(
                        self._conn_userstate,
                        target.id,
                        monster.id,
                        monster.content_key,
                    )

                progress_rows = target_repo.fetch_progress_for_target(
                    self._conn_userstate, target.id
                )
                progress_by_key = {
                    row.egg_key: row for row in progress_rows if row.egg_key
                }
                progress_by_id = {
                    row.egg_type_id: row for row in progress_rows if not row.egg_key
                }

                required_keys: set[str] = set()
                for requirement in requirements_map.get(monster.id, []):
                    egg_key = egg_keys_by_id.get(requirement.egg_type_id, "")
                    if not egg_key:
                        continue
                    required_keys.add(egg_key)
                    existing = progress_by_key.get(egg_key)
                    if existing is None:
                        existing = progress_by_id.get(requirement.egg_type_id)

                    if existing is None:
                        target_repo.insert_progress_row(
                            self._conn_userstate,
                            target.id,
                            requirement.egg_type_id,
                            requirement.quantity,
                            egg_key=egg_key,
                        )
                        continue

                    satisfied_count = min(existing.satisfied_count, requirement.quantity)
                    target_repo.update_progress_identity(
                        self._conn_userstate,
                        target.id,
                        existing.egg_type_id,
                        requirement.egg_type_id,
                        requirement.quantity,
                        egg_key,
                    )
                    if satisfied_count != existing.satisfied_count:
                        target_repo.set_progress(
                            self._conn_userstate,
                            target.id,
                            requirement.egg_type_id,
                            satisfied_count,
                        )

                for row in progress_rows:
                    row_key = row.egg_key or egg_keys_by_id.get(row.egg_type_id, "")
                    if row_key not in required_keys:
                        self._conn_userstate.execute(
                            "DELETE FROM target_requirement_progress "
                            "WHERE active_target_id = ? AND egg_type_id = ?",
                            (target.id, row.egg_type_id),
                        )

    # ── UI preferences ───────────────────────────────────────────────

    def get_ui_pref(self, key: str, default: str = "") -> str:
        """Read a UI preference from userstate."""
        return settings_repo.get(self._conn_userstate, key, default)

    def set_ui_pref(self, key: str, value: str) -> None:
        """Persist a UI preference to userstate."""
        with transaction(self._conn_userstate):
            settings_repo.set_value(self._conn_userstate, key, value)

    def clear_undo_redo(self) -> None:
        """Clear undo/redo stacks (e.g. after a content update)."""
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._emit_state()

    def handle_sort_change(self, order_str: str) -> None:
        try:
            self._sort_order = SortOrder(order_str)
        except ValueError:
            return
        with transaction(self._conn_userstate):
            settings_repo.set_value(
                self._conn_userstate, "breed_list_sort_order", order_str
            )
        self._emit_state()

    # ── Catalog data ─────────────────────────────────────────────────

    def get_catalog_items(self) -> list[MonsterCatalogItemViewModel]:
        monsters = monster_repo.fetch_all_monsters(self._conn_content)
        # Build active-count lookup from current targets
        targets = target_repo.fetch_all_targets(self._conn_userstate)
        active_counts: dict[int, int] = {}
        for t in targets:
            active_counts[t.monster_id] = active_counts.get(t.monster_id, 0) + 1
        items = []
        for m in monsters:

            items.append(
                MonsterCatalogItemViewModel(
                    monster_id=m.id,
                    name=m.name,
                    monster_type=m.monster_type.value,
                    image_path=resolver.resolve(m.image_path),
                    is_placeholder=m.is_placeholder,
                    active_count=active_counts.get(m.id, 0),
                )
            )
        return items

    # ── Settings data ────────────────────────────────────────────────

    def get_settings_viewmodel(self) -> SettingsViewModel:
        from app.ui.themes import get_active_font_offset, get_active_theme, FONT_SIZE_OPTIONS

        meta = monster_repo.fetch_update_metadata(self._conn_content)

        current_offset = get_active_font_offset()
        font_label = "Default"
        for label, offset in FONT_SIZE_OPTIONS:
            if offset == current_offset:
                font_label = label
                break

        return SettingsViewModel(
            content_version=meta.get("content_version", "—"),
            schema_version=str(self._get_content_schema_version()),
            last_updated_display=meta.get("last_updated_utc", "—"),
            data_rows=self._build_settings_data_rows(),
            current_theme=get_active_theme(),
            current_font_size_label=font_label,
        )

    # ── State derivation ─────────────────────────────────────────────

    def get_app_state(self) -> AppStateViewModel:
        progress = target_repo.fetch_all_progress(self._conn_userstate)
        targets = target_repo.fetch_all_targets(self._conn_userstate)

        active_monster_ids = {t.monster_id for t in targets}
        consumer_cards = vmb.build_consumer_cards(
            self._conn_content, active_monster_ids, self._requirements_cache
        )

        bl_vms = vmb.build_breed_list_vms(
            progress, self._egg_types_map, self._sort_order, consumer_cards
        )

        grouped: dict[int, int] = {}
        for t in targets:
            grouped[t.monster_id] = grouped.get(t.monster_id, 0) + 1
        inwork = vmb.build_inwork_vms(self._conn_content, grouped)

        return AppStateViewModel(
            breed_list_rows=bl_vms,
            inwork_by_type=inwork,
            sort_order=self._sort_order.value,
            can_undo=bool(self._undo_stack),
            can_redo=bool(self._redo_stack),
        )

    def _get_content_schema_version(self) -> int:
        row = self._conn_content.execute(
            "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
        ).fetchone()
        return int(row[0]) if row else 0

    def _build_settings_data_rows(self) -> list[SettingsDataRowViewModel]:
        requirements_map = monster_repo.fetch_all_requirements(self._conn_content)
        monsters = monster_repo.fetch_all_monsters(self._conn_content)
        return vmb.build_settings_data_rows(monsters, requirements_map)

    def _emit_state(self) -> None:
        self.state_changed.emit(self.get_app_state())
