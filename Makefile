# Transcriber: run `make install` once, then `make run`.
# `make install` picks your OS; `make install-windows`, `install-macos` and `install-linux`
# do the same thing for one OS explicitly.

ifeq ($(OS),Windows_NT)
  PLATFORM := windows
  UV := powershell -NoProfile -ExecutionPolicy Bypass -File scripts/uv.ps1
else
  PLATFORM := $(if $(filter Darwin,$(shell uname -s)),macos,linux)
  UV := sh scripts/uv.sh
endif

.PHONY: help install install-windows install-macos install-linux run test test-slow typecheck

# Messages print with $(info) or plain unquoted echo: on Windows, make runs recipes with
# cmd.exe or sh depending on what's installed, and the two treat quotes differently.

## help: list the commands
help:
	$(info make install          install everything for this computer ($(PLATFORM)))
	$(info make install-windows  install on Windows (NVIDIA GPU if present, otherwise CPU))
	$(info make install-macos    install on macOS (CPU only))
	$(info make install-linux    install on Linux (NVIDIA GPU if present, otherwise CPU))
	$(info make run              start the app at http://localhost:8765)
	$(info make test             run the fast tests)
	$(info make test-slow        also run the tests that use the real model and ffmpeg)
	$(info make typecheck        run mypy)
	@:

## install: install uv (if missing), Python 3.12, all dependencies, and the Whisper model.
## The model download step also reports whether transcription will use the GPU or the CPU.
install: install-$(PLATFORM)

install-windows:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/uv.ps1 sync
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/uv.ps1 run transcriber-download-model
	@echo Installed. Start the app with: make run

# macOS has no NVIDIA GPUs, so no CUDA libraries are installed and Whisper runs on the CPU.
install-macos:
	sh scripts/uv.sh sync
	sh scripts/uv.sh run transcriber-download-model
	@echo Installed. Start the app with: make run

install-linux:
	sh scripts/uv.sh sync
	sh scripts/uv.sh run transcriber-download-model
	@echo Installed. Start the app with: make run

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
