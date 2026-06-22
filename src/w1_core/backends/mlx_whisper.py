"""Apple MLX Whisper backend — the real runtime path on Apple Silicon (Metal-accelerated).

mlx-whisper is lazy-imported inside ``transcribe`` so that importing ``w1_core`` never pulls
the ML stack (keeps the platform-boundary contract green and the core mobile-portable).
"""
from __future__ import annotations

from .base import Segment, TranscriptionResult


class MLXWhisperBackend:
    def __init__(self, model_id: str):
        self.model_id = model_id

    def transcribe(self, audio, *, initial_prompt=None, language=None) -> TranscriptionResult:
        import mlx_whisper  # lazy — heavy ML import stays out of w1_core import graph

        kwargs: dict = {"path_or_hf_repo": self.model_id}
        if initial_prompt:
            kwargs["initial_prompt"] = initial_prompt
        if language:
            kwargs["language"] = language

        result = mlx_whisper.transcribe(audio, **kwargs)
        segments = [
            Segment(
                start=float(s.get("start", 0.0)),
                end=float(s.get("end", 0.0)),
                text=s.get("text", ""),
                avg_logprob=float(s.get("avg_logprob", 0.0)),
                no_speech_prob=float(s.get("no_speech_prob", 0.0)),
            )
            for s in result.get("segments", [])
        ]
        return TranscriptionResult(
            text=result.get("text", "").strip(),
            language=result.get("language"),
            segments=segments,
        )
