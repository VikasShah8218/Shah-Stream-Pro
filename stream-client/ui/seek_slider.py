"""Click-to-seek timeline slider expressed in milliseconds."""

from __future__ import annotations

import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QSlider, QStyle, QWidget

logger = logging.getLogger(__name__)


class SeekSlider(QSlider):
    """Horizontal timeline slider whose value is a position in milliseconds.

    A left-click anywhere on the groove seeks directly to that point (rather
    than stepping by a page), and releasing the handle after a drag re-emits the
    final position. :attr:`seekRequested` carries the target position in ms.
    """

    seekRequested = pyqtSignal(int)  # target position in milliseconds

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setRange(0, 0)
        # Emit the resting value once the user finishes dragging the handle.
        self.sliderReleased.connect(self._on_slider_released)

    def set_duration(self, ms: int) -> None:
        """Set the total duration (upper bound) of the timeline in ms."""
        self.setRange(0, max(0, ms))

    def is_scrubbing(self) -> bool:
        """Return True while the user is actively dragging the handle."""
        return self.isSliderDown()

    def _on_slider_released(self) -> None:
        self.seekRequested.emit(self.value())

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """Seek directly to the clicked position on a left-button press."""
        if event.button() == Qt.MouseButton.LeftButton and self.maximum() > self.minimum():
            x = int(event.position().x())
            value = QStyle.sliderValueFromPosition(
                self.minimum(), self.maximum(), x, self.width()
            )
            self.setValue(value)
            self.seekRequested.emit(value)
            event.accept()
            return
        super().mousePressEvent(event)
