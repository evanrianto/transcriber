# Transcriber

A small web app that runs on your own computer and turns a video or audio file into a timestamped text transcript, in English, Indonesian, or a mix of both.

- Pick a file, choose its language, and watch the transcript appear live.
- The transcript is saved as a `.txt` next to the video: `meeting.transcript.2026-10-12_14-30-05.txt`, one `[hh:mm:ss] text` line per segment.
- Review it beside the video: click a timestamp to jump there.
- Everything stays on your machine. Speech recognition is [Whisper large-v3](https://github.com/SYSTRAN/faster-whisper), run locally, with no cloud services or uploads.

## Requirements

- Windows, macOS, or Linux
- About 5 GB of free disk space (the model is ~3 GB)
- `make` (see below). Everything else, including Python, is installed by `make install`.
- **Recommended:** an NVIDIA GPU. Without one the app still works, on the CPU, but much slower:

  | Hardware | An hour of video takes roughly |
  | --- | --- |
  | NVIDIA GPU (e.g. RTX 4070) | 2–3 minutes (English/Indonesian), ~15 minutes (Mixed) |
  | CPU only (incl. all Macs) | an hour or more (English/Indonesian); Mixed is several times slower still |

## Install

### 1. Install `make`

**Windows** (PowerShell):

```powershell
winget install ezwinports.make
```

Then open a new terminal so `make` is on your PATH.

**macOS**:

```sh
xcode-select --install
```

**Linux** (Debian/Ubuntu; use your distro's package manager otherwise):

```sh
sudo apt install make curl
```

### 2. Install the app

From this folder:

```sh
make install
```

`make install` detects your OS. You can also name it explicitly:

| OS | Command | Transcribes on |
| --- | --- | --- |
| Windows | `make install-windows` | NVIDIA GPU if present, otherwise CPU |
| macOS | `make install-macos` | CPU |
| Linux | `make install-linux` | NVIDIA GPU if present, otherwise CPU |

At the end it tells you whether transcription will run on the GPU or the CPU. `make help` lists all the commands.

This installs [uv](https://docs.astral.sh/uv/) if you don't have it, then Python 3.12, the dependencies (including the NVIDIA CUDA libraries on Windows and Linux, and ffmpeg), and downloads the Whisper model. The first run takes a while: there are about 4 GB to download.

You don't need to install CUDA or ffmpeg yourself; they come from Python packages.

## Run

```sh
make run
```

The app starts and opens in your browser at <http://localhost:8765>. Press `Ctrl+C` in the terminal to stop it.

If port 8765 is taken, run `uv run transcriber --port 8800` instead (any free port).

## Using it

1. **Choose file…** opens your system's file dialog, or paste a path into the box. Paths copied with Windows' "Copy as path" (with quotes) work too.
2. Pick the **Language**:
   - **English** or **Indonesian** when the whole recording is in one language.
   - **Mixed** for Indonesian with English words and phrases inside the same sentences. It's slower (see the table above) because it guides Whisper to keep English words as spoken.
3. **Transcribe.** You can watch the progress, read segments as they appear, or cancel. Refreshing the page reconnects to the running job.
4. When it's done, the transcript is saved next to the video and shown beside a player. Click any timestamp to jump there.

Videos the browser can't play directly (for example MKV, AVI, or iPhone HEVC `.mov` files) get a temporary 720p preview made alongside the transcription. It's deleted when you start the next file or stop the app; nothing but the `.txt` is ever written next to your video.

If the video's folder is read-only, the transcript is still shown, with **Copy** and **Save as…** to keep it.

## Privacy and safety

The app only listens on `localhost`, never on your network. That matters because it reads files directly from your disk by path instead of uploading them (see [ADR-0001](docs/adr/0001-import-recordings-by-path.md)). Don't change it to listen on other interfaces.

It also refuses requests made by other websites open in your browser, so a malicious page can't use it to start transcriptions or read your files. Open it as `localhost` or `127.0.0.1`; other host names are refused.

## Development

```sh
make test        # fast tests (no GPU or model needed)
make test-slow   # also runs the real Whisper model and ffmpeg
make typecheck   # mypy
```

Domain language is in [CONTEXT.md](CONTEXT.md); design decisions are in [docs/adr](docs/adr).

## Troubleshooting

- **"No NVIDIA GPU is available" banner although you have one:** the app checks the GPU when it starts and falls back to the CPU if CUDA doesn't work. Update your NVIDIA driver and restart the app.
- **The file dialog doesn't appear:** it may have opened behind the browser window. Check the taskbar, or paste the path instead.
- **`make: command not found` on Windows right after installing:** open a new terminal.
- **"Requests from other sites are refused":** open the app at <http://localhost:8765> rather than through another host name or proxy.

## License

[MIT](LICENSE)
