"""The HTTP API and page. Only ever served on localhost (see docs/adr/0001)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Sequence
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from transcriber.dialogs import Dialogs, NativeDialogs
from transcriber.jobs import Job, JobAlreadyRunning, JobManager, NoJobRunning, RecordingNotFound
from transcriber.transcript import Segment

STATIC_DIR = Path(__file__).parent / "static"


class ImportRequest(BaseModel):
    path: str


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
        "state": job.state.value,
        "duration": job.duration,
        "percent": job.percent,
        "eta_seconds": job.eta_seconds,
        "saved_to": str(job.saved_to) if job.saved_to else None,
        "error": job.error,
    }
    if include_segments:
        data["segments"] = segments_json(job.segments)
    return data


def sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload)}\n\n"


async def job_events(manager: JobManager, request: Request) -> AsyncIterator[str]:
    """Stream the current Job: each event carries its state plus only the Segments not yet sent.

    The first event replays every Segment so far, which is how a refreshed page reconnects.
    The stream ends once the Job is finished.
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
        if job.state.finished or await request.is_disconnected():
            return
        await asyncio.sleep(EVENT_POLL_SECONDS)


def clean_path(raw: str) -> Path:
    """Accept paths as users paste them, including Windows "Copy as path" quotes."""
    return Path(raw.strip().strip('"').strip("'"))


def create_app(manager: JobManager, dialogs: Dialogs | None = None) -> FastAPI:
    app = FastAPI(title="Transcriber")
    os_dialogs = dialogs if dialogs is not None else NativeDialogs()

    @app.get("/api/job")
    def get_job() -> dict[str, Any]:
        return {"job": job_json(manager.current())}

    @app.post("/api/job", status_code=201)
    def start_job(request: ImportRequest) -> dict[str, Any]:
        try:
            job = manager.start(clean_path(request.path))
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
        chosen = os_dialogs.open_recording()
        return {"path": str(chosen) if chosen else None}

    @app.get("/api/job/events")
    def stream_job_events(request: Request) -> StreamingResponse:
        return StreamingResponse(job_events(manager, request), media_type="text/event-stream")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app
