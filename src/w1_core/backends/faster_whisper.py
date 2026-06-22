"""Portable faster-whisper backend (CI-validated fallback for non-Apple-Silicon).

Not asserted to run on this Apple Silicon box (ctranslate2 wheel availability varies); MLX is
the real local path. Lazy-imports faster_whisper so w1_core import stays clean.
"""
from __future__ import annotations

from .base import Segment, TranscriptionResult

# faster-whisper expects a model size or path, not an mlx-community HF repo id.
_MODEL_ALIASES = {
    "mlx-community/whisper-large-v3-turbo": "large-v3-turbo",
}


class FasterWhisperBackend:
    def __init__(self, model_id: str, *, device: str = "auto", compute_type: str = "int8"):
        self.model_id = _MODEL_ALIASES.get(model_id, model_id)
        self._device = device
        self._compute_type = compute_type
        self._model = None

    def _ensure_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel  # lazy

            self._model = WhisperModel(
                self.model_id, device=self._device, compute_type=self._compute_type
            )
        return self._model

    def transcribe(self, audio, *, initial_prompt=None, language=None) -> TranscriptionResult:
        model = self._ensure_model()
        segments_iter, info = model.transcribe(
            audio, initial_prompt=initial_prompt, language=language
        )
        segments, parts = [], []
        for s in segments_iter:
            parts.append(s.text)
            segments.append(
                Segment(
                    start=float(s.start),
                    end=float(s.end),
                    text=s.text,
                    avg_logprob=float(getattr(s, "avg_logprob", 0.0) or 0.0),
                    no_speech_prob=float(getattr(s, "no_speech_prob", 0.0) or 0.0),
                )
            )
        return TranscriptionResult(
            text="".join(parts).strip(),
            language=getattr(info, "language", language),
            segments=segments,
        )
