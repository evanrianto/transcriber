# 09: Cross-platform: CPU fallback, README, LICENSE

**What to build:** Make the project usable by other people on other machines. Without an NVIDIA GPU (macOS, AMD, or CPU-only machines), the app transcribes on the CPU automatically and warns clearly up front that it will be slow. A README walks a new user through setup on Windows, macOS, and Linux, from installing `make` to `make install` and `make run`. The repo gets an MIT license.

**Blocked by:** 01 (Walking skeleton)

**Status:** done

- [x] With no usable CUDA device (or if CUDA fails to initialize), the app falls back to CPU (int8) automatically instead of crashing
- [x] On CPU, the UI shows a persistent, clear warning before and during a Job that transcription will be much slower (measured ~1.2x real time on a Ryzen 5 5600X, so about an hour or more per hour of Recording)
- [ ] `make install` succeeds on Windows, macOS, and Linux, installing the CUDA libraries only where they apply
- [x] The README covers, per platform: installing `make` (Windows: `winget install ezwinports.make`; macOS: Xcode Command Line Tools; Linux: the distro's package manager), then `make install` and `make run`, the ~3 GB model download, and GPU vs CPU expectations
- [x] The README states that the app only listens on `localhost` and why (ADR-0001)
- [x] An MIT `LICENSE` file is added

## Comments

CPU fallback verified on Windows both with the GPU hidden (`CUDA_VISIBLE_DEVICES=-1`) and with the CUDA libraries missing (the warm-up at model load catches the lazy cuBLAS failure). `make install` was only run on Windows; macOS and the Linux CUDA-library preloading are untested.
