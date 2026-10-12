"""Native OS file dialogs, opened by the server on the user's own machine (see ADR-0001).

Each dialog runs in a short-lived child process (`python -m transcriber.dialogs ...`):
Tk must own its process's main thread (macOS crashes otherwise), while the server
handles requests on worker threads.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Protocol

MEDIA_EXTENSIONS = (
    "*.mp4 *.mkv *.mov *.avi *.webm *.m4v *.wmv *.flv *.ts *.mts "
    "*.mp3 *.wav *.m4a *.aac *.flac *.ogg *.opus *.wma"
)


class Dialogs(Protocol):
    def open_recording(self) -> Path | None: ...

    def save_transcript_as(self, suggested: Path) -> Path | None: ...


class NativeDialogs:
    def open_recording(self) -> Path | None:
        return _run_dialog("open")

    def save_transcript_as(self, suggested: Path) -> Path | None:
        return _run_dialog("save", str(suggested))


def _run_dialog(*args: str) -> Path | None:
    result = subprocess.run(
        [sys.executable, "-m", "transcriber.dialogs", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"The file dialog failed: {result.stderr.strip()}")
    chosen = result.stdout.strip()
    return Path(chosen) if chosen else None


def _main(argv: list[str]) -> None:
    import tkinter
    from tkinter import filedialog

    root = tkinter.Tk()
    root.withdraw()
    # Bring the dialog in front of the browser window that asked for it.
    root.attributes("-topmost", True)
    root.lift()
    root.focus_force()

    command = argv[0]
    chosen = ""
    if command == "open":
        chosen = filedialog.askopenfilename(
            parent=root,
            title="Choose a recording",
            filetypes=[("Video and audio", MEDIA_EXTENSIONS), ("All files", "*.*")],
        )
    elif command == "save":
        suggested = Path(argv[1])
        chosen = filedialog.asksaveasfilename(
            parent=root,
            title="Save transcript as",
            initialdir=str(suggested.parent),
            initialfile=suggested.name,
            defaultextension=".txt",
            filetypes=[("Text", "*.txt"), ("All files", "*.*")],
        )
    root.destroy()
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    print(chosen or "")


if __name__ == "__main__":
    _main(sys.argv[1:])
