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

from tests.fakes import FakeDialogs, FakeEngine, FakePreviewer, SteppedEngine
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
    return TestClient(create_app(manager, dialogs=FakeDialogs()))


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
        LiveServer(create_app(manager, dialogs=FakeDialogs())) as server,
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


def test_importing_while_a_job_runs_is_refused(recording: Path) -> None:
    engine = SteppedEngine(SEGMENTS)
    manager = JobManager(engine)
    client = TestClient(create_app(manager, dialogs=FakeDialogs()))
    client.post("/api/job", json={"path": str(recording)})

    response = client.post("/api/job", json={"path": str(recording)})

    assert response.status_code == 409
    assert "already running" in response.json()["detail"]
    engine.step(len(SEGMENTS))
    manager.wait(timeout=5)


def test_a_running_job_can_be_cancelled(recording: Path) -> None:
    engine = SteppedEngine(SEGMENTS)
    manager = JobManager(engine)
    client = TestClient(create_app(manager, dialogs=FakeDialogs()))
    client.post("/api/job", json={"path": str(recording)})

    response = client.post("/api/job/cancel")
    engine.step(len(SEGMENTS))
    manager.wait(timeout=5)

    assert response.status_code == 200
    assert client.get("/api/job").json()["job"]["state"] == "cancelled"
    assert client.post("/api/job/cancel").status_code == 409


def test_choose_file_returns_the_path_picked_in_the_os_dialog(manager: JobManager) -> None:
    picked = Path("D:/Videos/meeting.mp4")
    client = TestClient(create_app(manager, dialogs=FakeDialogs(choose=picked)))

    response = client.post("/api/dialog/open")

    assert response.status_code == 200
    assert response.json() == {"path": str(picked)}


def test_closing_the_os_dialog_without_choosing_returns_no_path(manager: JobManager) -> None:
    client = TestClient(create_app(manager, dialogs=FakeDialogs(choose=None)))

    assert client.post("/api/dialog/open").json() == {"path": None}


def test_the_language_mode_is_chosen_at_import_and_defaults_to_english(
    client: TestClient, manager: JobManager, recording: Path
) -> None:
    client.post("/api/job", json={"path": str(recording)})
    manager.wait(timeout=5)
    assert client.get("/api/job").json()["job"]["language_mode"] == "english"

    client.post("/api/job", json={"path": str(recording), "language_mode": "mixed"})
    manager.wait(timeout=5)
    assert client.get("/api/job").json()["job"]["language_mode"] == "mixed"


def test_an_unknown_language_mode_is_rejected(client: TestClient, recording: Path) -> None:
    response = client.post("/api/job", json={"path": str(recording), "language_mode": "auto"})

    assert response.status_code == 422


def test_the_recording_is_streamed_for_playback_with_seek_support(
    client: TestClient, manager: JobManager, recording: Path
) -> None:
    client.post("/api/job", json={"path": str(recording)})
    manager.wait(timeout=5)

    whole = client.get("/api/job/media")
    part = client.get("/api/job/media", headers={"Range": "bytes=4-9"})

    assert whole.status_code == 200
    assert whole.content == b"not really a video"
    assert whole.headers["accept-ranges"] == "bytes"
    assert part.status_code == 206
    assert part.content == b"really"


def test_there_is_nothing_to_play_before_the_first_import(client: TestClient) -> None:
    assert client.get("/api/job/media").status_code == 404


def test_a_converted_preview_is_played_instead_of_the_original(recording: Path) -> None:
    previewer = FakePreviewer(needed=True)
    manager = JobManager(FakeEngine(SEGMENTS), previewer=previewer)
    client = TestClient(create_app(manager, dialogs=FakeDialogs()))
    client.post("/api/job", json={"path": str(recording)})
    manager.wait(timeout=5)

    converting = client.get("/api/job").json()["job"]["preview"]
    still_converting = client.get("/api/job/media")
    previewer.finish()
    with client.stream("GET", "/api/job/events") as response:  # ends once the preview is ready
        last = [line for line in response.iter_lines() if line.startswith("data: ")][-1]
    ready = client.get("/api/job/media")

    assert converting == {"status": "converting", "percent": 50.0}
    assert still_converting.status_code == 409
    assert json.loads(last.removeprefix("data: "))["job"]["preview"]["status"] == "ready"
    assert ready.status_code == 200
    assert ready.content == b"preview video"
    manager.close()


def test_the_transcript_text_can_be_fetched_for_copying(
    client: TestClient, manager: JobManager, recording: Path
) -> None:
    client.post("/api/job", json={"path": str(recording)})
    manager.wait(timeout=5)

    response = client.get("/api/job/transcript")

    assert response.status_code == 200
    assert response.text == "[00:00:00] Hello and welcome.\n[00:00:03] Let's get started.\n"


def test_save_as_asks_where_to_save_with_the_usual_name_and_saves_there(
    recording: Path, tmp_path: Path
) -> None:
    chosen = tmp_path / "chosen.txt"
    dialogs = FakeDialogs(save_to=chosen)
    manager = JobManager(FakeEngine(SEGMENTS), clock=lambda: datetime(2026, 10, 12, 14, 30, 5))
    client = TestClient(create_app(manager, dialogs=dialogs))
    client.post("/api/job", json={"path": str(recording)})
    manager.wait(timeout=5)

    response = client.post("/api/job/save-as")

    assert response.status_code == 200
    assert dialogs.suggested == "meeting.transcript.2026-10-12_14-30-05.txt"
    assert response.json()["job"]["saved_to"] == str(chosen)
    assert chosen.read_text(encoding="utf-8").startswith("[00:00:00] Hello and welcome.")


def test_closing_the_save_dialog_saves_nothing(
    client: TestClient, manager: JobManager, recording: Path
) -> None:
    client.post("/api/job", json={"path": str(recording)})
    manager.wait(timeout=5)
    saved_before = client.get("/api/job").json()["job"]["saved_to"]

    response = client.post("/api/job/save-as")

    assert response.status_code == 200
    assert response.json()["job"]["saved_to"] == saved_before
