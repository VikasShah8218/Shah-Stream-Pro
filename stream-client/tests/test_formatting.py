"""Pure-logic unit tests for utils.formatting (no Qt/VLC required)."""

from __future__ import annotations

import logging
import os
import sys

import pytest

# Make the src-layout package importable without an editable install.
_SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from utils.formatting import ms_to_hhmmss  # noqa: E402

logger = logging.getLogger(__name__)


def test_zero_returns_placeholder() -> None:
    """Falsy zero renders the mm:ss placeholder."""
    assert ms_to_hhmmss(0) == "00:00"


@pytest.mark.parametrize(
    ("ms", "expected"),
    [
        (1, "00:00"),        # rounds down toward the second
        (999, "00:00"),      # just under a second
        (1000, "00:01"),
        (5000, "00:05"),
        (45000, "00:45"),
        (59000, "00:59"),
        (59999, "00:59"),
    ],
)
def test_sub_minute(ms: int, expected: str) -> None:
    """Sub-minute values render as mm:ss with a zero minutes field."""
    assert ms_to_hhmmss(ms) == expected


@pytest.mark.parametrize(
    ("ms", "expected"),
    [
        (60000, "01:00"),
        (61000, "01:01"),
        (61500, "01:01"),
        (125000, "02:05"),
        (600000, "10:00"),
        (3599000, "59:59"),   # one second short of an hour
    ],
)
def test_minutes(ms: int, expected: str) -> None:
    """Values below one hour render as mm:ss (zero-padded, no hours field)."""
    assert ms_to_hhmmss(ms) == expected


@pytest.mark.parametrize(
    ("ms", "expected"),
    [
        (3600000, "1:00:00"),
        (3661000, "1:01:01"),
        (3723000, "1:02:03"),
        (36000000, "10:00:00"),
        (36061000, "10:01:01"),
    ],
)
def test_hours(ms: int, expected: str) -> None:
    """Values at or above one hour render as h:mm:ss (hours not zero-padded)."""
    assert ms_to_hhmmss(ms) == expected


@pytest.mark.parametrize("ms", [-1, -1000, -5000, -3600000])
def test_negative_returns_placeholder(ms: int) -> None:
    """Negative durations clamp to the mm:ss placeholder."""
    assert ms_to_hhmmss(ms) == "00:00"


def test_hours_format_uses_padded_minutes_and_seconds() -> None:
    """In h:mm:ss form the minutes and seconds stay zero-padded to two digits."""
    # 1h 2m 3s -> minutes/seconds padded, hour bare.
    assert ms_to_hhmmss(3600000 + 2 * 60000 + 3 * 1000) == "1:02:03"
