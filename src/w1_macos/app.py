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
        # Permissions submenu: live status + one-click open of the exact pane. Input Monitoring
        # is the one users miss (Accessibility alone is not enough for the key tap on macOS 14+).
        self._perm_status_item = rumps.MenuItem("Checking permissions…", callback=None)
        self._perm_menu = rumps.MenuItem("Permissions")
        self._perm_menu.update([
            self._perm_status_item,
            None,
            rumps.MenuItem("Open Input Monitoring settings", callback=self._open_input_monitoring),
            rumps.MenuItem("Open Accessibility settings", callback=self._open_accessibility),
        ])
        self.menu = [
            rumps.MenuItem("W1 — hold Right-Option to talk", callback=None),
            None,
            *self._mode_items.values(),
            None,
            self._perm_menu,
            rumps.MenuItem("Relaunch W1", callback=self._relaunch),
            rumps.MenuItem("About W1", callback=self._about),
            None,
            rumps.MenuItem("Quit W1", callback=self._quit),
        ]

    # -- permissions ----------------------------------------------------------
    def refresh_permission_status(self, _timer=None) -> None:
        """Reflect current grants in the menu; flag the hotkey as blocked when Input Monitoring is off."""
        from w1_macos.permissions import permission_status

        s = permission_status()
        im, ax = s["input_monitoring"], s["accessibility"]
        if im == "granted" and ax == "granted":
            self._perm_status_item.title = "Permissions granted ✓"
            self.title = None
        else:
            missing = []
            if im != "granted":
                missing.append("Input Monitoring")
            if ax != "granted":
                missing.append("Accessibility")
            self._perm_status_item.title = "Hotkey blocked — enable: " + ", ".join(missing)
            # A visible menu-bar cue so the user is not left guessing why nothing happens.
            self.title = "!"

    def _open_input_monitoring(self, _item=None) -> None:
        from w1_macos.permissions import open_settings_pane

        open_settings_pane("input_monitoring")

    def _open_accessibility(self, _item=None) -> None:
        from w1_macos.permissions import open_settings_pane

        open_settings_pane("accessibility")

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
                "Local, private dictation. English and BAPS Gujarati."
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

    # Request Input Monitoring + Accessibility ONCE (see request_missing_once: re-prompting every
    # launch is what produced the "asks every time" nag). The hotkey needs BOTH; on macOS 14+ the
    # one users miss is Input Monitoring (Accessibility alone is not enough for pynput's key tap).
    try:
        from w1_macos.permissions import request_missing_once

        perms = request_missing_once()
        missing = [k for k, v in perms.items() if v != "granted"]
        if missing:
            print(f"[w1] permissions not granted yet: {', '.join(missing)}")
            rumps.notification(
                "W1 needs permission to hear the hotkey",
                "Enable W1 under " + " and ".join(m.replace("_", " ").title() for m in missing),
                "Open the menu bar → Permissions → Open Input Monitoring settings, switch W1 on, "
                "then Relaunch W1.",
            )
    except Exception as exc:  # permission checks must never stop the app
        print(f"[w1] permission check failed: {exc}")

    try:
        app.hotkey.start()  # needs Input Monitoring + Accessibility; requested above
    except Exception as exc:
        print(f"[w1] hotkey listener could not start (grant Input Monitoring): {exc}")
    app.controller.warm_up()
    # Keep the menu status live so the user sees the moment a grant takes effect.
    app.refresh_permission_status()
    app._perm_timer = rumps.Timer(app.refresh_permission_status, 3.0)
    app._perm_timer.start()

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
