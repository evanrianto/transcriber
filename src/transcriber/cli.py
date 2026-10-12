"""`transcriber`: start the app on localhost and open it in the browser."""

from __future__ import annotations

import argparse
import socket
import sys
import threading
import time
import webbrowser

import uvicorn

from transcriber.app import create_app
from transcriber.cuda_libs import register_cuda_libraries
from transcriber.dialogs import NativeDialogs
from transcriber.engine import WhisperEngine
from transcriber.jobs import JobManager
from transcriber.previews import FfmpegPreviewer, remove_stale_preview_dirs

# Localhost only: the server reads files by path, so it must never be reachable from
# the network. See docs/adr/0001-import-recordings-by-path.md.
HOST = "127.0.0.1"
DEFAULT_PORT = 8765


def port_is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex((HOST, port)) != 0


def open_browser_when_ready(server: uvicorn.Server, url: str) -> None:
    def wait_then_open() -> None:
        while not server.started:
            time.sleep(0.1)
        print(f"Transcriber is running at {url}  (press Ctrl+C to stop)")
        webbrowser.open(url)

    threading.Thread(target=wait_then_open, daemon=True).start()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Transcriber web app.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-browser", action="store_true", help="don't open a browser tab")
    args = parser.parse_args()

    url = f"http://localhost:{args.port}"
    if not port_is_free(args.port):
        print(f"Port {args.port} is already in use. Is Transcriber already running at {url}?")
        print("Use `uv run transcriber --port <number>` to pick another port.")
        sys.exit(1)

    remove_stale_preview_dirs()  # only one app runs at a time (the port check above)
    register_cuda_libraries()
    engine = WhisperEngine()
    engine.preload()
    manager = JobManager(engine, previewer=FfmpegPreviewer())

    app = create_app(manager, dialogs=NativeDialogs(), device=lambda: engine.device.name)
    config = uvicorn.Config(app, host=HOST, port=args.port, log_level="warning")
    server = uvicorn.Server(config)
    if not args.no_browser:
        open_browser_when_ready(server, url)
    else:
        print(f"Transcriber is running at {url}")
    try:
        server.run()
    finally:
        manager.close()  # stops any conversion and deletes temporary previews


if __name__ == "__main__":
    main()
