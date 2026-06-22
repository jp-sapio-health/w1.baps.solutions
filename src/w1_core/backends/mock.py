"""A backend that returns a canned transcript — lets the whole pipeline run with no model."""
from __future__ import annotations

from .base import Segment, TranscriptionResult


class MockBackend:
    def __init__(self, text: str = "", *, language: str | None = "en", segments=None):
        self._text = text
        self._language = language
        self._segments = segments or []

    def transcribe(self, audio, *, initial_prompt=None, language=None) -> TranscriptionResult:
        return TranscriptionResult(self._text, self._language, list(self._segments))
