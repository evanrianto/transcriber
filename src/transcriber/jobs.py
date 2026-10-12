"""Jobs: one attempt to turn a Recording into a Transcript, run in the background."""

from __future__ import annotations

import dataclasses
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path

from transcriber.engine import Engine
from transcriber.transcript import Segment, render_transcript, transcript_path_for


class JobState(StrEnum):
    EXTRACTING_AUDIO = "extracting_audio"
    TRANSCRIBING = "transcribing"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def finished(self) -> bool:
        return self in (JobState.DONE, JobState.FAILED, JobState.CANCELLED)


class RecordingNotFound(Exception):
    pass


class JobAlreadyRunning(Exception):
    pass


class NoJobRunning(Exception):
    pass


@dataclass
class Job:
    id: str
    recording: Path
    state: JobState
    segments: list[Segment] = field(default_factory=list)
    duration: float | None = None
    saved_to: Path | None = None
    error: str | None = None
    percent: float = 0.0
    eta_seconds: float | None = None
    transcribing_since: float | None = None
    version: int = 0  # bumped on every change, so watchers know when to send an update

    def record_progress(self, segment: Segment, now: float) -> None:
        """Update percent and time remaining from how far into the Recording `segment` ends."""
        if not self.duration or self.transcribing_since is None:
            return
        fraction = min(1.0, segment.end / self.duration)
        self.percent = round(fraction * 100, 1)
        elapsed = now - self.transcribing_since
        self.eta_seconds = elapsed * (1 - fraction) / fraction if fraction > 0 else None


class JobManager:
    """Runs one Job at a time on a background thread and exposes its current state."""

    def __init__(
        self,
        engine: Engine,
        clock: Callable[[], datetime] = datetime.now,
        timer: Callable[[], float] = time.monotonic,
    ) -> None:
        self._engine = engine
        self._clock = clock
        self._timer = timer
        self._lock = threading.Lock()
        self._job: Job | None = None
        self._worker: threading.Thread | None = None
        self._cancel = threading.Event()

    def current(self) -> Job | None:
        """A snapshot of the most recent Job, safe to read while it keeps running."""
        with self._lock:
            if self._job is None:
                return None
            return dataclasses.replace(self._job, segments=list(self._job.segments))

    def start(self, recording: Path) -> Job:
        """Start transcribing `recording`. Only one Job runs at a time; there is no queue."""
        if not recording.is_file():
            raise RecordingNotFound(f"No file at {recording}")
        job = Job(id=uuid.uuid4().hex, recording=recording, state=JobState.EXTRACTING_AUDIO)
        with self._lock:
            if self._job is not None and not self._job.state.finished:
                raise JobAlreadyRunning(f"A Job is already running for {self._job.recording.name}")
            self._job = job
            self._cancel = threading.Event()
            cancel = self._cancel
        self._worker = threading.Thread(
            target=self._run, args=(job, cancel), name="job", daemon=True
        )
        self._worker.start()
        return job

    def cancel(self) -> None:
        """Stop the running Job as soon as the engine yields; a cancelled Job writes nothing."""
        with self._lock:
            if self._job is None or self._job.state.finished:
                raise NoJobRunning("No Job is running")
            self._cancel.set()

    def wait(self, timeout: float | None = None) -> None:
        """Block until the current Job's worker finishes (used by tests and shutdown)."""
        if self._worker is not None:
            self._worker.join(timeout)

    def _run(self, job: Job, cancel: threading.Event) -> None:
        try:
            audio = self._engine.extract_audio(job.recording)
            if cancel.is_set():
                return self._mark_cancelled(job)
            with self._lock:
                job.duration = audio.duration
                job.state = JobState.TRANSCRIBING
                job.transcribing_since = self._timer()
                job.version += 1
            segments = self._engine.transcribe(audio)
            for segment in segments:
                if cancel.is_set():
                    segments.close()
                    return self._mark_cancelled(job)
                with self._lock:
                    job.segments.append(segment)
                    job.record_progress(segment, self._timer())
                    job.version += 1
            if cancel.is_set():
                return self._mark_cancelled(job)
            saved_to = transcript_path_for(job.recording, self._clock())
            saved_to.write_text(render_transcript(job.segments), encoding="utf-8")
            with self._lock:
                job.saved_to = saved_to
                job.state = JobState.DONE
                job.version += 1
        except Exception as error:
            with self._lock:
                job.error = str(error) or type(error).__name__
                job.state = JobState.FAILED
                job.version += 1

    def _mark_cancelled(self, job: Job) -> None:
        with self._lock:
            job.state = JobState.CANCELLED
            job.version += 1
