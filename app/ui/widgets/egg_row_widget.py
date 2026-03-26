"""Individual egg row in the Breed List."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import (
    QPropertyAnimation,
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

if TYPE_CHECKING:
    from app.ui.viewmodels import BreedListRowViewModel


class EggRowWidget(QWidget):
    clicked = Signal(int)  # egg_type_id

    def __init__(self, vm: BreedListRowViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._egg_type_id = vm.egg_type_id
        self._is_completing = False
        self._prev_bred_count = 0
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

        self._time_label = QLabel()
        self._time_label.setObjectName("eggTime")
        center.addWidget(self._time_label)

        root.addLayout(center, stretch=1)

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
        self._is_completing = True
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(300)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.finished.connect(self._on_fade_done)
        anim.start()
        self._anim = anim

    def _on_fade_done(self) -> None:
        self.hide()

    @property
    def is_completing(self) -> bool:
        return self._is_completing

    def mousePressEvent(self, event) -> None:
        if not self._is_completing:
            self.clicked.emit(self._egg_type_id)
        super().mousePressEvent(event)
