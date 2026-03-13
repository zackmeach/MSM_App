"""View-model dataclasses passed from AppService to UI widgets."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BreedListRowViewModel:
    egg_type_id: int
    name: str
    breeding_time_display: str
    egg_image_path: str
    bred_count: int
    total_needed: int
    remaining: int
    progress_fraction: float


@dataclass(frozen=True)
class InWorkMonsterRowViewModel:
    monster_id: int
    name: str
    monster_type: str
    image_path: str
    count: int
    display_name: str


@dataclass(frozen=True)
class MonsterCatalogItemViewModel:
    monster_id: int
    name: str
    monster_type: str
    image_path: str
    is_placeholder: bool


@dataclass(frozen=True)
class AppStateViewModel:
    breed_list_rows: list[BreedListRowViewModel] = field(default_factory=list)
    inwork_by_type: dict[str, list[InWorkMonsterRowViewModel]] = field(default_factory=dict)
    sort_order: str = "time_desc"
    can_undo: bool = False
    can_redo: bool = False


APP_VERSION = "1.0.0"


@dataclass(frozen=True)
class SettingsViewModel:
    content_version: str = ""
    last_updated_display: str = ""
    app_version: str = APP_VERSION
    disclaimer_text: str = (
        "This app is an unofficial fan creation and is not affiliated with, endorsed by, "
        "or sponsored by Big Blue Bubble Inc. All My Singing Monsters assets used in this "
        "app are sourced from the official Big Blue Bubble Fan Kit and are used in accordance "
        "with the BBB Fan Content Policy. My Singing Monsters is a trademark of Big Blue Bubble Inc."
    )
