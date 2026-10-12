import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import pytest

from tests.fakes import FakeEngine, SteppedEngine
from transcriber.jobs import (
    JobAlreadyRunning,
    JobManager,
    JobState,
    NoJobRunning,
    RecordingNotFound,
)
from transcriber.transcript import Segment
from transcriber.whisper_options import LanguageMode

SEGMENTS = [
    Segment(start=0.0, end=3.0, text="Hello and welcome."),
    Segment(start=3.0, end=7.5, text="Let's get started."),
]


def fixed_clock() -> datetime:
    return datetime(2026, 10, 12, 14, 30, 5)


@pytest.fixture
def recording(tmp_path: Path) -> Path:
    path = tmp_path / "meeting.mp4"
    path.write_bytes(b"not really a video")
    return path


def test_a_job_transcribes_the_recording_and_saves_the_transcript_next_to_it(
    recording: Path,
) -> None:
    manager = JobManager(FakeEngine(SEGMENTS), clock=fixed_clock)

    manager.start(recording)
    manager.wait(timeout=5)

    job = manager.current()
    assert job is not None
    assert job.state is JobState.DONE
    assert job.segments == SEGMENTS
    expected = recording.parent / "meeting.transcript.2026-10-12_14-30-05.txt"
    assert job.saved_to == expected
    assert expected.read_text(encoding="utf-8") == (
        "[00:00:00] Hello and welcome.\n[00:00:03] Let's get started.\n"
    )


def test_a_recording_that_does_not_exist_is_rejected(tmp_path: Path) -> None:
    manager = JobManager(FakeEngine(SEGMENTS), clock=fixed_clock)

    with pytest.raises(RecordingNotFound):
        manager.start(tmp_path / "missing.mp4")

    assert manager.current() is None


def test_an_engine_error_fails_the_job_with_a_readable_message(recording: Path) -> None:
    engine = FakeEngine(SEGMENTS)
    engine.fail_with = ValueError("Invalid data found when processing input")
    manager = JobManager(engine, clock=fixed_clock)

    manager.start(recording)
    manager.wait(timeout=5)

    job = manager.current()
    assert job is not None
    assert job.state is JobState.FAILED
    assert job.error == "Invalid data found when processing input"
    assert list(recording.parent.glob("*.txt")) == []


class FakeTimer:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def wait_for(condition: Callable[[], bool], timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while not condition():
        if time.monotonic() > deadline:
            raise AssertionError("condition not reached in time")
        time.sleep(0.01)


def test_progress_tracks_how_far_through_the_recording_transcription_has_reached(
    recording: Path,
) -> None:
    engine = SteppedEngine(
        [
            Segment(start=0.0, end=15.0, text="First quarter."),
            Segment(start=15.0, end=30.0, text="Halfway."),
            Segment(start=30.0, end=60.0, text="The end."),
        ],
        duration=60.0,
    )
    timer = FakeTimer()
    manager = JobManager(engine, clock=fixed_clock, timer=timer)
    manager.start(recording)
    wait_for(lambda: (job := manager.current()) is not None and job.state is JobState.TRANSCRIBING)

    timer.now = 10.0
    engine.step()
    wait_for(lambda: len(manager.current().segments) == 1)  # type: ignore[union-attr]
    job = manager.current()
    assert job is not None
    assert job.percent == 25.0
    assert job.eta_seconds == 30.0  # 10s for the first 25%, so 30s for the remaining 75%

    timer.now = 20.0
    engine.step()
    wait_for(lambda: len(manager.current().segments) == 2)  # type: ignore[union-attr]
    job = manager.current()
    assert job is not None
    assert job.percent == 50.0
    assert job.eta_seconds == 20.0

    engine.step()
    manager.wait(timeout=5)


def test_only_one_job_runs_at_a_time(recording: Path) -> None:
    engine = SteppedEngine(SEGMENTS)
    manager = JobManager(engine, clock=fixed_clock)
    manager.start(recording)

    with pytest.raises(JobAlreadyRunning):
        manager.start(recording)

    engine.step(len(SEGMENTS))
    manager.wait(timeout=5)
    manager.start(recording)  # allowed again once the first Job is finished
    engine.step(len(SEGMENTS))
    manager.wait(timeout=5)
    assert manager.current().state is JobState.DONE  # type: ignore[union-attr]


def test_cancelling_stops_the_job_and_writes_nothing(recording: Path) -> None:
    engine = SteppedEngine(SEGMENTS)
    manager = JobManager(engine, clock=fixed_clock)
    manager.start(recording)
    engine.step()
    wait_for(lambda: len(manager.current().segments) == 1)  # type: ignore[union-attr]

    manager.cancel()
    engine.step()  # unblock the engine so the worker can notice
    manager.wait(timeout=5)

    job = manager.current()
    assert job is not None
    assert job.state is JobState.CANCELLED
    assert list(recording.parent.glob("*.txt")) == []
    manager.start(recording)  # importing is available again
    engine.step(len(SEGMENTS))
    manager.wait(timeout=5)


def test_cancelling_when_nothing_is_running_is_an_error(recording: Path) -> None:
    manager = JobManager(FakeEngine(SEGMENTS), clock=fixed_clock)

    with pytest.raises(NoJobRunning):
        manager.cancel()


def test_the_job_transcribes_in_the_chosen_language_mode(recording: Path) -> None:
    engine = FakeEngine(SEGMENTS)
    manager = JobManager(engine, clock=fixed_clock)

    manager.start(recording, LanguageMode.MIXED)
    manager.wait(timeout=5)

    assert engine.language_modes == [LanguageMode.MIXED]
    assert manager.current().language_mode is LanguageMode.MIXED  # type: ignore[union-attr]
