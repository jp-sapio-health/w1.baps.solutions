"""py2app build recipe for the w1 menu-bar app.

    # from the repo root, in the project venv with py2app installed:
    python packaging/setup_app.py py2app

Produces ``dist/w1.app`` — a menu-bar-only (LSUIElement) bundle. The Whisper model is NOT
bundled; it downloads on first run to the user's Hugging Face cache (keeps the app small and
avoids redistributing model weights). See docs/PACKAGING.md for signing/notarization.
"""
from __future__ import annotations

import sys
from pathlib import Path

from setuptools import setup

# py2app's modulegraph recurses deeply; large transitive trees (torch) overflow the default
# limit. Raise it before the graph walk.
sys.setrecursionlimit(10000)

# Workaround for uv/python-build-standalone + py2app: this CPython statically links zlib (it is a
# builtin — no .so, no __file__). py2app's build_executable unconditionally runs
# copy_file(zlib.__file__, ...) to seed the bootstrap that unzips site-packages, and crashes with
# "module 'zlib' has no attribute '__file__'". The bundled interpreter also has zlib builtin, so
# the copy is vestigial; point __file__ at any real extension .so (a valid Mach-O, so later strip/
# codesign succeed) and it is simply never loaded.
import sysconfig as _sysconfig
import zlib as _zlib

if not getattr(_zlib, "__file__", None):
    _dynload = Path(_sysconfig.get_config_var("DESTSHARED") or "")
    _real_so = next(iter(sorted(_dynload.glob("*.so"))), None) if _dynload.is_dir() else None
    if _real_so is not None:
        _zlib.__file__ = str(_real_so)
    else:
        raise SystemExit("py2app workaround: no extension .so found to stand in for builtin zlib")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# torch is an mlx-whisper *weight-conversion* dependency only (torch_whisper.py); MLX inference
# on the pre-converted model never imports it. Excluding it keeps the bundle small and avoids a
# 387 MB recursive graph. The other excludes are dev/build noise never needed at runtime.
EXCLUDES = [
    "torch", "torchvision", "torchaudio",
    "tensorflow", "numba", "llvmlite",
    "pytest", "import_linter", "py2app",
    "tkinter", "matplotlib", "IPython",
]

APP = [str(ROOT / "packaging" / "app_main.py")]

PLIST = {
    "CFBundleName": "W1",
    "CFBundleDisplayName": "W1",
    "CFBundleIdentifier": "health.baps.w1",
    "CFBundleVersion": "1.1.0",
    "CFBundleShortVersionString": "1.1.0",
    "LSUIElement": True,  # menu-bar only — no Dock icon
    "LSMinimumSystemVersion": "13.0",
    "NSMicrophoneUsageDescription": (
        "W1 transcribes your speech entirely on this Mac. Audio never leaves your computer."
    ),
    # Never write .pyc into the signed bundle at runtime; the first launch would otherwise
    # add files under Contents/Resources and break the codesign seal (and with it the TCC
    # grants tied to the signature).
    "LSEnvironment": {"PYTHONDONTWRITEBYTECODE": "1"},
}

OPTIONS = {
    "argv_emulation": False,  # breaks pynput/AppKit event handling — keep off
    "plist": PLIST,
    "packages": ["w1_core", "w1_data", "w1_macos", "rumps", "pynput", "sounddevice"],
    # mlx_whisper + mlx are large and dlopen Metal libs; include only if bundling the backend.
    "includes": ["pyperclip"],
    "excludes": EXCLUDES,
    "iconfile": str(ROOT / "assets" / "menubar" / "idle.png"),
    "resources": [str(ROOT / "assets")],
}

setup(
    app=APP,
    name="w1",
    options={"py2app": OPTIONS},
    # NB: no setup_requires — setuptools 80+ rejects the legacy keyword and py2app is already
    # installed via the build extra. The build venv also pins setuptools < 80 (see build.sh).
)
