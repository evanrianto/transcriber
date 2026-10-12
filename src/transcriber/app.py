"""The HTTP API and page. Only ever served on localhost (see docs/adr/0001)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Callable, Sequence
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from transcriber.dialogs import Dialogs
from transcriber.jobs import (
    Job,
    JobAlreadyRunning,
    JobManager,
    NoJobRunning,
    NoTranscript,
    PreviewStatus,
    RecordingNotFound,
)
from transcriber.transcript import Segment, render_transcript
from transcriber.whisper_options import LanguageMode

STATIC_DIR = Path(__file__).parent / "static"


class ImportRequest(BaseModel):
    path: str
    language_mode: LanguageMode = LanguageMode.ENGLISH


EVENT_POLL_SECONDS = 0.2


def segments_json(segments: Sequence[Segment]) -> list[dict[str, Any]]:
    return [{"start": s.start, "end": s.end, "text": s.text.strip()} for s in segments]


def job_json(job: Job | None, include_segments: bool = True) -> dict[str, Any] | None:
    if job is None:
        return None
    data: dict[str, Any] = {
        "id": job.id,
        "recording": str(job.recording),
        "recording_name": job.recording.name,
        "language_mode": job.language_mode.value,
        "state": job.state.value,
        "duration": job.duration,
        "percent": job.percent,
        "eta_seconds": job.eta_seconds,
        "saved_to": str(job.saved_to) if job.saved_to else None,
        "save_error": job.save_error,
        "error": job.error,
        "preview": {"status": job.preview_status.value, "percent": job.preview_percent},
    }
    if include_segments:
        data["segments"] = segments_json(job.segments)
    return data


def sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload)}\n\n"


async def job_events(manager: JobManager, request: Request) -> AsyncIterator[str]:
    """Stream the current Job: each event carries its state plus only the Segments not yet sent.

    The first event replays every Segment so far, which is how a refreshed page reconnects.
    The stream ends once the Job is finished and its preview (if any) is ready or failed.
    """
    job_id: str | None = None
    sent = 0
    version = -1
    while True:
        job = manager.current()
        if job is None:
            yield sse({"job": None, "segments_from": 0, "new_segments": []})
            return
        if job.id != job_id:
            job_id, sent, version = job.id, 0, -1
        if job.version != version:
            yield sse(
                {
                    "job": job_json(job, include_segments=False),
                    "segments_from": sent,
                    "new_segments": segments_json(job.segments[sent:]),
                }
            )
            sent, version = len(job.segments), job.version
        if job.settled or await request.is_disconnected():
            return
        await asyncio.sleep(EVENT_POLL_SECONDS)


def clean_path(raw: str) -> Path:
    """Accept paths as users paste them, including Windows "Copy as path" quotes."""
    return Path(raw.strip().strip('"').strip("'"))


def create_app(
    manager: JobManager, dialogs: Dialogs, device: Callable[[], str] = lambda: "cuda"
) -> FastAPI:
    """`device` reports where Whisper runs ("cuda" or "cpu") so the page can warn on CPU."""
    app = FastAPI(title="Transcriber")

    @app.get("/api/system")
    def system() -> dict[str, Any]:
        return {"device": device()}

    @app.get("/api/job")
    def get_job() -> dict[str, Any]:
        return {"job": job_json(manager.current())}

    @app.post("/api/job", status_code=201)
    def start_job(request: ImportRequest) -> dict[str, Any]:
        try:
            job = manager.start(clean_path(request.path), request.language_mode)
        except RecordingNotFound as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except JobAlreadyRunning as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return {"job": job_json(job)}

    @app.post("/api/job/cancel")
    def cancel_job() -> dict[str, Any]:
        try:
            manager.cancel()
        except NoJobRunning as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return {"job": job_json(manager.current())}

    @app.post("/api/dialog/open")
    def choose_recording() -> dict[str, Any]:
        """Open the OS file dialog on this machine; blocks until the user closes it."""
        chosen = dialogs.open_recording()
        return {"path": str(chosen) if chosen else None}

    @app.get("/api/job/transcript")
    def transcript_text() -> PlainTextResponse:
        """The Transcript as `[hh:mm:ss] text` lines, for the Copy button."""
        job = manager.current()
        if job is None:
            raise HTTPException(status_code=404, detail="There is no Transcript yet")
        return PlainTextResponse(render_transcript(job.segments))

    @app.post("/api/job/save-as")
    def save_transcript_as() -> dict[str, Any]:
        """Ask where to save with the OS save dialog, then write the Transcript there."""
        try:
            chosen = dialogs.save_transcript_as(manager.suggested_transcript_path())
            if chosen is not None:
                manager.save_as(chosen)
        except NoTranscript as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except OSError as error:
            raise HTTPException(status_code=400, detail=f"Couldn't save there: {error}") from error
        return {"job": job_json(manager.current())}

    @app.get("/api/job/media")
    def play_recording() -> FileResponse:
        """The current Recording (or its preview, when the browser can't play the original).
        FileResponse honours Range requests, so the player can seek anywhere in it."""
        job = manager.current()
        if job is None:
            raise HTTPException(status_code=404, detail="No Recording to play")
        if job.preview_status is PreviewStatus.NOT_NEEDED:
            return FileResponse(job.recording)
        if job.preview_status is PreviewStatus.READY and job.preview_path is not None:
            return FileResponse(job.preview_path)
        raise HTTPException(status_code=409, detail="The preview isn't ready")

    @app.get("/api/job/events")
    def stream_job_events(request: Request) -> StreamingResponse:
        return StreamingResponse(job_events(manager, request), media_type="text/event-stream")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app
