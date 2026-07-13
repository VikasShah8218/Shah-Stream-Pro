"""Transport control bar: a dumb view that emits intent and reflects state."""

from __future__ import annotations

import logging

from PyQt6.QtCore import QSignalBlocker, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QWidget,
)

from config.constants import DEFAULT_RATE, DEFAULT_VOLUME, PLAYBACK_RATES
from ui import icons
from ui.seek_slider import SeekSlider
from utils.formatting import ms_to_hhmmss

logger = logging.getLogger(__name__)

# Icon tints: light on the flat controls, near-black on the gold play disc.
_ICON_COLOR = "#C9CDD4"
_PLAY_ICON_COLOR = "#0E0E12"

# Fixed control geometry keeps the bar tidy and the play disc a true circle.
_CTRL_SIZE = 34
_CTRL_ICON = 20
_PLAY_SIZE = 38
_PLAY_ICON = 18


def _format_rate(rate: float) -> str:
    """Render a playback rate as a compact label, e.g. ``1x`` or ``0.25x``."""
    return f"{rate:g}x"


class ControlBar(QWidget):
    """Horizontal strip of transport controls.

    The bar is a pure view: it emits *intent* signals when the user interacts
    and exposes ``set_*`` methods for the controller to push authoritative
    state back in. State setters block child signals so that reflecting state
    never feeds back as a new user intent, and the seek slider is never moved
    out from under the user while they are scrubbing.
    """

    playPauseClicked = pyqtSignal()
    stopClicked = pyqtSignal()
    seekRequested = pyqtSignal(int)
    volumeChanged = pyqtSignal(int)
    muteToggled = pyqtSignal()
    rateChanged = pyqtSignal(float)
    fullscreenToggled = pyqtSignal()
    openFileClicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("controlBar")

        # Pre-build the icons that get swapped as state changes.
        self._icon_play = icons.play_icon(_PLAY_ICON_COLOR)
        self._icon_pause = icons.pause_icon(_PLAY_ICON_COLOR)
        self._icon_volume = icons.volume_icon(_ICON_COLOR)
        self._icon_mute = icons.mute_icon(_ICON_COLOR)

        self._open_btn = self._make_button(
            icons.open_icon(_ICON_COLOR), "Open file", "controlButton"
        )
        self._play_btn = self._make_button(
            self._icon_play, "Play", "playButton", size=_PLAY_SIZE, icon_px=_PLAY_ICON
        )
        self._stop_btn = self._make_button(
            icons.stop_icon(_ICON_COLOR), "Stop", "controlButton"
        )

        self._seek = SeekSlider(self)
        self._seek.setObjectName("seekSlider")

        self._current_label = QLabel(ms_to_hhmmss(0), self)
        self._current_label.setObjectName("timeLabel")
        self._sep_label = QLabel("/", self)
        self._sep_label.setObjectName("timeSep")
        self._total_label = QLabel(ms_to_hhmmss(0), self)
        self._total_label.setObjectName("timeLabel")

        self._mute_btn = self._make_button(
            self._icon_volume, "Mute / Unmute", "controlButton"
        )

        self._volume = QSlider(Qt.Orientation.Horizontal, self)
        self._volume.setObjectName("volumeSlider")
        self._volume.setRange(0, 100)
        self._volume.setFixedWidth(96)
        with QSignalBlocker(self._volume):
            self._volume.setValue(DEFAULT_VOLUME)

        self._rate_combo = QComboBox(self)
        self._rate_combo.setObjectName("rateCombo")
        self._rate_combo.setFixedWidth(64)
        for rate in PLAYBACK_RATES:
            self._rate_combo.addItem(_format_rate(rate), float(rate))
        with QSignalBlocker(self._rate_combo):
            self._rate_combo.setCurrentIndex(self._index_for_rate(DEFAULT_RATE))

        self._fullscreen_btn = self._make_button(
            icons.fullscreen_icon(_ICON_COLOR), "Toggle fullscreen", "controlButton"
        )

        self._build_layout()
        self._connect_signals()
        logger.debug("ControlBar initialised")

    # ------------------------------------------------------------------ setup
    def _make_button(
        self,
        icon: QIcon,
        tooltip: str,
        object_name: str,
        size: int = _CTRL_SIZE,
        icon_px: int = _CTRL_ICON,
    ) -> QPushButton:
        button = QPushButton(self)
        button.setIcon(icon)
        button.setIconSize(QSize(icon_px, icon_px))
        button.setToolTip(tooltip)
        button.setObjectName(object_name)
        button.setFixedSize(size, size)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

    def _build_layout(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)
        layout.addWidget(self._open_btn)
        layout.addWidget(self._play_btn)
        layout.addWidget(self._stop_btn)
        layout.addSpacing(4)
        layout.addWidget(self._current_label)
        layout.addWidget(self._seek, stretch=1)
        layout.addWidget(self._sep_label)
        layout.addWidget(self._total_label)
        layout.addSpacing(4)
        layout.addWidget(self._mute_btn)
        layout.addWidget(self._volume)
        layout.addSpacing(2)
        layout.addWidget(self._rate_combo)
        layout.addWidget(self._fullscreen_btn)

    def _connect_signals(self) -> None:
        self._open_btn.clicked.connect(self.openFileClicked)
        self._play_btn.clicked.connect(self.playPauseClicked)
        self._stop_btn.clicked.connect(self.stopClicked)
        self._mute_btn.clicked.connect(self.muteToggled)
        self._fullscreen_btn.clicked.connect(self.fullscreenToggled)

        self._seek.seekRequested.connect(self.seekRequested)
        self._volume.valueChanged.connect(self.volumeChanged)
        self._rate_combo.currentIndexChanged.connect(self._on_rate_index_changed)

    # --------------------------------------------------------------- helpers
    def _index_for_rate(self, rate: float) -> int:
        """Return the combo index whose rate is closest to ``rate``."""
        best_idx = 0
        best_delta = float("inf")
        for idx in range(self._rate_combo.count()):
            value = self._rate_combo.itemData(idx)
            candidate = float(value) if value is not None else PLAYBACK_RATES[idx]
            delta = abs(candidate - rate)
            if delta < best_delta:
                best_delta = delta
                best_idx = idx
        return best_idx

    def _on_rate_index_changed(self, index: int) -> None:
        if index < 0:
            return
        data = self._rate_combo.itemData(index)
        if data is not None:
            rate = float(data)
        else:
            text = self._rate_combo.itemText(index).rstrip("xX").strip()
            try:
                rate = float(text)
            except ValueError:
                rate = PLAYBACK_RATES[index] if 0 <= index < len(PLAYBACK_RATES) else DEFAULT_RATE
        self.rateChanged.emit(rate)

    # ------------------------------------------------------------- state API
    def set_playing(self, playing: bool) -> None:
        """Reflect play/pause state by swapping the play button icon."""
        self._play_btn.setIcon(self._icon_pause if playing else self._icon_play)
        self._play_btn.setToolTip("Pause" if playing else "Play")

    def set_position(self, ms: int) -> None:
        """Update the current-time label and (unless scrubbing) the slider."""
        self._current_label.setText(ms_to_hhmmss(ms))
        if not self._seek.is_scrubbing():
            with QSignalBlocker(self._seek):
                self._seek.setValue(ms)

    def set_duration(self, ms: int) -> None:
        """Update the timeline range and the total-time label."""
        with QSignalBlocker(self._seek):
            self._seek.set_duration(ms)
        self._total_label.setText(ms_to_hhmmss(ms))

    def set_volume(self, v: int) -> None:
        """Reflect the current output volume on the volume slider."""
        with QSignalBlocker(self._volume):
            self._volume.setValue(max(0, min(100, v)))

    def set_muted(self, m: bool) -> None:
        """Reflect mute state by swapping the mute button icon."""
        self._mute_btn.setIcon(self._icon_mute if m else self._icon_volume)
        self._mute_btn.setToolTip("Unmute" if m else "Mute")

    def set_rate(self, r: float) -> None:
        """Select the combo entry matching the current playback rate."""
        with QSignalBlocker(self._rate_combo):
            self._rate_combo.setCurrentIndex(self._index_for_rate(r))
