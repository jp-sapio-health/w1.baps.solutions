"""Global hotkey listener. Two modes, switchable in config:

* push_to_talk — hold the key to talk, release to insert (default; conflict-free since you're
  speaking, not typing, while it's held).
* toggle — double-tap the key to start, double-tap again to stop (double-tap, not single, so an
  ordinary Right-Option keypress during typing never triggers it).

Default key: Right-Option (``<alt_r>``). Never Cmd+M.
"""
from __future__ import annotations

import time
from typing import Callable

from pynput import keyboard
from pynput.keyboard import Key

_KEY_ALIASES = {
    "<alt_r>": Key.alt_r,
    "<alt_l>": Key.alt_l,
    "<cmd_r>": Key.cmd_r,
    "<ctrl_r>": Key.ctrl_r,
    "<fn>": getattr(Key, "fn", Key.alt_r),
}


class HotkeyListener:
    def __init__(
        self,
        *,
        on_start: Callable[[], None],
        on_stop: Callable[[], None],
        mode: str = "push_to_talk",
        key: str = "<alt_r>",
        double_tap_window: float = 0.4,
    ):
        self._on_start = on_start
        self._on_stop = on_stop
        self._mode = mode
        self._key = _KEY_ALIASES.get(key, Key.alt_r)
        self._window = double_tap_window
        self._held = False
        self._toggled_on = False
        self._last_press = 0.0
        self._listener: keyboard.Listener | None = None

    def _on_press(self, k) -> None:
        if k != self._key:
            return
        if self._mode == "push_to_talk":
            if not self._held:
                self._held = True
                self._on_start()
        else:  # toggle via double-tap
            now = time.monotonic()
            if now - self._last_press <= self._window:
                self._toggled_on = not self._toggled_on
                (self._on_start if self._toggled_on else self._on_stop)()
                self._last_press = 0.0
            else:
                self._last_press = now

    def _on_release(self, k) -> None:
        if k != self._key:
            return
        if self._mode == "push_to_talk" and self._held:
            self._held = False
            self._on_stop()

    def start(self) -> None:
        self._listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
