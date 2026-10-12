"""Recordings as media: what's inside them, and whether a browser can play them as-is."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# What browsers (Chrome, Edge, Firefox) reliably play, by file extension: the video codecs
# and audio codecs each container may hold. None means "no stream of that kind".
_PLAYABLE: dict[str, tuple[set[str | None], set[str | None]]] = {
    ".mp4": ({"h264", "av1", None}, {"aac", "mp3", None}),
    ".m4v": ({"h264", "av1", None}, {"aac", "mp3", None}),
    ".mov": ({"h264", None}, {"aac", "mp3", None}),
    ".webm": ({"vp8", "vp9", "av1", None}, {"opus", "vorbis", None}),
    ".mp3": ({None}, {"mp3"}),
    ".m4a": ({None}, {"aac"}),
    ".aac": ({None}, {"aac"}),
    ".wav": ({None}, {"pcm_s16le", "pcm_s24le", "pcm_s32le", "pcm_f32le", "pcm_u8"}),
    ".flac": ({None}, {"flac"}),
    ".ogg": ({None}, {"opus", "vorbis"}),
    ".opus": ({None}, {"opus"}),
}

# Album art inside audio files shows up as a one-frame "video" stream.
_COVER_ART_CODECS = {"mjpeg", "png", "bmp"}


@dataclass(frozen=True)
class MediaInfo:
    extension: str
    video_codec: str | None
    audio_codec: str | None
    duration: float | None = None


def is_browser_playable(info: MediaInfo) -> bool:
    allowed = _PLAYABLE.get(info.extension.lower())
    if allowed is None:
        return False
    video_codecs, audio_codecs = allowed
    return info.video_codec in video_codecs and info.audio_codec in audio_codecs


def probe(path: Path) -> MediaInfo:
    """Read a Recording's container and codecs without decoding it."""
    import av

    with av.open(str(path)) as container:
        video = next(
            (s for s in container.streams.video if s.codec_context.name not in _COVER_ART_CODECS),
            None,
        )
        audio = next(iter(container.streams.audio), None)
        duration = container.duration / av.time_base if container.duration else None
        return MediaInfo(
            extension=path.suffix.lower(),
            video_codec=video.codec_context.name if video else None,
            audio_codec=audio.codec_context.name if audio else None,
            duration=duration,
        )
