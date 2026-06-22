"""Detect whether the focused UI element can accept pasted text (macOS Accessibility).

Used to decide between two injection strategies: paste straight into the focused field, or —
when nothing editable is focused — float a paste panel and let the user place the text with a
global hotkey.

Reliability note: AX focus reporting varies across apps, and the API is disabled without the
Accessibility permission. So the contract is deliberately conservative — ``editable_target()``
returns ``False`` (→ show the panel) ONLY when AX positively reports a non-editable focused
element. Any error, missing permission, or ambiguity returns ``True`` so we fall back to the
normal, reliable paste path rather than popping the panel spuriously.
"""
from __future__ import annotations

# Roles that accept typed/pasted text.
_EDITABLE_ROLES = {
    "AXTextField",
    "AXTextArea",
    "AXComboBox",
    "AXSearchField",
    "AXSecureTextField",
}


def editable_target() -> bool:
    """True if it's safe to paste into the focused element (or if focus can't be determined)."""
    try:
        from ApplicationServices import (
            AXUIElementCopyAttributeValue,
            AXUIElementCreateSystemWide,
            kAXFocusedUIElementAttribute,
            kAXRoleAttribute,
        )
    except Exception:
        return True  # AX unavailable -> use the dependable paste path

    try:
        system = AXUIElementCreateSystemWide()
        err, focused = AXUIElementCopyAttributeValue(
            system, kAXFocusedUIElementAttribute, None
        )
        if err != 0 or focused is None:
            return True  # no readable focus (or permission off) -> paste path

        role_err, role = AXUIElementCopyAttributeValue(focused, kAXRoleAttribute, None)
        if role_err != 0 or not role:
            return True  # element exists but role unreadable -> don't guess, paste

        if str(role) in _EDITABLE_ROLES:
            return True

        # Some custom/web inputs aren't standard roles but still expose a settable value.
        try:
            from ApplicationServices import (
                AXUIElementIsAttributeSettable,
                kAXValueAttribute,
            )

            set_err, settable = AXUIElementIsAttributeSettable(
                focused, kAXValueAttribute, None
            )
            if set_err == 0 and settable:
                return True
        except Exception:
            pass

        return False  # AX positively reports a non-editable focused element
    except Exception:
        return True  # any AX failure -> safe fallback to the paste path
