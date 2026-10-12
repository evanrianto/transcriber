"""Slow tests that run the real Whisper model. Run with `make test-slow`."""

from pathlib import Path

import numpy
import pytest

from transcriber.cuda_libs import register_cuda_libraries
from transcriber.engine import AudioClip, WhisperEngine
from transcriber.whisper_options import LanguageMode

SPEECH = Path(__file__).parent / "fixtures" / "speech.wav"

pytestmark = pytest.mark.slow


def test_the_real_engine_transcribes_english_speech() -> None:
    register_cuda_libraries()
    engine = WhisperEngine()

    audio = engine.extract_audio(SPEECH)
    text = " ".join(segment.text for segment in engine.transcribe(audio, LanguageMode.ENGLISH)).lower()

    assert 15 < audio.duration < 25
    assert "weekly team meeting" in text
    assert "launch date" in text


def test_mixed_mode_keeps_english_words_and_sentence_sized_segments() -> None:
    register_cuda_libraries()
    engine = WhisperEngine()

    clip = engine.extract_audio(SPEECH)
    # Real Recordings span many 30-second windows; repeat the clip to get several.
    audio = AudioClip(samples=numpy.tile(clip.samples, 4), duration=clip.duration * 4)
    segments = list(engine.transcribe(audio, LanguageMode.MIXED))
    text = " ".join(segment.text for segment in segments).lower()

    assert "weekly team meeting" in text
    assert len(segments) >= 8
    assert max(s.end - s.start for s in segments) < 15
