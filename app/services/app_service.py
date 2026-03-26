"""Application service — command orchestration, state derivation, event dispatch."""

from __future__ import annotations

import logging
import sqlite3
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

from app.domain.breed_list import derive_breed_list
from app.domain.models import MonsterType, SortOrder
from app.repositories import monster_repo, settings_repo, target_repo
from app.ui.viewmodels import (
    AppStateViewModel,
    BreedListRowViewModel,
    InWorkMonsterRowViewModel,
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

    def execute_command(self, cmd: Command) -> None:
        try:
            cmd.execute()
        except Exception as exc:
            logger.error("Command failed: %s", exc, exc_info=True)
            self.error_occurred.emit(str(exc))
            return

        self._undo_stack.append(cmd)
        self._redo_stack.clear()

        was_completion = getattr(cmd, "was_completion", False)
        completed_egg = getattr(cmd, "completed_egg_type_id", None)
        if was_completion and completed_egg is not None:
            self.completion_event.emit(completed_egg)

        self._emit_state()

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
        self.execute_command(cmd)

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
            from app.assets import resolver
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
        breed_rows = derive_breed_list(progress, self._egg_types_map, self._sort_order)

        from app.assets import resolver
        bl_vms = [
            BreedListRowViewModel(
                egg_type_id=r.egg_type_id,
                name=r.name,
                breeding_time_display=r.breeding_time_display,
                egg_image_path=resolver.resolve(r.egg_image_path),
                bred_count=r.bred_count,
                total_needed=r.total_needed,
                remaining=r.remaining,
                progress_fraction=r.bred_count / r.total_needed if r.total_needed else 0,
            )
            for r in breed_rows
        ]

        inwork = self._derive_inwork()

        return AppStateViewModel(
            breed_list_rows=bl_vms,
            inwork_by_type=inwork,
            sort_order=self._sort_order.value,
            can_undo=bool(self._undo_stack),
            can_redo=bool(self._redo_stack),
        )

    def _derive_inwork(self) -> dict[str, list[InWorkMonsterRowViewModel]]:
        targets = target_repo.fetch_all_targets(self._conn_userstate)
        grouped: dict[int, int] = {}
        for t in targets:
            grouped[t.monster_id] = grouped.get(t.monster_id, 0) + 1

        from app.assets import resolver
        by_type: dict[str, list[InWorkMonsterRowViewModel]] = {}
        for mid, count in grouped.items():
            m = monster_repo.fetch_monster_by_id(self._conn_content, mid)
            if m is None:
                continue
            display = f"{m.name} \u00d7 {count}" if count > 1 else m.name
            vm = InWorkMonsterRowViewModel(
                monster_id=m.id,
                name=m.name,
                monster_type=m.monster_type.value,
                image_path=resolver.resolve(m.image_path),
                is_placeholder=m.is_placeholder,
                count=count,
                display_name=display,
            )
            by_type.setdefault(m.monster_type.value, []).append(vm)
        return by_type

    def _get_content_schema_version(self) -> int:
        row = self._conn_content.execute(
            "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
        ).fetchone()
        return int(row[0]) if row else 0

    def _build_settings_data_rows(self) -> list[SettingsDataRowViewModel]:
        from app.assets import resolver

        requirements_map = monster_repo.fetch_all_requirements(self._conn_content)
        monsters = monster_repo.fetch_all_monsters(self._conn_content)
        rows: list[SettingsDataRowViewModel] = []

        for monster in monsters:
            requirements = requirements_map.get(monster.id, [])
            eggs_required = sum(req.quantity for req in requirements)
            rows.append(
                SettingsDataRowViewModel(
                    monster_id=monster.id,
                    monster_name=monster.name,
                    monster_type=monster.monster_type.value,
                    monster_type_label=_TYPE_LABELS[monster.monster_type],
                    image_path=resolver.resolve(monster.image_path),
                    is_placeholder=monster.is_placeholder,
                    eggs_required_display=_format_egg_total(eggs_required),
                    duration_display=_DURATION_LABELS[monster.monster_type],
                )
            )

        return rows

    def _emit_state(self) -> None:
        self.state_changed.emit(self.get_app_state())


_TYPE_LABELS = {
    MonsterType.WUBLIN: "Wublin",
    MonsterType.CELESTIAL: "Celestial",
    MonsterType.AMBER: "Amber Vessel",
}

_DURATION_LABELS = {
    MonsterType.WUBLIN: "N/A",
    MonsterType.CELESTIAL: "Permanent",
    MonsterType.AMBER: "30 Days",
}


def _format_egg_total(total: int) -> str:
    unit = "Egg" if total == 1 else "Eggs"
    return f"{total} {unit}"
