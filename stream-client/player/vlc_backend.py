"""Pure libVLC wrapper with no Qt dependencies and no signals."""

from __future__ import annotations

import logging
import sys

import vlc

from models.media_info import TrackInfo

logger = logging.getLogger(__name__)


class VlcBackend:
    """Thin, framework-agnostic adapter over a single libVLC media player.

    This class deliberately avoids any Qt imports or signals; it exposes plain
    method calls and return values so it can be driven by the Qt-aware
    :class:`~player.media_controller.MediaController` (or tested in
    isolation).
    """

    def __init__(self) -> None:
        self._instance: vlc.Instance = vlc.Instance()
        self._player = self._instance.media_player_new()
        logger.debug("VlcBackend initialised: instance=%r player=%r", self._instance, self._player)

    # -- Video output surface ------------------------------------------------
    def set_window(self, handle: int) -> None:
        """Bind the player's video output to a native window handle."""
        if sys.platform.startswith("win"):
            self._player.set_hwnd(handle)
        elif sys.platform == "darwin":
            self._player.set_nsobject(handle)
        else:
            self._player.set_xwindow(handle)
        logger.debug("Attached video output to window handle %s on %s", handle, sys.platform)

    # -- Media loading -------------------------------------------------------
    def load(self, path: str) -> None:
        """Load a media file (or URL) into the player without starting it."""
        media = self._instance.media_new(path)
        self._player.set_media(media)
        logger.info("Loaded media: %s", path)

    # -- Transport -----------------------------------------------------------
    def play(self) -> None:
        """Start (or resume) playback."""
        self._player.play()

    def pause(self) -> None:
        """Toggle pause/resume (libVLC ``pause`` is a toggle)."""
        self._player.pause()

    def stop(self) -> None:
        """Stop playback and reset the player position."""
        self._player.stop()

    def set_pause(self, paused: bool) -> None:
        """Deterministically pause (``True``) or resume (``False``) playback."""
        self._player.set_pause(int(paused))

    def is_playing(self) -> bool:
        """Return ``True`` while media is actively playing."""
        return bool(self._player.is_playing())

    # -- Position / timing ---------------------------------------------------
    def get_time(self) -> int:
        """Return the current playback time in milliseconds (``-1`` if unknown)."""
        return int(self._player.get_time())

    def set_time(self, ms: int) -> None:
        """Seek to an absolute time in milliseconds."""
        self._player.set_time(int(ms))

    def get_length(self) -> int:
        """Return the total media length in milliseconds (``0``/``-1`` until known)."""
        return int(self._player.get_length())

    def get_position(self) -> float:
        """Return the current position as a fraction in ``[0.0, 1.0]``."""
        return float(self._player.get_position())

    def set_position(self, pos: float) -> None:
        """Seek to a fractional position in ``[0.0, 1.0]``."""
        self._player.set_position(float(pos))

    # -- Rate ----------------------------------------------------------------
    def set_rate(self, rate: float) -> None:
        """Set the playback rate multiplier (``1.0`` is normal speed)."""
        self._player.set_rate(float(rate))

    def get_rate(self) -> float:
        """Return the current playback rate multiplier."""
        return float(self._player.get_rate())

    # -- Volume / mute -------------------------------------------------------
    def set_volume(self, v: int) -> None:
        """Set the audio volume in the ``0..100`` range."""
        self._player.audio_set_volume(int(v))

    def get_volume(self) -> int:
        """Return the current audio volume."""
        return int(self._player.audio_get_volume())

    def set_mute(self, m: bool) -> None:
        """Mute (``True``) or unmute (``False``) audio output."""
        self._player.audio_set_mute(bool(m))

    def get_mute(self) -> bool:
        """Return ``True`` when audio output is muted."""
        return bool(self._player.audio_get_mute())

    # -- Audio tracks --------------------------------------------------------
    def get_audio_tracks(self) -> list[TrackInfo]:
        """Return the selectable audio tracks for the current media."""
        try:
            tracks: list[TrackInfo] = []
            for track_id, name in self._player.audio_get_track_description() or []:
                if track_id == -1:
                    continue
                decoded = name.decode("utf-8", "ignore") if isinstance(name, bytes) else str(name)
                tracks.append(TrackInfo(id=int(track_id), name=decoded))
            return tracks
        except Exception:  # noqa: BLE001 - libVLC can raise on unloaded media
            logger.exception("Failed to enumerate audio tracks")
            return []

    def set_audio_track(self, track_id: int) -> None:
        """Select the audio track with the given libVLC id."""
        self._player.audio_set_track(int(track_id))

    # -- Subtitle tracks -----------------------------------------------------
    def get_subtitle_tracks(self) -> list[TrackInfo]:
        """Return the selectable subtitle (SPU) tracks for the current media."""
        try:
            tracks: list[TrackInfo] = []
            for spu_id, name in self._player.video_get_spu_description() or []:
                if spu_id == -1:
                    continue
                decoded = name.decode("utf-8", "ignore") if isinstance(name, bytes) else str(name)
                tracks.append(TrackInfo(id=int(spu_id), name=decoded))
            return tracks
        except Exception:  # noqa: BLE001 - libVLC can raise on unloaded media
            logger.exception("Failed to enumerate subtitle tracks")
            return []

    def set_subtitle_track(self, spu_id: int) -> None:
        """Select the subtitle (SPU) track with the given libVLC id."""
        self._player.video_set_spu(int(spu_id))

    # -- Video ---------------------------------------------------------------
    def set_aspect_ratio(self, ratio: str) -> None:
        """Force an aspect ratio (e.g. ``"16:9"``); empty string clears it."""
        self._player.video_set_aspect_ratio(ratio.encode() if ratio else None)

    # -- State / lifecycle ---------------------------------------------------
    def get_state(self) -> "vlc.State":
        """Return the raw libVLC player state."""
        return self._player.get_state()

    def release(self) -> None:
        """Stop playback and release the underlying libVLC resources."""
        try:
            self._player.stop()
        except Exception:  # noqa: BLE001
            logger.exception("Error stopping player during release")
        try:
            self._player.release()
        except Exception:  # noqa: BLE001
            logger.exception("Error releasing player during release")
        try:
            self._instance.release()
        except Exception:  # noqa: BLE001
            logger.exception("Error releasing instance during release")
        logger.debug("VlcBackend released")
