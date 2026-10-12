"""How each Language Mode is turned into settings for Whisper."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TypedDict


class LanguageMode(StrEnum):
    ENGLISH = "english"
    INDONESIAN = "indonesian"
    MIXED = "mixed"


class WhisperOptions(TypedDict):
    language: str
    initial_prompt: str | None


# Code-mixed Indonesian with English words left as spoken. Whisper continues in the style
# of its prompt, so this nudges it to keep English words English instead of translating
# them. Not yet validated on a real code-mixed Recording.
MIXED_PROMPT = (
    "Oke, jadi basically kita harus submit report-nya besok. "
    "Habis meeting jam sepuluh, nanti kita review deadline-nya bareng ya."
)


def whisper_options(mode: LanguageMode) -> WhisperOptions:
    """Mixed forces Indonesian: per-Segment language detection can't follow switches
    inside a sentence, and Whisper's Indonesian keeps English loanwords well."""
    if mode is LanguageMode.ENGLISH:
        return {"language": "en", "initial_prompt": None}
    if mode is LanguageMode.INDONESIAN:
        return {"language": "id", "initial_prompt": None}
    return {"language": "id", "initial_prompt": MIXED_PROMPT}


@dataclass(frozen=True)
class Device:
    """Where Whisper runs, and at what numeric precision."""

    name: str  # "cuda" or "cpu"
    compute_type: str


def choose_device(cuda_devices: int) -> Device:
    """NVIDIA GPUs run in float16. Everything else (macOS, AMD, no GPU) runs on the CPU
    in int8, which is several times slower but works everywhere."""
    if cuda_devices > 0:
        return Device(name="cuda", compute_type="float16")
    return Device(name="cpu", compute_type="int8")
