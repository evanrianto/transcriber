from transcriber.whisper_options import LanguageMode, whisper_options


def test_english_forces_english_with_no_prompt() -> None:
    assert whisper_options(LanguageMode.ENGLISH) == {"language": "en", "initial_prompt": None}


def test_indonesian_forces_indonesian_with_no_prompt() -> None:
    assert whisper_options(LanguageMode.INDONESIAN) == {"language": "id", "initial_prompt": None}


def test_mixed_forces_indonesian_and_hints_that_english_words_stay_english() -> None:
    options = whisper_options(LanguageMode.MIXED)

    assert options["language"] == "id"
    prompt = options["initial_prompt"]
    assert isinstance(prompt, str)
    # The hint is Indonesian text with English words left untranslated.
    assert "kita" in prompt
    assert "meeting" in prompt
