"""The single core entrypoint: audio -> transcribe -> gate -> correct -> text to insert.

Platform adapters call ``transcribe_and_correct`` and do nothing but insert ``result.text``.
No network, no disk writes, no logging of transcript content here.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .backends.base import TranscriptionBackend, TranscriptionResult
from .backends.factory import select_backend
from .config import CorrectionMode, W1Config
from .correction.bias_prompt import build_initial_prompt
from .correction.engine import correct
from .correction.transliterate import transliterate_gujarati

# Known Whisper hallucinations into silence/near-silence — never insert these.
_ARTIFACTS = {
    "",
    ".",
    "you",
    "thank you.",
    "thanks for watching!",
    "thank you for watching.",
    "[blank_audio]",
    "[ silence ]",
    "(silence)",
}


@dataclass
class InjectResult:
    text: str                      # corrected text to insert ("" when gated)
    raw: TranscriptionResult       # the backend's raw output
    applied: list[dict] = field(default_factory=list)  # structured correction log
    gated: bool = False            # True -> nothing to insert (empty/hallucination/low-confidence)
    gated_reason: str = ""         # "artifact" | "low_confidence" — drives the widget reject cue


def _is_artifact(text: str) -> bool:
    return text.strip().lower() in _ARTIFACTS


def _is_low_confidence(raw: TranscriptionResult, config: W1Config) -> bool:
    """True when Whisper's own segment confidences say this is probably not real speech.

    With no segment data (mock backend, some fallbacks) we never gate — silence is the only
    thing we refuse without evidence, and that is already caught by the artifact check.
    """
    cfg = config.confidence
    if not cfg.enabled or not raw.segments:
        return False
    n = len(raw.segments)
    mean_no_speech = sum(s.no_speech_prob for s in raw.segments) / n
    mean_logprob = sum(s.avg_logprob for s in raw.segments) / n
    return mean_no_speech > cfg.max_no_speech_prob or mean_logprob < cfg.min_avg_logprob


def transcribe_and_correct(
    audio, config: W1Config, *, backend: TranscriptionBackend | None = None
) -> InjectResult:
    backend = backend or select_backend(config)
    # The English bias prompt would skew Gujarati decoding, so it is English-modes only.
    prompt = (
        ""
        if config.correction_mode is CorrectionMode.gujarati
        else build_initial_prompt(config.bias_token_budget)
    )
    raw = backend.transcribe(
        audio, initial_prompt=prompt or None, language=config.resolved_language()
    )

    text = raw.text.strip()
    if _is_artifact(text):
        return InjectResult(text="", raw=raw, applied=[], gated=True, gated_reason="artifact")
    if _is_low_confidence(raw, config):
        return InjectResult(text="", raw=raw, applied=[], gated=True, gated_reason="low_confidence")

    # Gujarati (katha) mode bypasses the English correction chain: transliterate to ā-only Roman.
    if config.correction_mode is CorrectionMode.gujarati:
        roman = transliterate_gujarati(text)
        applied = [{"stage": "transliterate", "script": "gujarati", "rule": "aa_only"}]
        return InjectResult(text=roman, raw=raw, applied=applied, gated=False)

    result = correct(text, config)
    return InjectResult(text=result.text, raw=raw, applied=result.applied, gated=False)
