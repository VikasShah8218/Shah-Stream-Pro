"""Core enumerations describing player and connection lifecycle states."""

from enum import Enum, auto


class PlayerState(Enum):
    """High-level playback state exposed by the media controller."""

    IDLE = auto()
    PLAYING = auto()
    PAUSED = auto()
    STOPPED = auto()
    ENDED = auto()
    ERROR = auto()
    BUFFERING = auto()


class ConnectionState(Enum):
    """State of the sync WebSocket connection."""

    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    RECONNECTING = auto()
    ERROR = auto()
