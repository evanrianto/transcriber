import json
import socket
import threading
import time
from collections.abc import Callable, Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
import uvicorn
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.fakes import FakeEngine, SteppedEngine
from transcriber.app import create_app
from transcriber.jobs import JobManager
from transcriber.transcript import Segment

SEGMENTS = [
    Segment(start=0.0, end=3.0, text="Hello and welcome."),
    Segment(start=3.0, end=7.5, text="Let's get started."),
]


@pytest.fixture
def recording(tmp_path: Path) -> Path:
    path = tmp_path / "meeting.mp4"
    path.write_bytes(b"not really a video")
    return path


@pytest.fixture
def manager() -> JobManager:
    return JobManager(FakeEngine(SEGMENTS), clock=lambda: datetime(2026, 10, 12, 14, 30, 5))


@pytest.fixture
def client(manager: JobManager) -> TestClient:
    return TestClient(create_app(manager))


def test_there_is_no_job_before_the_first_import(client: TestClient) -> None:
    response = client.get("/api/job")

    assert response.status_code == 200
    assert response.json() == {"job": None}


def test_importing_a_recording_by_path_runs_a_job_to_a_saved_transcript(
    client: TestClient, manager: JobManager, recording: Path
) -> None:
    response = client.post("/api/job", json={"path": str(recording)})
    assert response.status_code == 201
    manager.wait(timeout=5)

    job = client.get("/api/job").json()["job"]

    assert job["state"] == "done"
    assert job["recording_name"] == "meeting.mp4"
    assert job["segments"] == [
        {"start": 0.0, "end": 3.0, "text": "Hello and welcome."},
        {"start": 3.0, "end": 7.5, "text": "Let's get started."},
    ]
    assert job["saved_to"] == str(recording.parent / "meeting.transcript.2026-10-12_14-30-05.txt")


def test_importing_a_path_that_does_not_exist_is_a_clear_error(
    client: TestClient, tmp_path: Path
) -> None:
    response = client.post("/api/job", json={"path": str(tmp_path / "nope.mp4")})

    assert response.status_code == 400
    assert "nope.mp4" in response.json()["detail"]


def test_the_page_is_served_at_the_root(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "<title>Transcriber</title>" in response.text


def next_event(lines: Iterator[str], matches: Callable[[dict[str, Any]], bool]) -> dict[str, Any]:
    """Read server-sent events until one matches."""
    for line in lines:
        if line.startswith("data: "):
            event: dict[str, Any] = json.loads(line.removeprefix("data: "))
            if matches(event):
                return event
    raise AssertionError("stream ended without a matching event")


class LiveServer:
    """Runs the app on a real localhost port. TestClient buffers whole responses, so
    watching the event stream live needs a real server."""

    def __init__(self, app: FastAPI) -> None:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        self.url = f"http://127.0.0.1:{port}"
        self.server = uvicorn.Server(uvicorn.Config(app, port=port, log_level="warning"))
        self.thread = threading.Thread(target=self.server.run, daemon=True)

    def __enter__(self) -> "LiveServer":
        self.thread.start()
        while not self.server.started:
            time.sleep(0.01)
        return self

    def __exit__(self, *exc: object) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=5)


def test_the_event_stream_sends_new_segments_as_they_are_produced(
    recording: Path,
) -> None:
    engine = SteppedEngine(SEGMENTS + [Segment(start=7.5, end=9.0, text="Third.")], duration=9.0)
    manager = JobManager(engine)
    manager.start(recording)
    engine.step()

    with (
        LiveServer(create_app(manager)) as server,
        httpx.stream("GET", f"{server.url}/api/job/events", timeout=5) as response,
    ):
        lines = response.iter_lines()
        first = next_event(lines, lambda e: len(e["new_segments"]) >= 1)
        engine.step()
        second = next_event(lines, lambda e: e["segments_from"] >= 1)
        engine.step()  # let the Job finish so the stream closes
        last = next_event(lines, lambda e: e["job"]["state"] == "done")

    assert first["job"]["state"] == "transcribing"
    assert first["segments_from"] == 0
    assert [s["text"] for s in first["new_segments"]] == ["Hello and welcome."]
    assert second["segments_from"] == 1
    assert [s["text"] for s in second["new_segments"]] == ["Let's get started."]
    assert second["job"]["percent"] == pytest.approx(83.3)
    assert last["job"]["saved_to"] is not None


def test_the_event_stream_replays_a_finished_job_and_closes(
    client: TestClient, manager: JobManager, recording: Path
) -> None:
    client.post("/api/job", json={"path": str(recording)})
    manager.wait(timeout=5)

    with client.stream("GET", "/api/job/events") as response:
        events = [
            json.loads(line.removeprefix("data: "))
            for line in response.iter_lines()
            if line.startswith("data: ")
        ]

    assert len(events) == 1
    assert events[0]["job"]["state"] == "done"
    assert events[0]["segments_from"] == 0
    assert len(events[0]["new_segments"]) == 2
