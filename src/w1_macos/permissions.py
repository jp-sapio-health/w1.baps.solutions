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


# System Settings deep links. Opening a pane is a plain navigation action (no security change);
# it just puts the user one click from the toggle W1 cannot flip on their behalf.
_PANE_INPUT_MONITORING = (
    "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent"
)
_PANE_ACCESSIBILITY = (
    "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
)


def open_settings_pane(which: str) -> None:
    """Open the Input Monitoring or Accessibility pane in System Settings."""
    import subprocess

    url = _PANE_INPUT_MONITORING if which == "input_monitoring" else _PANE_ACCESSIBILITY
    try:
        subprocess.Popen(["/usr/bin/open", url])
    except Exception:
        pass


def permission_status() -> dict:
    """Current grants without side effects: {'input_monitoring': ..., 'accessibility': ...}."""
    return {
        "input_monitoring": input_monitoring_status(),
        "accessibility": accessibility_status(prompt=False),
    }


def request_missing_once() -> dict:
    """Fire the OS grant prompt for each missing permission EXACTLY once per process.

    The hotkey needs BOTH Accessibility and, on recent macOS, Input Monitoring for pynput's
    listen-only key tap. IOHIDRequestAccess only shows a dialog the first time an app is seen;
    AXIsProcessTrustedWithOptions(prompt=True) would re-nag on every launch, so the caller must
    invoke this at most once. Returns the post-request status dict.
    """
    im = input_monitoring_status()
    if im != "granted":
        request_input_monitoring()
        im = input_monitoring_status()
    ax = accessibility_status(prompt=False)
    if ax != "granted":
        accessibility_status(prompt=True)
        ax = accessibility_status(prompt=False)
    return {"input_monitoring": im, "accessibility": ax}
