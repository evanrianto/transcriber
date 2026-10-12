"""Transcripts: rendering Segments as text and saving them next to the Recording."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class Segment:
    """One timestamped span of a Transcript, in seconds from the start of the Recording."""

    start: float
    end: float
    text: str


def format_timestamp(seconds: float) -> str:
    total = int(seconds)
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def render_transcript(segments: Iterable[Segment]) -> str:
    """Render a Transcript as one `[hh:mm:ss] text` line per Segment."""
    return "".join(f"[{format_timestamp(s.start)}] {s.text.strip()}\n" for s in segments)


def transcript_path_for(recording: Path, now: datetime, copy: int = 1) -> Path:
    """Where a Transcript of `recording` made at `now` is saved: next to it, never overwriting.

    `copy` numbers further Transcripts made within the same second (`...05-2.txt`)."""
    stamp = now.strftime("%Y-%m-%d_%H-%M-%S")
    suffix = f"-{copy}" if copy > 1 else ""
    return recording.with_name(f"{recording.stem}.transcript.{stamp}{suffix}.txt")
