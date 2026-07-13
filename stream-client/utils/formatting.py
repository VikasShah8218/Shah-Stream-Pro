"""Formatting helpers for presenting playback values in the UI."""


def ms_to_hhmmss(ms: int) -> str:
    """Format a millisecond duration as ``H:MM:SS`` or ``MM:SS``.

    Negative or falsy values are rendered as ``"00:00"``. The hours component
    is only included when the duration is at least one hour.
    """
    if not ms or ms < 0:
        return "00:00"
    h = ms // 3_600_000
    m = (ms // 60_000) % 60
    s = (ms // 1_000) % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"
