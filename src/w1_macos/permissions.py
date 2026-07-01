"""Check and request the macOS permissions the hotkey and paste paths need.

pynput never asks macOS for Input Monitoring or Accessibility; it just creates an event tap
that silently receives nothing when the grant is missing. Worse, TCC keys grants to the code
signature, so a grant made against an earlier (ad hoc) build stops matching a re-signed bundle
and macOS drops events without re-prompting. Calling the request APIs at startup makes macOS
show its own prompt and register the correct identity in System Settings.

IOHIDRequestAccess lives in IOKit and has no PyObjC wrapper, so it is loaded via ctypes.
"""
from __future__ import annotations

import ctypes

_KIOHID_REQUEST_LISTEN = 1  # kIOHIDRequestTypeListenEvent


def _iokit():
    lib = ctypes.CDLL("/System/Library/Frameworks/IOKit.framework/IOKit")
    lib.IOHIDCheckAccess.restype = ctypes.c_int
    lib.IOHIDCheckAccess.argtypes = [ctypes.c_int]
    lib.IOHIDRequestAccess.restype = ctypes.c_bool
    lib.IOHIDRequestAccess.argtypes = [ctypes.c_int]
    return lib


def input_monitoring_status() -> str:
    """'granted' | 'denied' | 'undetermined' | 'unknown' for the current process."""
    try:
        code = _iokit().IOHIDCheckAccess(_KIOHID_REQUEST_LISTEN)
        return {0: "granted", 1: "denied", 2: "undetermined"}.get(code, "unknown")
    except Exception:
        return "unknown"


def request_input_monitoring() -> bool:
    """Trigger the system Input Monitoring prompt (or return True if already granted)."""
    try:
        return bool(_iokit().IOHIDRequestAccess(_KIOHID_REQUEST_LISTEN))
    except Exception:
        return False


def accessibility_status(prompt: bool = False) -> str:
    """'granted' | 'denied' | 'unknown'. With prompt=True macOS shows its own dialog."""
    try:
        if prompt:
            from ApplicationServices import (
                AXIsProcessTrustedWithOptions,
                kAXTrustedCheckOptionPrompt,
            )

            ok = AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: True})
        else:
            from ApplicationServices import AXIsProcessTrusted

            ok = AXIsProcessTrusted()
        return "granted" if ok else "denied"
    except Exception:
        return "unknown"


def ensure_permissions() -> dict:
    """Startup check: request anything missing so macOS registers this exact binary.

    Returns {"input_monitoring": status, "accessibility": status} AFTER the requests, so the
    caller can tell the user what still needs a manual toggle (a denied grant only prompts
    once; after that the user must flip it in System Settings).
    """
    im = input_monitoring_status()
    if im != "granted":
        request_input_monitoring()  # shows the system prompt / registers the app row
        im = input_monitoring_status()
    ax = accessibility_status(prompt=False)
    if ax != "granted":
        accessibility_status(prompt=True)
        ax = accessibility_status(prompt=False)
    return {"input_monitoring": im, "accessibility": ax}
