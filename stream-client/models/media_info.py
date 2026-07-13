"""Dataclasses describing loaded media and its audio/subtitle tracks."""

from dataclasses import dataclass, field


@dataclass
class TrackInfo:
    """A single selectable audio or subtitle track."""

    id: int
    name: str
    language: str | None = None


@dataclass
class MediaInfo:
    """Metadata for a piece of media loaded into the player."""

    path: str
    title: str
    duration_ms: int = 0
    has_video: bool = True
    audio_tracks: list[TrackInfo] = field(default_factory=list)
    subtitle_tracks: list[TrackInfo] = field(default_factory=list)
