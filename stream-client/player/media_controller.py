"""High-level media controller bridging libVLC playback to Qt signals and sync."""

from __future__ import annotations

import logging
import os

import vlc
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from config.constants import POSITION_POLL_INTERVAL_MS
from core.enums import PlayerState
from models.media_info import MediaInfo, TrackInfo
from player.vlc_backend import VlcBackend

logger = logging.getLogger(__name__)


class MediaController(QObject):
    """Qt-aware facade over :class:`VlcBackend`.

    Owns the playback backend plus a polling :class:`QTimer` that translates the
    stateless libVLC player into Qt signals. It is the only player-layer object
    the UI and sync layers interact with. Transport actions triggered locally
    are broadcast as sync messages via :attr:`syncActionRequested`, while inbound
    remote actions are applied through :meth:`apply_remote` with broadcasting
    suppressed to avoid feedback loops.
    """

    # -- Signals -------------------------------------------------------------
    positionChanged = pyqtSignal(int)       # current playback time in ms
    durationChanged = pyqtSignal(int)       # total media length in ms
    stateChanged = pyqtSignal(object)       # PlayerState
    mediaLoaded = pyqtSignal(object)        # MediaInfo
    volumeChanged = pyqtSignal(int)
    muteChanged = pyqtSignal(bool)
    rateChanged = pyqtSignal(float)
    errorOccurred = pyqtSignal(str)
    syncActionRequested = pyqtSignal(object)  # sync.protocol.SyncMessage to broadcast

    # -- vlc.State -> PlayerState mapping ------------------------------------
    _STATE_MAP: dict[vlc.State, PlayerState] = {
        vlc.State.Playing: PlayerState.PLAYING,
        vlc.State.Paused: PlayerState.PAUSED,
        vlc.State.Stopped: PlayerState.STOPPED,
        vlc.State.Ended: PlayerState.ENDED,
        vlc.State.Error: PlayerState.ERROR,
        vlc.State.Opening: PlayerState.BUFFERING,
        vlc.State.Buffering: PlayerState.BUFFERING,
        vlc.State.NothingSpecial: PlayerState.IDLE,
    }

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._backend = VlcBackend()
        self._timer = QTimer(self)
        self._timer.setInterval(POSITION_POLL_INTERVAL_MS)
        self._timer.timeout.connect(self._on_poll)

        self._duration: int = 0
        self._last_state: PlayerState | None = None
        self._seeking: bool = False
        self._has_media: bool = False
        logger.debug("MediaController initialised")

    # -- Video surface -------------------------------------------------------
    def attach_window(self, handle: int) -> None:
        """Bind libVLC video output to a native window handle."""
        self._backend.set_window(handle)

    # -- Loading -------------------------------------------------------------
    def open_file(self, path: str) -> None:
        """Load a media file, reset discovered duration, and start polling."""
        try:
            self._backend.load(path)
        except Exception as exc:  # noqa: BLE001 - surface any libVLC failure to UI
            logger.exception("Failed to open media: %s", path)
            self.errorOccurred.emit(f"Failed to open media: {exc}")
            return

        self._duration = 0
        self._has_media = True
        if not self._timer.isActive():
            self._timer.start()

        self.mediaLoaded.emit(MediaInfo(path=path, title=os.path.basename(path)))
        self._last_state = PlayerState.STOPPED
        self.stateChanged.emit(PlayerState.STOPPED)
        logger.info("Opened media: %s", path)

    # -- Transport -----------------------------------------------------------
    def play(self, broadcast: bool = True) -> None:
        """Start/resume playback, optionally broadcasting a PLAY sync message."""
        self._backend.play()
        if broadcast:
            self._emit_sync("PLAY", self.current_position_ms())

    def pause(self, broadcast: bool = True) -> None:
        """Pause playback deterministically, optionally broadcasting PAUSE."""
        self._backend.set_pause(True)
        if broadcast:
            self._emit_sync("PAUSE", self.current_position_ms())

    def stop(self, broadcast: bool = True) -> None:
        """Stop playback, optionally broadcasting a STOP sync message."""
        self._backend.stop()
        if broadcast:
            self._emit_sync("STOP", 0)

    def toggle_play_pause(self, broadcast: bool = True) -> None:
        """Toggle between playing and paused based on current backend state."""
        if self._backend.is_playing():
            self.pause(broadcast)
        else:
            self.play(broadcast)

    def seek(self, position_ms: int, broadcast: bool = True) -> None:
        """Seek to an absolute time in ms, optionally broadcasting SEEK."""
        position_ms = int(position_ms)
        self._seeking = True
        try:
            self._backend.set_time(position_ms)
        finally:
            self._seeking = False
        self.positionChanged.emit(position_ms)
        if broadcast:
            self._emit_sync("SEEK", position_ms)

    def seek_relative(self, delta_ms: int, broadcast: bool = True) -> None:
        """Seek by a signed delta, clamped to ``[0, duration]``."""
        target = self.current_position_ms() + int(delta_ms)
        target = max(0, target)
        if self._duration > 0:
            target = min(target, self._duration)
        self.seek(target, broadcast)

    # -- Rate / volume / mute (not synced) -----------------------------------
    def set_rate(self, rate: float) -> None:
        """Set the playback rate multiplier (not broadcast to peers)."""
        self._backend.set_rate(rate)
        self.rateChanged.emit(float(rate))

    def set_volume(self, v: int) -> None:
        """Set audio volume in ``0..100`` and notify listeners."""
        v = int(v)
        self._backend.set_volume(v)
        self.volumeChanged.emit(v)

    def toggle_mute(self) -> None:
        """Toggle audio mute and notify listeners of the new state."""
        muted = not self._backend.get_mute()
        self._backend.set_mute(muted)
        self.muteChanged.emit(muted)

    # -- Track / aspect selection --------------------------------------------
    def set_audio_track(self, track_id: int) -> None:
        """Select an audio track by libVLC id."""
        self._backend.set_audio_track(track_id)

    def set_subtitle_track(self, spu_id: int) -> None:
        """Select a subtitle (SPU) track by libVLC id."""
        self._backend.set_subtitle_track(spu_id)

    def set_aspect_ratio(self, ratio: str) -> None:
        """Force a video aspect ratio (empty string restores the default)."""
        self._backend.set_aspect_ratio(ratio)

    def audio_tracks(self) -> list[TrackInfo]:
        """Return the currently available audio tracks."""
        return self._backend.get_audio_tracks()

    def subtitle_tracks(self) -> list[TrackInfo]:
        """Return the currently available subtitle tracks."""
        return self._backend.get_subtitle_tracks()

    # -- Remote (sync) application -------------------------------------------
    def apply_remote(self, msg) -> None:
        """Apply an inbound :class:`SyncMessage` without re-broadcasting it."""
        if not self._has_media:
            logger.debug("Ignoring remote action %r: no media loaded", getattr(msg, "type", None))
            return

        from sync.protocol import MessageType

        mtype = msg.type
        if mtype == MessageType.PLAY:
            self.seek(msg.position_ms, False)
            self.play(False)
        elif mtype == MessageType.PAUSE:
            self.seek(msg.position_ms, False)
            self.pause(False)
        elif mtype == MessageType.SEEK:
            self.seek(msg.position_ms, False)
        elif mtype == MessageType.STOP:
            self.stop(False)
        else:
            logger.debug("Ignoring non-transport remote message: %s", mtype)

    # -- Queries -------------------------------------------------------------
    def current_position_ms(self) -> int:
        """Return the current playback time in ms (never negative)."""
        return max(0, self._backend.get_time())

    def duration_ms(self) -> int:
        """Return the last discovered media duration in ms."""
        return self._duration

    # -- Lifecycle -----------------------------------------------------------
    def release(self) -> None:
        """Stop polling and release the underlying backend resources."""
        if self._timer.isActive():
            self._timer.stop()
        self._backend.release()
        logger.debug("MediaController released")

    # -- Internal ------------------------------------------------------------
    def _emit_sync(self, mtype_name: str, position_ms: int) -> None:
        """Build and emit a sync message for a local transport action."""
        from sync.protocol import MessageType, make

        msg = make(MessageType[mtype_name], position_ms=int(position_ms))
        self.syncActionRequested.emit(msg)

    def _map_state(self, state: "vlc.State") -> PlayerState:
        """Translate a raw libVLC state into a :class:`PlayerState`."""
        return self._STATE_MAP.get(state, PlayerState.IDLE)

    def _on_poll(self) -> None:
        """Timer tick: emit position, duration, and state changes as they occur."""
        time_ms = self._backend.get_time()
        if time_ms >= 0 and not self._seeking:
            self.positionChanged.emit(time_ms)

        length = self._backend.get_length()
        if length > 0 and length != self._duration:
            self._duration = length
            self.durationChanged.emit(length)

        state = self._map_state(self._backend.get_state())
        if state != self._last_state:
            self._last_state = state
            self.stateChanged.emit(state)
