"""Individual egg row in the Breed List."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import (
    QPropertyAnimation,
    QSize,
    Signal,
)
from PySide6.QtGui import QCursor, QPixmap
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QProgressBar,
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
        self.setCursor(QCursor.pos().__class__(QCursor().shape()))
        self.setCursor(QCursor(QCursor().shape()))

    def _build_ui(self) -> None:
        self.setObjectName("eggRow")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)

        self._icon_label = QLabel()
        self._icon_label.setFixedSize(QSize(40, 40))
        self._icon_label.setScaledContents(True)
        layout.addWidget(self._icon_label)

        info_layout = QHBoxLayout()
        self._name_label = QLabel()
        self._name_label.setObjectName("eggName")
        info_layout.addWidget(self._name_label)

        self._time_label = QLabel()
        self._time_label.setObjectName("eggTime")
        info_layout.addWidget(self._time_label)

        info_layout.addStretch()

        self._counter_label = QLabel()
        self._counter_label.setObjectName("eggCounter")
        info_layout.addWidget(self._counter_label)

        layout.addLayout(info_layout, stretch=1)

        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedWidth(80)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(8)
        layout.addWidget(self._progress_bar)

        self.setStyleSheet("""
            #eggRow {
                background-color: #313244; border-radius: 8px;
            }
            #eggRow:hover { background-color: #45475a; }
            #eggName { font-weight: bold; font-size: 13px; }
            #eggTime { color: #a6adc8; font-size: 12px; }
            #eggCounter { font-size: 13px; color: #89b4fa; }
            QProgressBar { background-color: #45475a; border-radius: 4px; }
            QProgressBar::chunk { background-color: #a6e3a1; border-radius: 4px; }
        """)

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

    def mousePressEvent(self, event) -> None:
        if not self._is_completing:
            self.clicked.emit(self._egg_type_id)
        super().mousePressEvent(event)
