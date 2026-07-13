"""Wire protocol for the watch-together sync feature (self-contained, no app deps)."""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """Kinds of messages exchanged over the room WebSocket protocol."""

    JOIN = "join"
    LEAVE = "leave"
    PLAY = "play"
    PAUSE = "pause"
    STOP = "stop"
    SEEK = "seek"
    SYNC = "sync"
    PING = "ping"
    PEERS = "peers"
    ERROR = "error"


@dataclass
class SyncMessage:
    """A single protocol message describing a room event or transport action."""

    type: MessageType
    room: str = ""
    sender: str = ""
    position_ms: int = 0
    rate: float = 1.0
    msg_id: str = ""
    timestamp: float = 0.0
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to a plain JSON-compatible dict (``type`` as its string value)."""
        return {
            "type": self.type.value,
            "room": self.room,
            "sender": self.sender,
            "position_ms": self.position_ms,
            "rate": self.rate,
            "msg_id": self.msg_id,
            "timestamp": self.timestamp,
            "extra": dict(self.extra) if self.extra else {},
        }

    def to_json(self) -> str:
        """Serialize to a JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, d: dict) -> "SyncMessage":
        """Build a message from a dict, tolerating missing keys.

        Raises ``ValueError`` if the ``type`` field is missing or unknown.
        """
        msg_type = MessageType(d.get("type"))
        extra = d.get("extra") or {}
        if not isinstance(extra, dict):
            extra = {}
        return cls(
            type=msg_type,
            room=d.get("room", "") or "",
            sender=d.get("sender", "") or "",
            position_ms=int(d.get("position_ms", 0) or 0),
            rate=float(d.get("rate", 1.0) or 1.0),
            msg_id=d.get("msg_id", "") or "",
            timestamp=float(d.get("timestamp", 0.0) or 0.0),
            extra=extra,
        )

    @classmethod
    def from_json(cls, raw: str) -> "SyncMessage":
        """Parse a message from a JSON string."""
        return cls.from_dict(json.loads(raw))


def new_msg_id() -> str:
    """Return a fresh unique message id."""
    return uuid.uuid4().hex


def make(
    type: MessageType,
    room: str = "",
    sender: str = "",
    position_ms: int = 0,
    rate: float = 1.0,
) -> SyncMessage:
    """Construct a :class:`SyncMessage` stamped with a new id and current time."""
    return SyncMessage(
        type=type,
        room=room,
        sender=sender,
        position_ms=position_ms,
        rate=rate,
        msg_id=new_msg_id(),
        timestamp=time.time(),
    )
