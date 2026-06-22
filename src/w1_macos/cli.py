"""w1 command-line entrypoint — the runnable slice before the full menu-bar/widget app.

Subcommands:
  w1 transcribe FILE   transcribe an audio file and print raw vs corrected
  w1 dictate           record from the mic (Enter to stop), correct, copy to clipboard
  w1 correct TEXT...   run text through the correction engine (no audio)
  w1 doctor            check the environment (model, deps, permissions hints)
"""
from __future__ import annotations

import argparse
import sys

from w1_core.config import CorrectionMode, W1Config


def _print_result(res, *, show_raw: bool) -> None:
    if show_raw:
        print(f"\n  raw:       {res.raw.text.strip()!r}", file=sys.stderr)
    if res.gated:
        print("  (nothing to insert — empty/silence)", file=sys.stderr)
        return
    if res.applied:
        notes = ", ".join(f"{a['label']}×{a['count']}" for a in res.applied)
        print(f"  corrected: {notes}", file=sys.stderr)
    print(res.text)


def _cmd_transcribe(args) -> int:
    from w1_core.pipeline import transcribe_and_correct

    cfg = W1Config(correction_mode=CorrectionMode(args.mode))
    print(f"Transcribing {args.file} (mode={args.mode})…", file=sys.stderr)
    res = transcribe_and_correct(args.file, cfg)
    _print_result(res, show_raw=True)
    return 0


def _cmd_dictate(args) -> int:
    import pyperclip

    from w1_core.pipeline import transcribe_and_correct
    from w1_macos.mic import record_seconds, record_until_enter

    cfg = W1Config(correction_mode=CorrectionMode(args.mode))
    audio = record_seconds(args.seconds) if args.seconds else record_until_enter()
    res = transcribe_and_correct(audio, cfg)
    _print_result(res, show_raw=True)
    if not res.gated and res.text:
        pyperclip.copy(res.text)
        print("  ✓ copied to clipboard — paste with ⌘V", file=sys.stderr)
    return 0


def _cmd_correct(args) -> int:
    from w1_core.correction.engine import correct

    cfg = W1Config(correction_mode=CorrectionMode(args.mode))
    print(correct(" ".join(args.text), cfg).text)
    return 0


def _cmd_app(_args) -> int:
    from w1_macos.app import main as app_main

    return app_main()


def _cmd_doctor(_args) -> int:
    import importlib.util
    import platform

    print(f"platform     : {platform.platform()} ({platform.machine()})")
    print(f"python       : {sys.version.split()[0]}")
    for mod in ("mlx", "mlx_whisper", "sounddevice", "pyperclip", "rapidfuzz", "pydantic"):
        ok = importlib.util.find_spec(mod) is not None
        print(f"  {'✓' if ok else '✗'} {mod}")
    try:
        from w1_core.correction.loader import load_rule_data

        d = load_rule_data()
        print(f"rule data    : {len(d.rules)} rules, {len(d.protected)} protected, {len(d.bias_seed)} bias terms")
    except Exception as e:  # pragma: no cover
        print(f"rule data    : ERROR {e}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="w1", description="Local bilingual dictation.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("transcribe", help="transcribe an audio file")
    t.add_argument("file")
    t.add_argument("--mode", default="dictation", choices=[m.value for m in CorrectionMode])
    t.set_defaults(func=_cmd_transcribe)

    d = sub.add_parser("dictate", help="record from the mic and correct")
    d.add_argument("--seconds", type=float, default=None, help="fixed duration instead of Enter-to-stop")
    d.add_argument("--mode", default="dictation", choices=[m.value for m in CorrectionMode])
    d.set_defaults(func=_cmd_dictate)

    c = sub.add_parser("correct", help="run text through the correction engine")
    c.add_argument("text", nargs="+")
    c.add_argument("--mode", default="dictation", choices=[m.value for m in CorrectionMode])
    c.set_defaults(func=_cmd_correct)

    doc = sub.add_parser("doctor", help="check the environment")
    doc.set_defaults(func=_cmd_doctor)

    a = sub.add_parser("app", help="launch the menu-bar app + floating widget")
    a.set_defaults(func=_cmd_app)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
