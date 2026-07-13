"""Pure-logic unit tests for sync.protocol (no Qt/VLC required)."""

from __future__ import annotations

import logging
import os
import sys

import pytest

# Make the src-layout package importable without an editable install.
_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from sync.protocol import (  # noqa: E402
    MessageType,
    SyncMessage,
    make,
    new_msg_id,
)

logger = logging.getLogger(__name__)


def test_messagetype_string_values() -> None:
    """MessageType is a str-Enum whose members equal their wire strings."""
    assert MessageType.JOIN == "join"
    assert MessageType.LEAVE == "leave"
    assert MessageType.PLAY == "play"
    assert MessageType.PAUSE == "pause"
    assert MessageType.STOP == "stop"
    assert MessageType.SEEK == "seek"
    assert MessageType.SYNC == "sync"
    assert MessageType.PING == "ping"
    assert MessageType.PEERS == "peers"
    assert MessageType.ERROR == "error"
    # str-Enum: value is the raw string.
    assert MessageType.PLAY.value == "play"


def test_messagetype_coercion_from_string() -> None:
    """A raw wire string coerces back into the correct MessageType."""
    assert MessageType("seek") is MessageType.SEEK
    assert MessageType("play") is MessageType.PLAY


def test_new_msg_id_is_unique_hex() -> None:
    """new_msg_id returns distinct 32-char hex strings."""
    a = new_msg_id()
    b = new_msg_id()
    assert isinstance(a, str)
    assert len(a) == 32
    assert all(c in "0123456789abcdef" for c in a)
    assert a != b


def test_make_sets_msg_id_and_timestamp() -> None:
    """make() stamps a fresh msg_id and a positive timestamp."""
    msg = make(MessageType.PLAY, room="lobby", sender="alice", position_ms=1234)
    assert msg.type is MessageType.PLAY
    assert msg.room == "lobby"
    assert msg.sender == "alice"
    assert msg.position_ms == 1234
    assert msg.rate == 1.0
    assert msg.msg_id
    assert len(msg.msg_id) == 32
    assert msg.timestamp > 0.0


def test_make_defaults() -> None:
    """make() applies documented defaults for optional arguments."""
    msg = make(MessageType.PING)
    assert msg.type is MessageType.PING
    assert msg.room == ""
    assert msg.sender == ""
    assert msg.position_ms == 0
    assert msg.rate == 1.0
    assert msg.msg_id
    assert msg.timestamp > 0.0


def test_make_generates_distinct_ids() -> None:
    """Two make() calls of the same type still get unique ids."""
    m1 = make(MessageType.SEEK, position_ms=10)
    m2 = make(MessageType.SEEK, position_ms=10)
    assert m1.msg_id != m2.msg_id


def test_to_dict_uses_string_type() -> None:
    """to_dict serialises the enum as its .value string."""
    msg = make(MessageType.SEEK, room="r1", sender="bob", position_ms=500)
    d = msg.to_dict()
    assert d["type"] == "seek"
    assert isinstance(d["type"], str)
    assert d["room"] == "r1"
    assert d["sender"] == "bob"
    assert d["position_ms"] == 500


def test_json_round_trip_preserves_fields() -> None:
    """to_json/from_json round-trips every field faithfully."""
    original = make(MessageType.PAUSE, room="movie-night", sender="carol", position_ms=9876)
    original.rate = 1.5
    original.extra = {"foo": "bar", "n": 3}

    raw = original.to_json()
    assert isinstance(raw, str)

    restored = SyncMessage.from_json(raw)
    assert restored.type is MessageType.PAUSE
    assert restored.room == original.room
    assert restored.sender == original.sender
    assert restored.position_ms == original.position_ms
    assert restored.rate == original.rate
    assert restored.msg_id == original.msg_id
    assert restored.timestamp == original.timestamp
    assert restored.extra == {"foo": "bar", "n": 3}


def test_dict_round_trip() -> None:
    """to_dict/from_dict is a faithful round-trip."""
    original = make(MessageType.PLAY, room="a", sender="b", position_ms=42)
    restored = SyncMessage.from_dict(original.to_dict())
    assert restored == original


def test_from_dict_tolerates_missing_keys() -> None:
    """from_dict fills defaults for every omitted key except 'type'."""
    msg = SyncMessage.from_dict({"type": "stop"})
    assert msg.type is MessageType.STOP
    assert msg.room == ""
    assert msg.sender == ""
    assert msg.position_ms == 0
    assert msg.rate == 1.0
    assert msg.msg_id == ""
    assert msg.timestamp == 0.0
    assert msg.extra == {}


def test_from_dict_ignores_unknown_keys() -> None:
    """from_dict does not raise on unexpected extra keys in the payload."""
    msg = SyncMessage.from_dict(
        {"type": "join", "room": "x", "totally_unknown": 99, "another": [1, 2]}
    )
    assert msg.type is MessageType.JOIN
    assert msg.room == "x"


def test_from_dict_bad_type_raises_value_error() -> None:
    """An unrecognised type value raises ValueError for callers to catch."""
    with pytest.raises(ValueError):
        SyncMessage.from_dict({"type": "not-a-real-type"})


def test_from_json_bad_type_raises_value_error() -> None:
    """from_json surfaces the same ValueError on an invalid type."""
    with pytest.raises(ValueError):
        SyncMessage.from_json('{"type": "bogus"}')


def test_direct_construction_defaults() -> None:
    """A bare SyncMessage(type=...) uses documented dataclass defaults."""
    msg = SyncMessage(type=MessageType.LEAVE)
    assert msg.room == ""
    assert msg.sender == ""
    assert msg.position_ms == 0
    assert msg.rate == 1.0
    assert msg.msg_id == ""
    assert msg.timestamp == 0.0
    assert msg.extra == {}
    # Independent extra dicts per instance (default_factory, not shared mutable).
    other = SyncMessage(type=MessageType.LEAVE)
    msg.extra["k"] = "v"
    assert other.extra == {}
