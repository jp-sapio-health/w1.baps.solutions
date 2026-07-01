"""Orchestrates a dictation cycle: hotkey -> mic capture -> pipeline -> paste, with state.

Recording runs on the audio callback thread; transcription runs on a worker thread so the
hotkey/UI never block. State changes are pushed out via ``on_state`` (the app marshals UI work
to the main thread). The Whisper backend is warmed up once so the first dictation isn't slow.
"""
from __future__ import annotations

import threading
from typing import Callable

import numpy as np

from w1_core.audio.types import CHANNELS, SAMPLE_RATE
from w1_core.config import CorrectionMode, W1Config
from w1_core.pipeline import transcribe_and_correct

_MIN_SAMPLES = 1600  # ~0.1s — ignore accidental taps
_LEVELS = 12         # number of amplitude frames the widget exposes
_LEVEL_GAIN = 165.0  # maps speech RMS (~0.02–0.08) across the 0..LEVELS-1 range


def _default_paste(text: str) -> None:
    from w1_macos.inject import paste_and_restore

    paste_and_restore(text)


class Controller:
    def __init__(
        self,
        config: W1Config | None = None,
        on_state: Callable[[str], None] | None = None,
        on_level: Callable[[int], None] | None = None,
        on_result: Callable[[str], None] | None = None,
    ):
        self.config = config or W1Config()
        self._on_state = on_state or (lambda s: None)
        self._on_level = on_level or (lambda lvl: None)
        # Injection strategy. Default = paste into the focused app; the macOS app overrides this
        # to add the no-editable-field floating panel path.
        self._on_result = on_result or _default_paste
        self._state = "idle"
        self._stream = None
        self._frames: list = []
        self._backend = None
        self._lock = threading.Lock()

    # -- lifecycle ------------------------------------------------------------
    def warm_up(self) -> None:
        def _load():
            try:
                from w1_core.backends.factory import select_backend

                self._backend = select_backend(self.config)
            except Exception as exc:  # pragma: no cover - environment dependent
                print(f"[w1] backend warm-up failed: {exc}")

        threading.Thread(target=_load, daemon=True).start()

    def _set_state(self, state: str) -> None:
        self._state = state
        self._on_state(state)

    # -- recording ------------------------------------------------------------
    def start_recording(self) -> None:
        # This runs on the pynput callback thread: an uncaught exception here dies silently
        # and the app just looks unresponsive. Import failures (e.g. portaudio missing from a
        # bad bundle) must be logged, not swallowed.
        try:
            import sounddevice as sd
        except Exception as exc:
            print(f"[w1] audio stack unavailable, cannot record: {exc}")
            return

        with self._lock:
            if self._state != "idle":
                return
            self._frames = []

            def _callback(indata, frames, time_info, status):  # pragma: no cover - realtime
                self._frames.append(indata.copy())
                # Push a live amplitude level to the widget so the waveform reacts in real time.
                rms = float(np.sqrt(np.mean(np.square(indata)))) if indata.size else 0.0
                level = int(min(_LEVELS - 1, max(0, round(rms * _LEVEL_GAIN))))
                self._on_level(level)

            try:
                self._stream = sd.InputStream(
                    samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="float32", callback=_callback
                )
                self._stream.start()
            except Exception as exc:
                print(f"[w1] could not open microphone: {exc}")
                self._set_state("idle")
                return
            self._set_state("listening")

    def stop_recording(self) -> None:

        with self._lock:
            if self._state != "listening":
                return
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
            audio = (
                np.concatenate(self._frames).reshape(-1)
                if self._frames
                else np.zeros(0, dtype="float32")
            )
            self._frames = []
            self._set_state("processing")

        threading.Thread(target=self._process, args=(audio,), daemon=True).start()

    def _process(self, audio) -> None:
        try:
            if audio.size < _MIN_SAMPLES:
                self._set_state("idle")
                return
            result = transcribe_and_correct(audio, self.config, backend=self._backend)
            if result.gated:
                self._reject()  # nothing trustworthy to paste — show the ✕ cue
            elif result.text:
                self._on_result(result.text)
                self._set_state("idle")
            else:
                self._set_state("idle")
        except Exception as exc:  # pragma: no cover - environment dependent
            print(f"[w1] transcription error: {exc}")
            self._set_state("idle")

    def _reject(self) -> None:
        """Emit a transient reject cue without trapping the state machine.

        The widget plays the red ✕ and collapses itself back to rest, so the controller's own
        state returns to ``idle`` immediately and the next hotkey press works.
        """
        self._state = "idle"
        self._on_state("rejected")

    # -- config ---------------------------------------------------------------
    def set_mode(self, mode: str) -> None:
        self.config.correction_mode = CorrectionMode(mode)
