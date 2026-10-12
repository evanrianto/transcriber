"""Test doubles for the speech-to-text engine."""

from __future__ import annotations

import threading
from collections.abc import Generator
from pathlib import Path

from transcriber.engine import AudioClip
from transcriber.transcript import Segment


class FakeEngine:
    """Returns canned Segments instead of running Whisper."""

    def __init__(self, segments: list[Segment], duration: float = 60.0) -> None:
        self.segments = segments
        self.duration = duration
        self.fail_with: Exception | None = None

    def extract_audio(self, recording: Path) -> AudioClip:
        if self.fail_with is not None:
            raise self.fail_with
        return AudioClip(samples=None, duration=self.duration)

    def transcribe(self, audio: AudioClip) -> Generator[Segment]:
        yield from self.segments


class SteppedEngine:
    """Produces one Segment each time the test calls `step()`, so tests can watch a Job mid-run."""

    def __init__(self, segments: list[Segment], duration: float = 60.0) -> None:
        self.segments = segments
        self.duration = duration
        self._steps = threading.Semaphore(0)

    def step(self, count: int = 1) -> None:
        for _ in range(count):
            self._steps.release()

    def extract_audio(self, recording: Path) -> AudioClip:
        return AudioClip(samples=None, duration=self.duration)

    def transcribe(self, audio: AudioClip) -> Generator[Segment]:
        for segment in self.segments:
            self._steps.acquire()
            yield segment
