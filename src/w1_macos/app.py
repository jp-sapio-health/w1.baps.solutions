"""w1 menu-bar app + floating widget. Entry point: ``w1 app`` (or ./w1 app).

The menu-bar icon reflects state (idle/listening/processing) and the active correction mode is
switchable from the menu. The floating widget shows the pill. The global hotkey drives a
dictation cycle via the Controller.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import rumps
from PyObjCTools import AppHelper

from w1_core import __version__
from w1_core.config import CorrectionMode, W1Config
from w1_macos.controller import Controller
from w1_macos.hotkey import HotkeyListener
from w1_macos.paths import resource_dir

_REPO_ROOT = Path(__file__).resolve().parents[2]  # dev source root (for relaunch re-exec)
_MENUBAR = resource_dir() / "assets" / "menubar"  # frozen-bundle aware


def _short_version() -> str:
    # "1.1.0" -> "1.1" for the About box.
    return ".".join(__version__.split(".")[:2])
_ICON_IDLE = str(_MENUBAR / "idle.png")
_ICON_ACTIVE = str(_MENUBAR / "active.png")
# Menu order is deliberate: Dictate (verbatim) -> Default (sacred-aware) -> Clean + (editorial)
# -> Gujarati (katha). The map values are the user-facing labels.
_MODE_LABEL = {
    CorrectionMode.raw: "Dictate",
    CorrectionMode.dictation: "Default",
    CorrectionMode.document: "Clean +",
    CorrectionMode.gujarati: "Gujarati (katha)",
}


class W1App(rumps.App):
    def __init__(self) -> None:
        super().__init__("w1", title=None, icon=_ICON_IDLE, template=True, quit_button=None)
        self.config = W1Config()
        self.widget = None
        self.paste_panel = None
        self.controller = Controller(
            self.config,
            on_state=self._on_state,
            on_level=self._on_level,
            on_result=self._on_result,
        )
        self.hotkey = HotkeyListener(
            on_start=self.controller.start_recording,
            on_stop=self.controller.stop_recording,
            mode=self.config.hotkey_mode.value,
            key=self.config.hotkey,
        )
        self._mode_items = {
            mode: rumps.MenuItem(label, callback=self._make_mode_setter(mode))
            for mode, label in _MODE_LABEL.items()
        }
        self._mode_items[CorrectionMode.dictation].state = 1
        self.menu = [
            rumps.MenuItem("W1 — hold Right-Option to talk", callback=None),
            None,
            *self._mode_items.values(),
            None,
            rumps.MenuItem("Relaunch W1", callback=self._relaunch),
            rumps.MenuItem("About W1", callback=self._about),
            None,
            rumps.MenuItem("Quit W1", callback=self._quit),
        ]

    # -- state / UI -----------------------------------------------------------
    def _on_state(self, state: str) -> None:
        AppHelper.callAfter(self._set_icon, state)
        if self.widget is not None:
            self.widget.set_state(state)

    def _on_level(self, level: int) -> None:
        if self.widget is not None:
            self.widget.set_level(level)

    def _on_result(self, text: str) -> None:
        """Paste into the focused field, or float the paste panel when nothing editable is focused."""
        from w1_macos.focus import editable_target
        from w1_macos.inject import paste_and_restore

        if editable_target() or self.paste_panel is None:
            paste_and_restore(text)
        else:
            self.paste_panel.present(text)

    def _set_icon(self, state: str) -> None:
        # Clean monochrome template icon — filled while active, outline at rest. No coloured dots.
        self.icon = _ICON_ACTIVE if state in ("listening", "processing") else _ICON_IDLE
        self.template = True

    def _make_mode_setter(self, mode: CorrectionMode):
        def _setter(_item) -> None:
            self.controller.set_mode(mode.value)
            for m, item in self._mode_items.items():
                item.state = 1 if m == mode else 0

        return _setter

    def _about(self, _item) -> None:
        rumps.alert(
            title="W1",
            message=(
                f"W1 v{_short_version()}\n\n"
                "Local, privacy-first dictation — English + BAPS Gujarati,\n"
                "fully on-device. Built for sewa. Private by design."
            ),
            ok="Close",
        )

    def _relaunch(self, _item=None) -> None:
        """Start a fresh instance, then quit this one (works from ./w1 app and the .app bundle)."""
        try:
            self.hotkey.stop()
        except Exception:
            pass
        try:
            if getattr(sys, "frozen", False):  # packaged .app bundle
                bundle = Path(sys.executable).resolve().parents[2]  # …/W1.app
                subprocess.Popen(["/usr/bin/open", "-n", str(bundle)], start_new_session=True)
            else:  # dev: re-exec the CLI module against the live source tree
                subprocess.Popen(
                    [sys.executable, "-m", "w1_macos.cli", "app"],
                    cwd=str(_REPO_ROOT),
                    env={**os.environ, "PYTHONPATH": str(_REPO_ROOT / "src")},
                    start_new_session=True,
                )
        finally:
            rumps.quit_application()

    def _quit(self, _item) -> None:
        try:
            self.hotkey.stop()
        finally:
            rumps.quit_application()


def main() -> int:
    app = W1App()
    try:
        app.hotkey.start()  # needs Accessibility / Input Monitoring; granted on first run
    except Exception as exc:
        print(f"[w1] hotkey listener could not start (grant Input Monitoring): {exc}")
    app.controller.warm_up()

    def _init_widget(timer) -> None:
        try:
            from w1_macos.widget import Widget

            app.widget = Widget()
            app.widget.set_state("idle")
        except Exception as exc:  # menu-bar app still works without the floating widget
            print(f"[w1] floating widget unavailable: {exc}")
        try:
            from w1_macos.paste_panel import PastePanel

            app.paste_panel = PastePanel()
        except Exception as exc:  # paste falls back to direct injection without the panel
            print(f"[w1] paste panel unavailable: {exc}")
        timer.stop()

    rumps.Timer(_init_widget, 0.4).start()

    def _animate(_timer) -> None:
        if app.widget is not None:
            try:
                app.widget.tick()
            except Exception:
                pass

    app._anim_timer = rumps.Timer(_animate, 0.09)  # ~11 fps frame cycling
    app._anim_timer.start()

    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
