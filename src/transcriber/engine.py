"""The speech-to-text engine: the interface Jobs use, and the real faster-whisper implementation."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from transcriber.transcript import Segment

MODEL_NAME = "large-v3"
# Chunks of audio decoded together on the GPU. Higher is faster but makes live progress
# arrive in bigger bursts (each batch covers BATCH_SIZE x 30 seconds of audio).
BATCH_SIZE = 8


@dataclass(frozen=True)
class AudioClip:
    """A Recording's audio track, decoded and ready for Whisper."""

    samples: Any
    duration: float


class Engine(Protocol):
    def extract_audio(self, recording: Path) -> AudioClip: ...

    def transcribe(self, audio: AudioClip) -> Iterator[Segment]: ...


class WhisperEngine:
    """faster-whisper running large-v3 on an NVIDIA GPU, batched for speed.

    The batched pipeline always splits audio with the voice detector (VAD) first, which
    also stops Whisper inventing text over silence and music.

    The model takes several seconds to load, so `preload()` starts loading it in the
    background at app startup; `transcribe` waits for it.
    """

    def __init__(self) -> None:
        self._model: Any = None
        self._load_error: BaseException | None = None
        self._loaded = threading.Event()
        self._load_started = threading.Lock()
        self._loading = False

    def preload(self) -> None:
        with self._load_started:
            if self._loading:
                return
            self._loading = True
        threading.Thread(target=self._load, name="whisper-load", daemon=True).start()

    def _load(self) -> None:
        try:
            from faster_whisper import BatchedInferencePipeline, WhisperModel

            model = WhisperModel(MODEL_NAME, device="cuda", compute_type="float16")
            self._model = BatchedInferencePipeline(model)
        except BaseException as error:  # surfaced to the Job that needs the model
            self._load_error = error
        finally:
            self._loaded.set()

    def _ready_model(self) -> Any:
        self.preload()
        self._loaded.wait()
        if self._load_error is not None:
            raise RuntimeError(f"Could not load the Whisper model: {self._load_error}")
        return self._model

    def extract_audio(self, recording: Path) -> AudioClip:
        from faster_whisper.audio import decode_audio

        sampling_rate = 16000
        samples = decode_audio(str(recording), sampling_rate=sampling_rate)
        return AudioClip(samples=samples, duration=len(samples) / sampling_rate)

    def transcribe(self, audio: AudioClip) -> Iterator[Segment]:
        model = self._ready_model()
        segments, _info = model.transcribe(
            audio.samples,
            language="en",
            beam_size=5,
            batch_size=BATCH_SIZE,
            without_timestamps=False,  # keeps Segments sentence-sized instead of 30 seconds
        )
        for segment in segments:
            yield Segment(start=segment.start, end=segment.end, text=segment.text)


def download_model_cli() -> None:
    """Download the Whisper model into the local cache so the first Job doesn't have to."""
    from faster_whisper import download_model

    print(f"Downloading Whisper {MODEL_NAME} (about 3 GB, skipped if already downloaded)...")
    path = download_model(MODEL_NAME)
    print(f"Model ready: {path}")
