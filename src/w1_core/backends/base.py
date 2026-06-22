"""The single backend seam. Core code only ever touches this Protocol.

``initial_prompt`` is passed PER CALL so all biasing logic stays in the core (where the
glossary lives); swapping backends never touches biasing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class Segment:
    start: float
    end: float
    text: str
    avg_logprob: float = 0.0
    no_speech_prob: float = 0.0


@dataclass
class TranscriptionResult:
    text: str
    language: str | None = None
    segments: list[Segment] = field(default_factory=list)


@runtime_checkable
class TranscriptionBackend(Protocol):
    """Audio (a float32 16 kHz mono ndarray, or a file path) -> text + confidences."""

    def transcribe(
        self, audio, *, initial_prompt: str | None = None, language: str | None = None
    ) -> TranscriptionResult: ...
