"""Reusable grouped section card (Wublins / Celestials / Amber Vessels)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.ui.themes import scaled
from app.ui.widgets.monster_entry import MonsterEntryRow

if TYPE_CHECKING:
    from app.ui.viewmodels import InWorkMonsterRowViewModel


class SectionCard(QWidget):
    """A single monster-type group with header, badge, body, and empty state."""

    def __init__(
        self,
        label: str,
        icon_text: str,
        empty_text: str,
        *,
        icon_image_path: str | None = None,
        interactive: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._interactive = interactive
        self.setObjectName("sectionCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._entries: list[MonsterEntryRow] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)

        header = QHBoxLayout()
        header.setSpacing(12)

        icon = QLabel()
        icon.setObjectName("sectionIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        s = scaled(44)
        icon.setFixedSize(s, s)
        icon.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        if icon_image_path:
            pix = QPixmap(icon_image_path)
            if not pix.isNull():
                # Inset by the QSS padding (~4px each side) for a nicer fit.
                inset = max(s - 12, 16)
                icon.setPixmap(
                    pix.scaled(
                        QSize(inset, inset),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            else:
                icon.setText(icon_text)
        else:
            icon.setText(icon_text)
        header.addWidget(icon)

        name = QLabel(label)
        name.setObjectName("sectionLabel")
        header.addWidget(name)

        header.addStretch()

        self._badge = QLabel("INACTIVE")
        self._badge.setObjectName("sectionBadge")
        header.addWidget(self._badge)

        layout.addLayout(header)

        self._body = QWidget()
        self._body.setObjectName("sectionBody")
        self._body.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(16, 0, 16, 0)
        self._body_layout.setSpacing(6)

        self._empty_label = QLabel(empty_text)
        self._empty_label.setObjectName("sectionEmptyText")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._body_layout.addWidget(self._empty_label)

        layout.addWidget(self._body)

    def refresh(
        self,
        monsters: list[InWorkMonsterRowViewModel],
        on_click=None,
    ) -> list[MonsterEntryRow]:
        for entry in self._entries:
            self._body_layout.removeWidget(entry)
            entry.deleteLater()
        self._entries.clear()

        has_entries = bool(monsters)
        self._empty_label.setVisible(not has_entries)
        self._badge.setText(
            f"{len(monsters)} ACTIVE" if has_entries else "INACTIVE"
        )

        for m in monsters:
            badge = f"\u00d7 {m.count}" if m.count > 1 else ""
            entry = MonsterEntryRow(
                m.monster_id,
                m.name,
                m.image_path,
                monster_type=m.monster_type,
                is_placeholder=m.is_placeholder,
                badge_text=badge,
                interactive=self._interactive,
            )
            if self._interactive and on_click is not None:
                entry.setToolTip("Click to close out")
                entry.clicked.connect(on_click)
            idx = self._body_layout.indexOf(self._empty_label)
            self._body_layout.insertWidget(idx, entry)
            self._entries.append(entry)

        return list(self._entries)
