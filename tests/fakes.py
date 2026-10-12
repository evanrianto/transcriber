"""Test doubles for the speech-to-text engine."""

from __future__ import annotations

import threading
from collections.abc import Callable, Generator
from pathlib import Path

from transcriber.engine import AudioClip
from transcriber.previews import PreviewCancelled
from transcriber.transcript import Segment
from transcriber.whisper_options import LanguageMode


class FakeEngine:
    """Returns canned Segments instead of running Whisper."""

    def __init__(self, segments: list[Segment], duration: float = 60.0) -> None:
        self.segments = segments
        self.duration = duration
        self.fail_with: Exception | None = None
        self.language_modes: list[LanguageMode] = []

    def extract_audio(self, recording: Path) -> AudioClip:
        if self.fail_with is not None:
            raise self.fail_with
        return AudioClip(samples=None, duration=self.duration)

    def transcribe(self, audio: AudioClip, mode: LanguageMode) -> Generator[Segment]:
        self.language_modes.append(mode)
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

    def transcribe(self, audio: AudioClip, mode: LanguageMode) -> Generator[Segment]:
        for segment in self.segments:
            self._steps.acquire()
            yield segment


class FakeDialogs:
    """Stands in for the native OS file dialogs."""

    def __init__(self, choose: Path | None = None, save_to: Path | None = None) -> None:
        self.choose = choose
        self.save_to = save_to
        self.suggested: str | None = None

    def open_recording(self) -> Path | None:
        return self.choose

    def save_transcript_as(self, suggested: Path) -> Path | None:
        self.suggested = suggested.name
        return self.save_to


class FakePreviewer:
    """Stands in for ffmpeg. Reports 50%, then holds until the test calls `finish()`."""

    def __init__(self, needed: bool = True, fail: bool = False) -> None:
        self.needed = needed
        self.fail = fail
        self.made: list[Path] = []
        self.saw_cancel = False
        self._finish = threading.Event()

    def finish(self) -> None:
        self._finish.set()

    def needs_preview(self, recording: Path) -> bool:
        return self.needed

    def make(
        self,
        recording: Path,
        dest_dir: Path,
        on_progress: Callable[[float], None],
        cancel: threading.Event,
    ) -> Path:
        on_progress(50.0)
        while not self._finish.wait(0.01):
            if cancel.is_set():
                self.saw_cancel = True
                raise PreviewCancelled()
        if self.fail:
            raise RuntimeError("encoder exploded")
        preview = dest_dir / f"{recording.stem}.preview.mp4"
        preview.write_bytes(b"preview video")
        self.made.append(preview)
        return preview
