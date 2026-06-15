"""Regression: SectionCard.refresh must not leave ghost rows in the paint tree.

Root cause of the rail "double-rendered / strikethrough text" artifact:
``refresh()`` called ``layout.removeWidget`` + ``deleteLater`` on the old
``MonsterEntryRow`` widgets. ``removeWidget`` only detaches from the layout —
the widget stays parented and visible at its last geometry until the deferred
``deleteLater`` destruction runs. Rapid refreshes (one per egg increment)
stacked stale rows under the new ones, so ``QWidget.grab()`` composited the
overlap. The fix detaches synchronously via ``setParent(None)``.
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from app.services.viewmodels import InWorkMonsterRowViewModel
from app.ui.widgets.section_card import SectionCard


@pytest.fixture(scope="module", autouse=True)
def _qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _vm(monster_id: int, name: str) -> InWorkMonsterRowViewModel:
    return InWorkMonsterRowViewModel(
        monster_id=monster_id,
        name=name,
        monster_type="wublin",
        image_path="",
        is_placeholder=True,
        count=1,
    )


def test_refresh_detaches_old_rows_synchronously(qtbot):
    card = SectionCard("Wublins", "W", "No active monsters", interactive=False)
    qtbot.addWidget(card)

    first = card.refresh([_vm(1, "Astropod"), _vm(2, "Blipsqueak")])
    assert all(e.parent() is not None for e in first)

    # Re-refresh BEFORE the event loop processes deferred deletes — this is
    # exactly the rapid-refresh scenario that produced ghost rows.
    card.refresh([_vm(3, "Brump")])

    for stale in first:
        assert stale.parent() is None, (
            "old MonsterEntryRow still parented after refresh — it remains "
            "visible until deleteLater runs and will ghost under new rows"
        )
        assert not stale.isVisible()
