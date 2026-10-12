# Transcriber: run `make install` once, then `make run`.

ifeq ($(OS),Windows_NT)
  UV := powershell -NoProfile -ExecutionPolicy Bypass -File scripts/uv.ps1
else
  UV := sh scripts/uv.sh
endif

.PHONY: install run test test-slow typecheck

## install: install uv (if missing), Python 3.12, all dependencies, and the Whisper model
install:
	$(UV) sync
	$(UV) run transcriber-download-model

## run: start the app on localhost and open it in the browser
run:
	$(UV) run transcriber

## test: run the fast test suite
test:
	$(UV) run pytest

## test-slow: run the tests that use the real Whisper model and ffmpeg
test-slow:
	$(UV) run pytest -m slow

## typecheck: run mypy over the source and tests
typecheck:
	$(UV) run mypy
