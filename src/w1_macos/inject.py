"""Insert text into the focused app via clipboard paste, preserving the user's clipboard.

Paste (rather than synthetic typing) is the only reliable way to emit Gujarati Unicode into
arbitrary apps. We snapshot the existing clipboard, paste, then restore it after a short delay
(synchronous restore races the paste — the app may not have read the pasteboard yet).
"""
from __future__ import annotations

import threading
import time

import pyperclip
from pynput.keyboard import Controller, Key

_keyboard = Controller()


def paste_and_restore(text: str, *, settle: float = 0.04, restore_delay: float = 0.6) -> None:
    if not text:
        return
    try:
        previous = pyperclip.paste()
    except Exception:
        previous = ""

    pyperclip.copy(text)
    time.sleep(settle)  # let the pasteboard settle before the paste keystroke
    with _keyboard.pressed(Key.cmd):
        _keyboard.press("v")
        _keyboard.release("v")

    def _restore() -> None:
        try:
            pyperclip.copy(previous)
        except Exception:
            pass

    threading.Timer(restore_delay, _restore).start()
