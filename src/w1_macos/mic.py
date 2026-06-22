"""Microphone capture for the macOS adapter. Records 16 kHz mono float32 for the core.

Lives in the platform layer (uses sounddevice) — never imported by w1_core.
"""
from __future__ import annotations

import queue
import sys

import numpy as np
import sounddevice as sd

from w1_core.audio.types import CHANNELS, SAMPLE_RATE


def record_until_enter() -> np.ndarray:
    """Record from the default mic until the user presses Enter. Returns float32 mono."""
    frames: "queue.Queue[np.ndarray]" = queue.Queue()

    def _callback(indata, _frames, _time, status):  # pragma: no cover - realtime callback
        if status:
            print(f"[mic] {status}", file=sys.stderr)
        frames.put(indata.copy())

    print("🎙  Recording… press Enter to stop.", file=sys.stderr)
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="float32", callback=_callback):
        input()

    chunks = []
    while not frames.empty():
        chunks.append(frames.get())
    if not chunks:
        return np.zeros(0, dtype="float32")
    return np.concatenate(chunks, axis=0).reshape(-1)


def record_seconds(seconds: float) -> np.ndarray:
    """Record a fixed duration (useful for scripted tests)."""
    print(f"🎙  Recording {seconds:.1f}s…", file=sys.stderr)
    audio = sd.rec(int(seconds * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="float32")
    sd.wait()
    return audio.reshape(-1)
