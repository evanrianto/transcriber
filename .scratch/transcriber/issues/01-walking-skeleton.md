# 01: Walking skeleton: path → Transcript → .txt

**What to build:** The thinnest end-to-end path. A user runs `make install` once, then `make run`, which starts the server on `localhost` and opens the browser. On the single page they paste the path of a Recording on disk and start a Job. The page shows "Transcribing…", then the finished Transcript as one `[hh:mm:ss] text` line per Segment. When the Job finishes, the Transcript is also written as a `.txt` next to the Recording. For now, Language Mode is fixed to English and only an NVIDIA GPU is supported. This ticket also sets the page's clean, minimal visual design so every later ticket builds on it. See ADR-0001 for why Recordings are read by path instead of uploaded.

**Blocked by:** None (can start immediately).

**Status:** done

- [x] `make install` installs `uv`, a pinned Python 3.12, all dependencies (including the CUDA libraries for `faster-whisper` on Windows/Linux), and downloads the `large-v3` model so the first run doesn't
- [x] `make run` starts the server bound to `localhost` only (never a network interface) and opens the default browser to the app
- [x] Pasting a valid path to a video or audio file and starting a Job produces a Transcript using `faster-whisper` `large-v3` on the GPU, with the voice detector (VAD) enabled to skip silence
- [x] The Transcript renders on the page as one line per Segment: `[hh:mm:ss] text` (start time only)
- [x] When the Job finishes, the Transcript is written next to the Recording as `<name>.transcript.<YYYY-MM-DD_HH-MM-SS>.txt` in the same `[hh:mm:ss] text` format. Every run gets its own file and none are overwritten
- [x] An invalid or missing path shows a clear error instead of starting a Job
- [x] The page has a clean single-page layout: neutral palette, one accent color, system font, generous whitespace, following the OS light/dark theme
- [x] The repo has a `.gitignore` covering the virtualenv, model cache, and temp files
- [x] Automated tests cover the Transcript file naming and the `[hh:mm:ss] text` formatting
