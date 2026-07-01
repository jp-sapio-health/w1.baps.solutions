"""Bundle entry point for py2app.

Two jobs beyond launching the app:

1. Log to a file. A frozen .app has no terminal, so every print (hotkey errors, backend
   failures, permission warnings) vanished; failures looked like an unresponsive app.
   Everything now also lands in ~/Library/Logs/W1.log.
2. Self-test mode. `W1_SELFTEST=1 W1.app/Contents/MacOS/W1` imports the whole dictation
   runtime (mic, portaudio, mlx, mlx_whisper, backend selection) inside the real bundle and
   exits non-zero on any failure. build.sh runs this after signing, so a bundle missing a
   dylib or package can no longer ship.
"""
import os
import sys


def _setup_logging() -> None:
    log_path = os.path.expanduser("~/Library/Logs/W1.log")
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        log = open(log_path, "a", buffering=1)

        class _Tee:
            def __init__(self, *streams):
                self._streams = streams

            def write(self, data):
                for s in self._streams:
                    try:
                        s.write(data)
                    except Exception:
                        pass

            def flush(self):
                for s in self._streams:
                    try:
                        s.flush()
                    except Exception:
                        pass

        sys.stdout = _Tee(sys.__stdout__, log)
        sys.stderr = _Tee(sys.__stderr__, log)
        import datetime

        print(f"[w1] ---- launch {datetime.datetime.now().isoformat(timespec='seconds')} ----")
    except Exception:
        pass  # logging must never block the app


def _selftest() -> int:
    """Import the full dictation runtime inside the bundle; report each stage."""
    import traceback

    failures = 0
    checks = [
        ("sounddevice (portaudio)", "import sounddevice; sounddevice.query_devices()"),
        ("mlx.core", "import mlx.core"),
        ("mlx_whisper", "import mlx_whisper"),
        ("tokenizer (tiktoken)", "from mlx_whisper.tokenizer import get_tokenizer"),
        ("backend selection (must be MLX)", (
            "from w1_core.config import W1Config;"
            "from w1_core.backends.factory import select_backend;"
            "b = select_backend(W1Config());"
            "assert type(b).__name__ == 'MLXWhisperBackend', f'wrong backend: {type(b).__name__}'"
        )),
        ("pyperclip", "import pyperclip"),
        ("permissions module", "from w1_macos.permissions import input_monitoring_status"),
    ]
    for name, code in checks:
        try:
            exec(code, {})
            print(f"  ok    {name}")
        except Exception:
            failures += 1
            print(f"  FAIL  {name}")
            traceback.print_exc()
    print(f"selftest: {'PASS' if failures == 0 else f'{failures} FAILURE(S)'}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    if os.environ.get("W1_SELFTEST"):
        raise SystemExit(_selftest())
    _setup_logging()
    from w1_macos.app import main

    raise SystemExit(main())
