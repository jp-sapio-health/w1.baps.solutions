"""Select a transcription backend from config. MLX on Apple Silicon, else faster-whisper."""
from __future__ import annotations

import platform

from ..config import W1Config
from .base import TranscriptionBackend


def select_backend(config: W1Config) -> TranscriptionBackend:
    choice = config.backend

    if choice == "mock":
        from .mock import MockBackend

        return MockBackend()

    if choice == "mlx" or (choice == "auto" and platform.machine() == "arm64"):
        try:
            # mlx is a NAMESPACE package: `import mlx` succeeds even when the compiled core
            # is missing or its dylib cannot load. Probe the real extension module so a broken
            # install falls through instead of returning a backend that dies at transcribe time.
            import mlx.core  # noqa: F401

            from .mlx_whisper import MLXWhisperBackend

            return MLXWhisperBackend(config.model_id)
        except Exception:
            if choice == "mlx":
                raise

    from .faster_whisper import FasterWhisperBackend

    return FasterWhisperBackend(config.model_id)
