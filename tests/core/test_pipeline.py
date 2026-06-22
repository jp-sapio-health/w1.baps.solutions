"""Edge-case tests for the transcribe->gate->correct pipeline.

Covers the failure / empty / hallucinated-transcription paths so the widget never inserts
garbage and the app never crashes on a bad cycle.
"""
import numpy as np
import pytest

from w1_core.backends.base import Segment, TranscriptionResult
from w1_core.backends.mock import MockBackend
from w1_core.config import CorrectionMode, W1Config
from w1_core.pipeline import transcribe_and_correct


def _audio():
    return np.zeros(16000, dtype="float32")  # 1s of silence (length is fine; content is mocked)


class _SegBackend:
    """A backend returning fixed text plus crafted per-segment confidences."""

    def __init__(self, text, avg_logprob, no_speech_prob):
        self._result = TranscriptionResult(
            text=text,
            segments=[Segment(0.0, 1.0, text, avg_logprob, no_speech_prob)],
        )

    def transcribe(self, audio, *, initial_prompt=None, language=None):
        return self._result


def test_empty_transcription_is_gated():
    r = transcribe_and_correct(_audio(), W1Config(), backend=MockBackend(""))
    assert r.gated and r.text == ""


def test_whisper_hallucinations_are_gated():
    # Whisper invents polite filler over silence — must never reach the document.
    for artifact in ("Thank you.", "  thank you. ", "[BLANK_AUDIO]", "you", "."):
        r = transcribe_and_correct(_audio(), W1Config(), backend=MockBackend(artifact))
        assert r.gated, f"artifact not gated: {artifact!r}"
        assert r.text == ""


def test_real_speech_is_corrected_and_not_gated():
    cfg = W1Config(correction_mode=CorrectionMode.dictation)
    r = transcribe_and_correct(_audio(), cfg, backend=MockBackend("we visited the temple"))
    assert not r.gated
    assert "mandir" in r.text


def test_backend_failure_propagates_for_caller_to_handle():
    """A backend exception bubbles up; the macOS controller catches it and returns to rest."""

    class _Boom:
        def transcribe(self, audio, *, initial_prompt=None, language=None):
            raise RuntimeError("model failure")

    with pytest.raises(RuntimeError):
        transcribe_and_correct(_audio(), W1Config(), backend=_Boom())


def test_low_confidence_transcription_is_gated():
    # High no-speech probability AND very low logprob -> noise, never paste it.
    backend = _SegBackend("garbled noise", avg_logprob=-2.5, no_speech_prob=0.95)
    r = transcribe_and_correct(_audio(), W1Config(), backend=backend)
    assert r.gated and r.gated_reason == "low_confidence" and r.text == ""


def test_confident_speech_is_not_gated():
    backend = _SegBackend("we visited the temple", avg_logprob=-0.25, no_speech_prob=0.05)
    r = transcribe_and_correct(_audio(), W1Config(), backend=backend)
    assert not r.gated and "mandir" in r.text


def test_confidence_gate_can_be_disabled():
    cfg = W1Config()
    cfg.confidence.enabled = False
    backend = _SegBackend("low conf words", avg_logprob=-2.5, no_speech_prob=0.95)
    r = transcribe_and_correct(_audio(), cfg, backend=backend)
    assert not r.gated  # gate off -> confidences ignored


def test_mock_without_segments_is_never_confidence_gated():
    # The mock backend has no segment data -> we must not gate on absent evidence.
    r = transcribe_and_correct(_audio(), W1Config(), backend=MockBackend("a real sentence here"))
    assert not r.gated


def test_gujarati_mode_transliterates_to_roman():
    cfg = W1Config(correction_mode=CorrectionMode.gujarati)
    assert cfg.resolved_language() == "gu"
    r = transcribe_and_correct(_audio(), cfg, backend=MockBackend("મંદિર કથા"))
    assert not r.gated
    assert r.text == "mandir kathā"
    assert r.applied and r.applied[0]["stage"] == "transliterate"
