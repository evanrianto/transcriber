"""Slow tests that run the real Whisper model. Run with `make test-slow`."""

from pathlib import Path

import pytest

from transcriber.cuda_libs import register_cuda_libraries
from transcriber.engine import WhisperEngine

SPEECH = Path(__file__).parent / "fixtures" / "speech.wav"

pytestmark = pytest.mark.slow


def test_the_real_engine_transcribes_english_speech() -> None:
    register_cuda_libraries()
    engine = WhisperEngine()

    audio = engine.extract_audio(SPEECH)
    text = " ".join(segment.text for segment in engine.transcribe(audio)).lower()

    assert 15 < audio.duration < 25
    assert "weekly team meeting" in text
    assert "launch date" in text
