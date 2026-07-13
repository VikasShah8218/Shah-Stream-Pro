"""Native video surface widget that libVLC renders into."""

from __future__ import annotations

import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QMouseEvent, QPalette
from PyQt6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


class VideoWidget(QWidget):
    """A native, black-filled surface whose window handle is handed to libVLC.

    The widget forces a native window (so ``winId`` yields a real OS handle that
    VLC can draw into) and emits :attr:`doubleClicked` so the main window can
    toggle fullscreen on a double-click.
    """

    doubleClicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # A real, native OS window is required for libVLC to attach its output.
        self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)

        # Paint the surface solid black so there is no flicker before playback.
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor("black"))
        self.setPalette(palette)

        self.setMinimumSize(320, 180)
        self.setMouseTracking(True)
        logger.debug("VideoWidget initialised")

    def window_handle(self) -> int:
        """Return the native window handle for this surface as an int."""
        return int(self.winId())

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """Emit :attr:`doubleClicked` on double-click (used for fullscreen)."""
        self.doubleClicked.emit()
        super().mouseDoubleClickEvent(event)
