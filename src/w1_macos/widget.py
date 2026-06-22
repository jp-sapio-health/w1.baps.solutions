"""Floating, always-on-top dictation widget — an animated borderless NSPanel.

Cycles a sequence of pre-rendered pill frames per state (idle is static; listening shows a
flowing waveform; processing shows rotating dots). Frame advance is driven by the app's
main-thread animation timer via ``tick()`` so all AppKit calls stay on the main thread.
"""
from __future__ import annotations

from AppKit import (
    NSAnimationContext,
    NSColor,
    NSImage,
    NSImageScaleProportionallyUpOrDown,
    NSImageView,
    NSPanel,
    NSScreen,
    NSView,
    NSViewHeightSizable,
    NSViewWidthSizable,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorStationary,
    NSWindowStyleMaskBorderless,
    NSWindowStyleMaskNonactivatingPanel,
)
from PyObjCTools import AppHelper

from w1_macos.paths import resource_dir

# Liquid-glass backdrop (real system blur of the desktop behind the widget). Imported
# defensively so the widget still works if the constants are unavailable.
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


# Ease-out timing for the morph (pro motion feel rather than a linear resize).
try:
    from Quartz import CAMediaTimingFunction

    _EASE = CAMediaTimingFunction.functionWithName_("easeOut")
except Exception:  # pragma: no cover
    _EASE = None

_ASSETS = resource_dir() / "assets" / "widget" / "states"
_WIDTH, _HEIGHT = 86, 26           # pill size on listen (trimmed so the waveform fills it)
_CIRCLE = 44                       # resting state: a slightly elongated lozenge (not a full circle)
_REJECT_HOLD = 0.7                 # seconds the red ✕ lingers before collapsing back to rest
_SCREENSAVER_LEVEL = 1000          # NSScreenSaverWindowLevel — above normal app windows
_NSBackingStoreBuffered = 2
_GLASS_ALPHA = 0.50                # a touch more frost so the white bars pop more


def _load(name: str):
    path = _ASSETS / name
    return NSImage.alloc().initWithContentsOfFile_(str(path)) if path.exists() else None


class Widget:
    def __init__(self) -> None:
        idle = [img for i in range(6) if (img := _load(f"idle_{i}.png"))]
        if not idle:
            idle = [img for img in [_load("idle.png")] if img]
        listening = [img for i in range(12) if (img := _load(f"listening_{i}.png"))]
        processing = [img for i in range(4) if (img := _load(f"processing_{i}.png"))]
        rejected = [img for i in range(3) if (img := _load(f"reject_{i}.png"))]
        self._frames = {
            "idle": idle or [None],
            "listening": listening or idle or [None],
            "processing": processing or idle or [None],
            "rejected": rejected or idle or [None],  # degrade to idle if the ✕ art is missing
        }
        self._state = "idle"
        self._idx = 0
        self._disp_level = 0.0  # eased display level for smooth (non-snapping) bars
        self._panel = None
        self._view = None
        self._build()

    def _build(self) -> None:
        screen = NSScreen.mainScreen().frame()
        self._cx = screen.size.width / 2.0
        self._y = 96.0  # just above the Dock
        w0 = _CIRCLE  # start life as a circle
        rect = ((self._cx - w0 / 2.0, self._y), (w0, _HEIGHT))
        style = NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel

        panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, style, _NSBackingStoreBuffered, False
        )
        panel.setLevel_(_SCREENSAVER_LEVEL)
        panel.setOpaque_(False)
        panel.setBackgroundColor_(NSColor.clearColor())
        panel.setHasShadow_(False)
        panel.setIgnoresMouseEvents_(True)
        panel.setReleasedWhenClosed_(False)
        panel.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces | NSWindowCollectionBehaviorStationary
        )

        view = NSImageView.alloc().initWithFrame_(((0, 0), (w0, _HEIGHT)))
        view.setImageScaling_(NSImageScaleProportionallyUpOrDown)
        view.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)

        backing = None
        if _HAS_GLASS:
            try:
                fx = NSVisualEffectView.alloc().initWithFrame_(((0, 0), (w0, _HEIGHT)))
                fx.setMaterial_(NSVisualEffectMaterialHUDWindow)
                fx.setBlendingMode_(NSVisualEffectBlendingModeBehindWindow)
                fx.setState_(NSVisualEffectStateActive)
                fx.setAlphaValue_(_GLASS_ALPHA)
                fx.setWantsLayer_(True)
                fx.layer().setCornerRadius_(_HEIGHT / 2.0)
                fx.layer().setMasksToBounds_(True)
                fx.addSubview_(view)
                backing = fx
            except Exception as exc:  # pragma: no cover
                print(f"[w1] frosted glass unavailable: {exc}")

        panel.setContentView_(backing if backing is not None else view)
        self._panel, self._view = panel, view

    def _resize_to(self, width: float) -> None:
        """Smoothly morph the window (glass + content) between the resting line and the pill."""
        frame = ((self._cx - width / 2.0, self._y), (width, _HEIGHT))
        NSAnimationContext.beginGrouping()
        ctx = NSAnimationContext.currentContext()
        ctx.setDuration_(0.34)
        if _EASE is not None:
            ctx.setTimingFunction_(_EASE)
        self._panel.animator().setFrame_display_(frame, True)
        NSAnimationContext.endGrouping()

    def _show(self, image) -> None:
        if image is not None:
            self._view.setImage_(image)
        self._panel.orderFrontRegardless()

    def set_state(self, state: str) -> None:
        """Thread-safe: switch state and reset the animation on the main thread."""

        def _do() -> None:
            self._state = state if state in self._frames else "idle"
            self._idx = 0
            self._disp_level = 0.0
            if self._state == "rejected":
                self._play_reject()
                return
            self._show(self._frames[self._state][0])
            self._resize_to(_CIRCLE if self._state == "idle" else _WIDTH)  # line <-> pill morph

        AppHelper.callAfter(_do)

    def _play_reject(self) -> None:
        """Morph the waveform into a red ✕, hold briefly, then collapse back to the resting line.

        Main-thread only (called from set_state's marshaled block). Uses timed callbacks rather
        than the shared animation timer so it never interferes with listening/processing.
        """
        frames = self._frames["rejected"]
        self._resize_to(_WIDTH)
        self._show(frames[0])
        for i, img in enumerate(frames[1:], start=1):
            AppHelper.callLater(0.07 * i, self._view.setImage_, img)

        def _collapse() -> None:
            if self._state == "rejected":  # only if a new cycle hasn't taken over
                self.set_state("idle")

        AppHelper.callLater(0.07 * len(frames) + _REJECT_HOLD, _collapse)

    def set_level(self, level: int) -> None:
        """Drive the listening waveform from a live mic amplitude level (0..11)."""

        def _do() -> None:
            if self._state != "listening":
                return
            frames = self._frames["listening"]
            # ease the displayed level toward the live mic level so bars glide, not snap
            self._disp_level += (level - self._disp_level) * 0.4
            idx = max(0, min(len(frames) - 1, round(self._disp_level)))
            self._view.setImage_(frames[idx])

        AppHelper.callAfter(_do)

    def tick(self) -> None:
        """Advance the processing animation (listening is live-level-driven, idle is static).

        MUST be called on the main thread (app timer).
        """
        if self._state != "processing":   # idle is a static dot; listening is live-level-driven
            return
        frames = self._frames.get(self._state)
        if not frames or len(frames) <= 1:
            return
        self._idx = (self._idx + 1) % len(frames)
        self._view.setImage_(frames[self._idx])
