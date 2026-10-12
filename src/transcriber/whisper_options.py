"""How each Language Mode is turned into settings for Whisper."""

from __future__ import annotations

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
