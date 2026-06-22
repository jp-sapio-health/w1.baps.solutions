"""A floating panel for dictation with no editable field focused.

When the controller produces text but nothing editable is focused, the text would otherwise be
lost. Instead this panel floats above the widget showing the result, with the footer
"⌘⇧V to paste into intended box". A global ⌘⇧V (armed only while the panel is visible) pastes
the held text into whatever the user clicks into, then dismisses the panel.

Separate from the waveform widget on purpose: the widget is the pill, this is a transient
text surface. Every failure path falls back to pasting immediately so text is never dropped.
"""
from __future__ import annotations

from AppKit import (
    NSColor,
    NSFont,
    NSPanel,
    NSScreen,
    NSTextField,
    NSView,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorStationary,
    NSWindowStyleMaskBorderless,
    NSWindowStyleMaskNonactivatingPanel,
)
from PyObjCTools import AppHelper

from w1_macos.inject import paste_and_restore

try:
    from AppKit import (
        NSVisualEffectBlendingModeBehindWindow,
        NSVisualEffectMaterialHUDWindow,
        NSVisualEffectStateActive,
        NSVisualEffectView,
    )

    _HAS_GLASS = True
except Exception:  # pragma: no cover
    _HAS_GLASS = False

_SCREENSAVER_LEVEL = 1000
_NSBackingStoreBuffered = 2
_WIDTH, _HEIGHT = 360.0, 96.0
_PAD = 16.0
_FOOTER = "⌘⇧V to paste into intended box"


class PastePanel:
    def __init__(self) -> None:
        self._text = ""
        self._panel = None
        self._body = None
        self._hotkey = None
        try:
            self._build()
        except Exception as exc:  # pragma: no cover - environment dependent
            print(f"[w1] paste panel unavailable: {exc}")
            self._panel = None

    def _build(self) -> None:
        screen = NSScreen.mainScreen().frame()
        cx = screen.size.width / 2.0
        y = 150.0  # above the widget (which sits at ~96)
        rect = ((cx - _WIDTH / 2.0, y), (_WIDTH, _HEIGHT))
        style = NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel

        panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, style, _NSBackingStoreBuffered, False
        )
        panel.setLevel_(_SCREENSAVER_LEVEL)
        panel.setOpaque_(False)
        panel.setBackgroundColor_(NSColor.clearColor())
        panel.setHasShadow_(True)
        panel.setIgnoresMouseEvents_(True)
        panel.setReleasedWhenClosed_(False)
        panel.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces | NSWindowCollectionBehaviorStationary
        )

        container = NSView.alloc().initWithFrame_(((0, 0), (_WIDTH, _HEIGHT)))
        if _HAS_GLASS:
            fx = NSVisualEffectView.alloc().initWithFrame_(((0, 0), (_WIDTH, _HEIGHT)))
            fx.setMaterial_(NSVisualEffectMaterialHUDWindow)
            fx.setBlendingMode_(NSVisualEffectBlendingModeBehindWindow)
            fx.setState_(NSVisualEffectStateActive)
            fx.setWantsLayer_(True)
            fx.layer().setCornerRadius_(14.0)
            fx.layer().setMasksToBounds_(True)
            container = fx

        body = self._label(
            (( _PAD, 34), (_WIDTH - 2 * _PAD, _HEIGHT - 44)),
            NSFont.systemFontOfSize_(15.0),
            NSColor.whiteColor(),
        )
        footer = self._label(
            (( _PAD, 12), (_WIDTH - 2 * _PAD, 18)),
            NSFont.systemFontOfSize_(11.0),
            NSColor.colorWithCalibratedWhite_alpha_(1.0, 0.55),
        )
        footer.setStringValue_(_FOOTER)

        container.addSubview_(body)
        container.addSubview_(footer)
        panel.setContentView_(container)
        self._panel, self._body = panel, body

    @staticmethod
    def _label(frame, font, color):
        f = NSTextField.alloc().initWithFrame_(frame)
        f.setBezeled_(False)
        f.setDrawsBackground_(False)
        f.setEditable_(False)
        f.setSelectable_(False)
        f.setFont_(font)
        f.setTextColor_(color)
        f.setStringValue_("")
        return f

    # -- public API -----------------------------------------------------------
    def present(self, text: str) -> None:
        """Show the held text and arm the global ⌘⇧V. Falls back to a direct paste on failure."""
        if not text:
            return
        if self._panel is None:
            paste_and_restore(text)  # no panel -> never drop the text
            return

        def _do() -> None:
            try:
                self._text = text
                self._body.setStringValue_(text)
                self._panel.orderFrontRegardless()
                self._arm()
            except Exception as exc:  # pragma: no cover
                print(f"[w1] paste panel present failed: {exc}")
                paste_and_restore(text)

        AppHelper.callAfter(_do)

    def dismiss(self) -> None:
        def _do() -> None:
            self._disarm()
            if self._panel is not None:
                self._panel.orderOut_(None)

        AppHelper.callAfter(_do)

    # -- global hotkey --------------------------------------------------------
    def _arm(self) -> None:
        if self._hotkey is not None:
            return
        try:
            from pynput import keyboard

            self._hotkey = keyboard.GlobalHotKeys({"<cmd>+<shift>+v": self._on_hotkey})
            self._hotkey.start()
        except Exception as exc:  # pragma: no cover
            print(f"[w1] could not arm ⌘⇧V: {exc}")
            self._hotkey = None

    def _disarm(self) -> None:
        if self._hotkey is not None:
            try:
                self._hotkey.stop()
            except Exception:
                pass
            self._hotkey = None

    def _on_hotkey(self) -> None:
        # Runs on the pynput listener thread — marshal the AppKit work to the main thread.
        text = self._text

        def _paste() -> None:
            self._disarm()
            if self._panel is not None:
                self._panel.orderOut_(None)
            paste_and_restore(text)

        AppHelper.callAfter(_paste)
