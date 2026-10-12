"""Previews: browser-playable copies of Recordings the browser can't play as they are."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from transcriber.media import is_browser_playable, probe

PREVIEW_HEIGHT = 720
# Previews are only for checking passages, so cap the bitrate (~700 MB per hour at most).
PREVIEW_MAX_BITRATE = ["-maxrate", "1500k", "-bufsize", "3000k"]
PREVIEW_DIR_PREFIX = "transcriber-previews-"


def remove_stale_preview_dirs() -> None:
    """Delete preview folders left behind by an app that was killed instead of stopped."""
    for stale in Path(tempfile.gettempdir()).glob(f"{PREVIEW_DIR_PREFIX}*"):
        shutil.rmtree(stale, ignore_errors=True)


class PreviewCancelled(Exception):
    pass


class Previewer(Protocol):
    def needs_preview(self, recording: Path) -> bool: ...

    def make(
        self,
        recording: Path,
        dest_dir: Path,
        on_progress: Callable[[float], None],
        cancel: threading.Event,
    ) -> Path:
        """Write a playable preview of `recording` into `dest_dir` and return its path."""
        ...


class FfmpegPreviewer:
    """Converts with the ffmpeg bundled by imageio-ffmpeg: the GPU's NVENC encoder when it
    works, otherwise a fast CPU encode. Video becomes a 720p H.264 MP4; audio-only becomes
    AAC in M4A."""

    def __init__(self) -> None:
        import imageio_ffmpeg

        self._ffmpeg: str = imageio_ffmpeg.get_ffmpeg_exe()

    def needs_preview(self, recording: Path) -> bool:
        return not is_browser_playable(probe(recording))

    def make(
        self,
        recording: Path,
        dest_dir: Path,
        on_progress: Callable[[float], None],
        cancel: threading.Event,
    ) -> Path:
        info = probe(recording)
        if info.video_codec is None:
            dest = dest_dir / f"{recording.stem}.preview.m4a"
            encoders = [["-vn", "-map", "0:a:0", "-c:a", "aac", "-b:a", "128k"]]
        else:
            dest = dest_dir / f"{recording.stem}.preview.mp4"
            video = [
                "-map", "0:v:0", "-map", "0:a:0?",
                "-vf", f"scale=-2:'min({PREVIEW_HEIGHT},ih)'", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k", "-ac", "2", *PREVIEW_MAX_BITRATE,
            ]  # fmt: skip
            encoders = [
                [*video, "-c:v", "h264_nvenc", "-preset", "p4", "-cq", "30"],
                [*video, "-c:v", "libx264", "-preset", "veryfast", "-crf", "28"],
            ]

        error = ""
        for encoder_args in encoders:
            error = self._run(recording, dest, encoder_args, info.duration, on_progress, cancel)
            if not error:
                return dest
        raise RuntimeError(f"Couldn't make a preview: {error}")

    def _run(
        self,
        recording: Path,
        dest: Path,
        encoder_args: list[str],
        duration: float | None,
        on_progress: Callable[[float], None],
        cancel: threading.Event,
    ) -> str:
        """Run one ffmpeg attempt. Returns "" on success, or ffmpeg's error output."""
        command = [
            self._ffmpeg, "-nostdin", "-y", "-loglevel", "error",
            "-i", str(recording), *encoder_args,
            "-movflags", "+faststart", "-progress", "pipe:1", "-nostats", str(dest),
        ]  # fmt: skip
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8"
        )
        assert process.stdout is not None
        # Watch for cancellation independently: ffmpeg may go quiet for a while.
        watcher = threading.Thread(target=_kill_on_cancel, args=(process, cancel), daemon=True)
        watcher.start()
        for line in process.stdout:
            key, _, value = line.strip().partition("=")
            if key == "out_time_us" and duration and value.isdigit():
                on_progress(min(99.0, int(value) / 1_000_000 / duration * 100))
        process.wait()
        stderr = process.stderr.read() if process.stderr else ""
        if cancel.is_set():
            dest.unlink(missing_ok=True)
            raise PreviewCancelled()
        if process.returncode != 0:
            dest.unlink(missing_ok=True)
            return stderr.strip().splitlines()[-1] if stderr.strip() else f"exit {process.returncode}"
        return ""


def _kill_on_cancel(process: subprocess.Popen[str], cancel: threading.Event) -> None:
    while process.poll() is None:
        if cancel.wait(0.2):
            process.kill()
            return
