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
        "w1 transcribes your speech entirely on this Mac. Audio never leaves your computer."
    ),
    "NSHumanReadableCopyright": "Built for sewa. Private by design.",
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
    setup_requires=["py2app"],
)
