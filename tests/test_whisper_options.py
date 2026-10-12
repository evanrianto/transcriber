from transcriber.whisper_options import Device, LanguageMode, choose_device, whisper_options


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


def test_an_nvidia_gpu_runs_whisper_in_half_precision() -> None:
    assert choose_device(cuda_devices=1) == Device(name="cuda", compute_type="float16")


def test_without_an_nvidia_gpu_whisper_falls_back_to_the_cpu() -> None:
    assert choose_device(cuda_devices=0) == Device(name="cpu", compute_type="int8")
