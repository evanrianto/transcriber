"""Make the pip-installed NVIDIA libraries (cuBLAS, cuDNN) findable by CTranslate2.

The `nvidia-*-cu12` wheels put the CUDA libraries inside site-packages, where neither the
Windows DLL loader nor the Linux dynamic linker looks by default. This must run before
faster-whisper loads a model on the GPU.
"""

from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path

_LIBRARIES = ("cublas", "cudnn", "cuda_nvrtc")


def _library_dirs(subdir: str) -> list[Path]:
    try:
        import nvidia
    except ImportError:
        return []
    dirs = []
    for base in nvidia.__path__:
        for name in _LIBRARIES:
            candidate = Path(base) / name / subdir
            if candidate.is_dir():
                dirs.append(candidate)
    return dirs


def register_cuda_libraries() -> None:
    if sys.platform == "win32":
        for directory in _library_dirs("bin"):
            os.add_dll_directory(str(directory))
            os.environ["PATH"] = f"{directory}{os.pathsep}{os.environ.get('PATH', '')}"
    elif sys.platform.startswith("linux"):
        # Preload with RTLD_GLOBAL so later dlopen() calls by soname resolve to these.
        # Libraries can depend on each other, so retry until no more progress is made.
        pending = [lib for d in _library_dirs("lib") for lib in sorted(d.glob("lib*.so*"))]
        while pending:
            failed = []
            for lib in pending:
                try:
                    ctypes.CDLL(str(lib), mode=ctypes.RTLD_GLOBAL)
                except OSError:
                    failed.append(lib)
            if len(failed) == len(pending):
                break
            pending = failed
