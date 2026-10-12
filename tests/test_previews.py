"""Slow tests that run the real ffmpeg. Run with `make test-slow`."""

import subprocess
import threading
from pathlib import Path

import imageio_ffmpeg
import pytest

from transcriber.media import is_browser_playable, probe
from transcriber.previews import FfmpegPreviewer

pytestmark = pytest.mark.slow


def make_media(path: Path, *args: str) -> Path:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ffmpeg, "-loglevel", "error", "-y", *args, str(path)], check=True)
    return path


def test_an_hevc_mkv_becomes_a_playable_preview(tmp_path: Path) -> None:
    source = make_media(
        tmp_path / "talk.mkv",
        "-f", "lavfi", "-i", "testsrc2=size=1920x1080:rate=25:duration=3",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
        "-c:v", "libx265", "-preset", "ultrafast", "-c:a", "ac3",
    )  # fmt: skip
    previewer = FfmpegPreviewer()
    progress: list[float] = []
    assert previewer.needs_preview(source)

    preview = previewer.make(source, tmp_path, progress.append, threading.Event())

    info = probe(preview)
    assert is_browser_playable(info)
    assert (info.video_codec, info.audio_codec) == ("h264", "aac")
    assert progress and progress[-1] <= 99.0


def test_an_audio_only_recording_becomes_a_playable_audio_preview(tmp_path: Path) -> None:
    source = make_media(
        tmp_path / "voice.wma", "-f", "lavfi", "-i", "sine=frequency=300:duration=3", "-c:a", "wmav2"
    )
    previewer = FfmpegPreviewer()

    preview = previewer.make(source, tmp_path, lambda _: None, threading.Event())

    assert preview.suffix == ".m4a"
    assert is_browser_playable(probe(preview))
