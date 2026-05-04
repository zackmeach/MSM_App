"""Tests for ElementPipRow, ConsumerCardRow, and MonsterEntryRow widgets."""

from __future__ import annotations

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from app.services.viewmodels import ConsumerCardViewModel
from app.ui.widgets.consumer_card_row import ConsumerCardRow
from app.ui.widgets.element_pip_row import ElementPipRow
from app.ui.widgets.monster_entry import MonsterEntryRow


@pytest.fixture(scope="module", autouse=True)
def _qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _card(monster_id: int, name: str, mtype: str = "wublin") -> ConsumerCardViewModel:
    return ConsumerCardViewModel(
        monster_id=monster_id,
        name=name,
        image_path="",
        monster_type=mtype,
        is_placeholder=True,
    )


class TestElementPipRow:
    def test_empty_elements_hides_widget(self, qtbot):
        w = ElementPipRow(())
        qtbot.addWidget(w)
        assert len(w._labels) == 0

    def test_renders_one_label_per_element(self, qtbot):
        w = ElementPipRow(("natural-cold", "natural-plant", "natural-air"))
        qtbot.addWidget(w)
        assert len(w._labels) == 3

    def test_set_elements_replaces_existing(self, qtbot):
        w = ElementPipRow(("natural-cold",))
        qtbot.addWidget(w)
        w.set_elements(("natural-plant", "natural-water"))
        assert len(w._labels) == 2

    def test_set_elements_to_empty_clears_labels(self, qtbot):
        w = ElementPipRow(("natural-cold", "natural-plant"))
        qtbot.addWidget(w)
        w.set_elements(())
        assert len(w._labels) == 0

    def test_tooltip_pretty_names_element(self, qtbot):
        w = ElementPipRow(("natural-cold",))
        qtbot.addWidget(w)
        assert w._labels[0].toolTip() == "Natural Cold"


class TestConsumerCardRow:
    def test_empty_cards_hides_widget(self, qtbot):
        w = ConsumerCardRow(())
        qtbot.addWidget(w)
        assert len(w._labels) == 0

    def test_renders_one_label_per_card(self, qtbot):
        cards = tuple(_card(i, f"Mon{i}") for i in range(3))
        w = ConsumerCardRow(cards)
        qtbot.addWidget(w)
        assert len(w._labels) == 3

    def test_caps_visible_at_six_with_overflow_chip(self, qtbot):
        cards = tuple(_card(i, f"Mon{i}") for i in range(10))
        w = ConsumerCardRow(cards)
        qtbot.addWidget(w)
        assert len(w._labels) == 7
        assert w._labels[-1].text() == "+4"

    def test_overflow_tooltip_lists_remaining_names(self, qtbot):
        cards = tuple(_card(i, f"Monster{i:02d}") for i in range(8))
        w = ConsumerCardRow(cards)
        qtbot.addWidget(w)
        chip = w._labels[-1]
        tooltip = chip.toolTip()
        assert "Monster06" in tooltip
        assert "Monster07" in tooltip

    def test_no_overflow_chip_at_exactly_six(self, qtbot):
        cards = tuple(_card(i, f"Mon{i}") for i in range(6))
        w = ConsumerCardRow(cards)
        qtbot.addWidget(w)
        assert len(w._labels) == 6
        for lbl in w._labels:
            assert not lbl.text().startswith("+")

    def test_card_tooltip_is_monster_name(self, qtbot):
        cards = (_card(1, "Tympa"),)
        w = ConsumerCardRow(cards)
        qtbot.addWidget(w)
        assert w._labels[0].toolTip() == "Tympa"

    def test_set_cards_replaces_existing(self, qtbot):
        w = ConsumerCardRow((_card(1, "A"), _card(2, "B")))
        qtbot.addWidget(w)
        w.set_cards((_card(3, "C"),))
        assert len(w._labels) == 1


def _press(widget) -> None:
    pos = QPointF(widget.rect().center())
    ev = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        pos,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(widget, ev)


class TestMonsterEntryRow:
    def test_press_pending_initialized_false(self, qtbot):
        row = MonsterEntryRow(1, "Mammott", "", monster_type="natural")
        qtbot.addWidget(row)
        assert row._press_pending is False

    def test_consecutive_clicks_both_emit(self, qtbot):
        """Regression: _press_pending must reset so a second click after the
        debounce window still fires (matters when handle_close_out hits its
        early-return path and no state_changed rebuilds the row)."""
        row = MonsterEntryRow(42, "Mammott", "", monster_type="natural")
        qtbot.addWidget(row)
        emitted: list[int] = []
        row.clicked.connect(emitted.append)

        _press(row)
        qtbot.wait(200)  # debounce window is 150ms
        assert emitted == [42]
        assert row._press_pending is False, "flag must reset after emit"

        _press(row)
        qtbot.wait(200)
        assert emitted == [42, 42]
