# 07: Preview for videos the browser can't play

**What to build:** Recordings the browser can't play (e.g. many MKV/AVI files, HEVC `.mov`) still get the full result player. When a Job starts, the app detects that the Recording isn't playable and, at the same time as transcription, converts a temporary 720p preview. On NVIDIA it uses the GPU's video encoder, and elsewhere a fast CPU encode. The Transcript shows as soon as it's ready. The player shows "Preparing preview… NN%" until the preview finishes, then works like the player in 06. Nothing but the `.txt` is ever written next to the Recording.

**Blocked by:** 06 (Result player for playable videos)

**Status:** ready-for-agent

- [ ] `make install` installs a full ffmpeg through pip, so no platform needs a manual ffmpeg install
- [ ] The app decides from the Recording's container and codec whether it's browser-playable. Playable Recordings are never converted
- [ ] For non-playable Recordings, a 720p, modest-bitrate preview is produced at the same time as transcription, using NVENC when available and a fast CPU encoder otherwise
- [ ] The result screen shows the Transcript immediately and a "Preparing preview… NN%" placeholder until the preview is ready, then the working player with click-to-seek
- [ ] Previews live in a temp location that is cleared when the next Job starts and when the app stops. Cancelling a Job also stops and discards its preview
- [ ] If preview conversion fails, the Transcript is unaffected and the player area shows a short "preview unavailable" note
