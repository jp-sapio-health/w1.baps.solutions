"""w1_macos — the macOS platform adapter.

ALL desktop dependencies (rumps, pynput, sounddevice, pyperclip) live ONLY in this package.
It wires OS events to the single ``w1_core`` pipeline entrypoint.
"""
