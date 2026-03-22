"""Individual egg row in the Breed List."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import (
    QEvent,
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

if TYPE_CHECKING:
    from app.ui.viewmodels import BreedListRowViewModel


class EggRowWidget(QWidget):
    clicked = Signal(int)  # egg_type_id

    def __init__(self, vm: BreedListRowViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._egg_type_id = vm.egg_type_id
        self._is_completing = False
        self._build_ui()
        self.update_data(vm)

    def _build_ui(self) -> None:
        self.setObjectName("eggRow")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMinimumHeight(62)

        root = QHBoxLayout(self)
        root.setContentsMargins(10, 8, 14, 8)
        root.setSpacing(12)

        self._icon_label = QLabel()
        self._icon_label.setFixedSize(QSize(46, 46))
        self._icon_label.setObjectName("eggIconContainer")
        self._icon_label.setScaledContents(True)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self._icon_label.installEventFilter(self)
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
        self._progress_bar.setFixedWidth(100)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(6)
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

        if vm.egg_image_path:
            pix = QPixmap(vm.egg_image_path)
            if not pix.isNull():
                self._icon_label.setPixmap(pix)
            else:
                self._icon_label.setText(vm.name[:2])
        else:
            self._icon_label.setText(vm.name[:2])

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

    def eventFilter(self, obj, event) -> bool:
        if (
            obj is self._icon_label
            and event.type() == QEvent.Type.MouseButtonPress
            and not self._is_completing
        ):
            self.clicked.emit(self._egg_type_id)
            return True
        return super().eventFilter(obj, event)
