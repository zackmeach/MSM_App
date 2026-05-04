"""View-model dataclasses passed from AppService to UI widgets."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


@dataclass(frozen=True)
class ConsumerCardViewModel:
    """One active-target monster that consumes the egg in this row."""

    monster_id: int
    name: str
    image_path: str
    monster_type: str  # "wublin" | "celestial" | "amber" — drives ring color
    is_placeholder: bool = False


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
    elements: tuple[str, ...] = ()
    consumer_cards: tuple[ConsumerCardViewModel, ...] = ()


@dataclass(frozen=True)
class InWorkMonsterRowViewModel:
    monster_id: int
    name: str
    monster_type: str
    image_path: str
    is_placeholder: bool
    count: int
    display_name: str


@dataclass(frozen=True)
class MonsterCatalogItemViewModel:
    monster_id: int
    name: str
    monster_type: str
    image_path: str
    is_placeholder: bool
    active_count: int = 0


@dataclass(frozen=True)
class SettingsDataRowViewModel:
    monster_id: int
    monster_name: str
    monster_type: str
    monster_type_label: str
    image_path: str
    is_placeholder: bool
    eggs_required_display: str
    duration_display: str


@dataclass(frozen=True)
class AppStateViewModel:
    breed_list_rows: list[BreedListRowViewModel] = field(default_factory=list)
    inwork_by_type: dict[str, list[InWorkMonsterRowViewModel]] = field(default_factory=dict)
    sort_order: str = "time_desc"
    can_undo: bool = False
    can_redo: bool = False


APP_VERSION = "1.0.0"

BBB_DISCLAIMER = (
    "This app is an unofficial fan creation and is not affiliated with, endorsed by, "
    "or sponsored by Big Blue Bubble Inc. All My Singing Monsters assets used in this "
    "app are sourced from the official Big Blue Bubble Fan Kit and are used in accordance "
    "with the BBB Fan Content Policy. My Singing Monsters is a trademark of Big Blue Bubble Inc."
)


class UpdateStatus(Enum):
    """Discrete states for the content update workflow."""

    IDLE = "idle"
    CHECKING = "checking"
    UPDATE_AVAILABLE = "update_available"
    NO_UPDATE = "no_update"
    STAGING = "staging"
    FINALIZING = "finalizing"
    SUCCESS = "success"
    ERROR = "error"


_TONE_MAP: dict[UpdateStatus, str] = {
    UpdateStatus.IDLE: "neutral",
    UpdateStatus.CHECKING: "neutral",
    UpdateStatus.UPDATE_AVAILABLE: "accent",
    UpdateStatus.NO_UPDATE: "success",
    UpdateStatus.STAGING: "neutral",
    UpdateStatus.FINALIZING: "neutral",
    UpdateStatus.SUCCESS: "success",
    UpdateStatus.ERROR: "error",
}


@dataclass(frozen=True)
class SettingsUpdateState:
    """Declarative state object for the content-update card UI.

    Use the class-method factories (``idle``, ``checking``, ``available``, etc.)
    rather than constructing instances directly.
    """

    status: UpdateStatus = UpdateStatus.IDLE
    button_label: str = "Check for Updates"
    button_enabled: bool = True
    is_install_action: bool = False
    status_headline: str = "Ready to check"
    status_detail: str = ""
    remote_version: str = ""

    @property
    def tone(self) -> str:
        return _TONE_MAP.get(self.status, "neutral")

    @classmethod
    def idle(cls) -> SettingsUpdateState:
        return cls()

    @classmethod
    def checking(cls) -> SettingsUpdateState:
        return cls(
            status=UpdateStatus.CHECKING,
            button_label="Checking\u2026",
            button_enabled=False,
            status_headline="Checking for updates\u2026",
        )

    @classmethod
    def available(cls, remote_version: str) -> SettingsUpdateState:
        return cls(
            status=UpdateStatus.UPDATE_AVAILABLE,
            button_label=f"Install Update ({remote_version})",
            button_enabled=True,
            is_install_action=True,
            status_headline="Update available",
            status_detail=f"Version {remote_version} is ready to install.",
            remote_version=remote_version,
        )

    @classmethod
    def no_update(cls) -> SettingsUpdateState:
        return cls(
            status=UpdateStatus.NO_UPDATE,
            button_label="Check for Updates",
            button_enabled=True,
            status_headline="Content is up to date",
        )

    @classmethod
    def staging(cls, detail: str = "Downloading update\u2026") -> SettingsUpdateState:
        return cls(
            status=UpdateStatus.STAGING,
            button_label="Updating\u2026",
            button_enabled=False,
            status_headline=detail,
        )

    @classmethod
    def finalizing(cls) -> SettingsUpdateState:
        return cls(
            status=UpdateStatus.FINALIZING,
            button_label="Applying\u2026",
            button_enabled=False,
            status_headline="Applying update\u2026",
        )

    @classmethod
    def success(cls, version: str) -> SettingsUpdateState:
        return cls(
            status=UpdateStatus.SUCCESS,
            button_label="Check for Updates",
            button_enabled=True,
            status_headline=f"Updated to {version}",
            status_detail="Content database has been refreshed.",
        )

    @classmethod
    def error(cls, detail: str) -> SettingsUpdateState:
        return cls(
            status=UpdateStatus.ERROR,
            button_label="Retry",
            button_enabled=True,
            status_headline="Update failed",
            status_detail=detail,
        )


@dataclass(frozen=True)
class SettingsViewModel:
    content_version: str = ""
    schema_version: str = ""
    last_updated_display: str = ""
    app_version: str = APP_VERSION
    disclaimer_text: str = BBB_DISCLAIMER
    data_rows: list[SettingsDataRowViewModel] = field(default_factory=list)
    update_state: SettingsUpdateState = field(default_factory=SettingsUpdateState)
    current_theme: str = "Deep Island Night"
    current_font_size_label: str = "Default"
