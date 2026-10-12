"""The speech-to-text engine: the interface Jobs use, and the real faster-whisper implementation."""

from __future__ import annotations

import threading
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from transcriber.transcript import Segment
from transcriber.whisper_options import Device, LanguageMode, choose_device, whisper_options

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

    def transcribe(self, audio: AudioClip, mode: LanguageMode) -> Generator[Segment]: ...


class WhisperEngine:
    """faster-whisper running large-v3, batched for speed: on an NVIDIA GPU when there is
    one, otherwise (or if the GPU fails to load the model) on the CPU.

    The batched pipeline always splits audio with the voice detector (VAD) first, which
    also stops Whisper inventing text over silence and music.

    The model takes several seconds to load, so `preload()` starts loading it in the
    background at app startup; `transcribe` waits for it.
    """

    def __init__(self) -> None:
        self.device = self._planned_device()
        self._model: Any = None
        self._batched: Any = None
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

    @staticmethod
    def _planned_device() -> Device:
        try:
            import ctranslate2

            return choose_device(ctranslate2.get_cuda_device_count())
        except Exception:
            return choose_device(0)

    def _load(self) -> None:
        try:
            from faster_whisper import BatchedInferencePipeline, WhisperModel

            try:
                self._model = self._load_model(WhisperModel, self.device)
            except Exception:
                if self.device.name == "cpu":
                    raise
                # e.g. missing CUDA libraries or an unsupported GPU: CPU still works.
                self.device = choose_device(0)
                self._model = self._load_model(WhisperModel, self.device)
            self._batched = BatchedInferencePipeline(self._model)
        except BaseException as error:  # surfaced to the Job that needs the model
            self._load_error = error
        finally:
            self._loaded.set()

    @staticmethod
    def _load_model(whisper_model: Any, device: Device) -> Any:
        import numpy

        model = whisper_model(MODEL_NAME, device=device.name, compute_type=device.compute_type)
        # CUDA libraries load lazily, so a broken GPU setup only shows on first use: warm up
        # on a second of silence now, while falling back to the CPU is still possible.
        segments, _info = model.transcribe(numpy.zeros(16000, dtype=numpy.float32), language="en")
        list(segments)
        return model

    def _wait_for_model(self) -> None:
        self.preload()
        self._loaded.wait()
        if self._load_error is not None:
            raise RuntimeError(f"Could not load the Whisper model: {self._load_error}")

    def extract_audio(self, recording: Path) -> AudioClip:
        from faster_whisper.audio import decode_audio

        sampling_rate = 16000
        samples = decode_audio(str(recording), sampling_rate=sampling_rate)
        return AudioClip(samples=samples, duration=len(samples) / sampling_rate)

    def transcribe(self, audio: AudioClip, mode: LanguageMode) -> Generator[Segment]:
        self._wait_for_model()
        options = whisper_options(mode)
        if options["initial_prompt"] is None:
            segments, _info = self._batched.transcribe(
                audio.samples,
                **options,
                beam_size=5,
                batch_size=BATCH_SIZE,
                without_timestamps=False,  # keeps Segments sentence-sized instead of 30 seconds
            )
        else:
            # A prompt makes the batched pipeline emit 30-second Segments, so prompted
            # Language Modes (Mixed) use the sequential pipeline: ~9x slower, same timestamps.
            segments, _info = self._model.transcribe(
                audio.samples, **options, beam_size=5, vad_filter=True
            )
        for segment in segments:
            yield Segment(start=segment.start, end=segment.end, text=segment.text)


def download_model_cli() -> None:
    """Download the Whisper model into the local cache so the first Job doesn't have to."""
    from faster_whisper import download_model

    print(f"Downloading Whisper {MODEL_NAME} (about 3 GB, skipped if already downloaded)...")
    path = download_model(MODEL_NAME)
    print(f"Model ready: {path}")
