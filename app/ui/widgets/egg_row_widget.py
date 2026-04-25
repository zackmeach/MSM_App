"""Individual egg row in the Breed List."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QParallelAnimationGroup,
    QPropertyAnimation,
    QSequentialAnimationGroup,
    QSize,
    Signal,
    Qt,
)
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from app.ui.themes import scaled
from app.ui.widgets.consumer_card_row import ConsumerCardRow
from app.ui.widgets.element_pip_row import ElementPipRow

if TYPE_CHECKING:
    from app.services.audio_player import AudioPlayer
    from app.ui.viewmodels import BreedListRowViewModel


class EggRowWidget(QWidget):
    clicked = Signal(int)  # egg_type_id
    completion_finished = Signal(int)  # egg_type_id — fired after the close-out animation

    # -- Qt property for animating icon size ---------------------------------
    def _get_icon_size(self) -> int:
        return self._icon_size_value

    def _set_icon_size(self, v: int) -> None:
        self._icon_size_value = v
        self._icon_label.setFixedSize(QSize(v, v))

    iconSize = Property(int, _get_icon_size, _set_icon_size)

    # -- Qt property for animating widget height during close-out ------------
    def _get_row_height(self) -> int:
        return self._row_height_value

    def _set_row_height(self, v: int) -> None:
        self._row_height_value = v
        self.setMaximumHeight(v)
        self.setMinimumHeight(v)

    rowHeight = Property(int, _get_row_height, _set_row_height)

    def __init__(
        self,
        vm: BreedListRowViewModel,
        *,
        audio: "AudioPlayer | None" = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._egg_type_id = vm.egg_type_id
        self._is_completing = False
        self._prev_bred_count = 0
        self._audio = audio
        self._build_ui()
        self.update_data(vm)

    def _build_ui(self) -> None:
        self.setObjectName("eggRow")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumHeight(scaled(62))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Click to increment egg count")

        root = QHBoxLayout(self)
        root.setContentsMargins(10, 8, 14, 8)
        root.setSpacing(12)

        self._icon_label = QLabel()
        s = scaled(46)
        self._base_icon_size = s
        self._icon_size_value = s
        self._row_height_value = scaled(62)
        self._icon_label.setFixedSize(QSize(s, s))
        self._icon_label.setObjectName("eggIconContainer")
        self._icon_label.setScaledContents(True)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        root.addWidget(self._icon_label)

        center = QVBoxLayout()
        center.setSpacing(2)
        center.setContentsMargins(0, 2, 0, 2)

        self._name_label = QLabel()
        self._name_label.setObjectName("eggName")
        center.addWidget(self._name_label)

        # Time + element pips on a single sub-row.
        time_row = QHBoxLayout()
        time_row.setContentsMargins(0, 0, 0, 0)
        time_row.setSpacing(8)
        self._time_label = QLabel()
        self._time_label.setObjectName("eggTime")
        time_row.addWidget(self._time_label)
        self._element_row = ElementPipRow(())
        time_row.addWidget(self._element_row)
        time_row.addStretch()
        center.addLayout(time_row)

        root.addLayout(center, stretch=1)

        # Consumer monster cards: vertically centered between center column
        # and the progress/counter column ("to the left of the progress bar").
        self._consumer_row = ConsumerCardRow(())
        root.addWidget(self._consumer_row, alignment=Qt.AlignmentFlag.AlignVCenter)

        right = QVBoxLayout()
        right.setSpacing(4)
        right.setContentsMargins(0, 2, 0, 2)

        self._counter_label = QLabel()
        self._counter_label.setObjectName("eggCounter")
        self._counter_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        right.addWidget(self._counter_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setMinimumWidth(100)
        self._progress_bar.setTextVisible(False)
        right.addWidget(
            self._progress_bar, alignment=Qt.AlignmentFlag.AlignRight
        )

        root.addLayout(right)

    def update_data(self, vm: BreedListRowViewModel) -> None:
        self._egg_type_id = vm.egg_type_id
        self._name_label.setText(vm.name)
        self._time_label.setText(vm.breeding_time_display)
        self._counter_label.setText(f"{vm.bred_count} / {vm.total_needed}")
        self._progress_bar.setMaximum(vm.total_needed)
        self._progress_bar.setValue(vm.bred_count)
        self._element_row.set_elements(vm.elements)
        self._consumer_row.set_cards(vm.consumer_cards)

        if vm.bred_count > self._prev_bred_count and self._prev_bred_count > 0:
            self._flash_counter()
        self._prev_bred_count = vm.bred_count

        if vm.egg_image_path:
            pix = QPixmap(vm.egg_image_path)
            if not pix.isNull():
                self._icon_label.setPixmap(pix)
            else:
                self._icon_label.setText(vm.name[:2])
        else:
            self._icon_label.setText(vm.name[:2])

    def _pulse_icon(self) -> None:
        """Brief scale-down pulse on the egg icon to acknowledge a click."""
        base = self._base_icon_size
        anim = QPropertyAnimation(self, b"iconSize")
        anim.setDuration(200)
        anim.setKeyValueAt(0.0, base)
        anim.setKeyValueAt(0.4, int(base * 0.85))
        anim.setKeyValueAt(1.0, base)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()
        self._icon_pulse_anim = anim  # prevent GC

    def _flash_counter(self) -> None:
        """Brief opacity pulse on the counter label to acknowledge an increment."""
        effect = QGraphicsOpacityEffect(self._counter_label)
        self._counter_label.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(200)
        anim.setStartValue(0.3)
        anim.setEndValue(1.0)
        anim.finished.connect(lambda: self._counter_label.setGraphicsEffect(None))
        anim.start()
        self._counter_flash_anim = anim  # prevent GC

    def animate_completion(self) -> None:
        """Pop slightly larger, then collapse and fade — paired with closeout sound."""
        self._is_completing = True
        if self._audio is not None:
            self._audio.play_closeout()

        base_h = max(self.height(), self.sizeHint().height(), scaled(62))
        peak_h = int(base_h * 1.10)
        self._row_height_value = base_h

        # Phase 1: grow to peak (120ms, OutBack for tactile pop).
        grow = QPropertyAnimation(self, b"rowHeight")
        grow.setDuration(120)
        grow.setStartValue(base_h)
        grow.setEndValue(peak_h)
        grow.setEasingCurve(QEasingCurve.Type.OutBack)

        # Phase 2: collapse height + fade opacity in parallel (260ms).
        effect = QGraphicsOpacityEffect(self)
        effect.setOpacity(1.0)
        self.setGraphicsEffect(effect)

        collapse_h = QPropertyAnimation(self, b"rowHeight")
        collapse_h.setDuration(260)
        collapse_h.setStartValue(peak_h)
        collapse_h.setEndValue(0)
        collapse_h.setEasingCurve(QEasingCurve.Type.InCubic)

        fade = QPropertyAnimation(effect, b"opacity")
        fade.setDuration(260)
        fade.setStartValue(1.0)
        fade.setEndValue(0.0)
        fade.setEasingCurve(QEasingCurve.Type.InCubic)

        collapse = QParallelAnimationGroup()
        collapse.addAnimation(collapse_h)
        collapse.addAnimation(fade)

        sequence = QSequentialAnimationGroup()
        sequence.addAnimation(grow)
        sequence.addAnimation(collapse)
        sequence.finished.connect(self._on_fade_done)
        sequence.start()
        self._anim = sequence  # prevent GC

    def _on_fade_done(self) -> None:
        self.hide()
        self.completion_finished.emit(self._egg_type_id)

    @property
    def is_completing(self) -> bool:
        return self._is_completing

    def mousePressEvent(self, event) -> None:
        if not self._is_completing:
            self._pulse_icon()
            if self._audio is not None:
                self._audio.play_click()
            self.clicked.emit(self._egg_type_id)
        super().mousePressEvent(event)
