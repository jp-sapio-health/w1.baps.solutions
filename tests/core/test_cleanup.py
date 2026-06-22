"""Cleanup stage tests — light disfluency + self-correction, with a hard negative corpus.

The self-correction heuristic must correct the intended word WITHOUT eating sentence content,
and must never fire on ordinary speech that merely contains words like "mean" or "sorry".
"""
from w1_core.config import CleanupConfig, CorrectionMode, W1Config
from w1_core.correction.cleanup import cleanup_text
from w1_core.correction.engine import correct


def _clean(text, **kw):
    return cleanup_text(text, **kw)[0]


# --- self-correction: corrects the word, keeps the rest of the sentence ------------------
def test_self_correction_keeps_sentence():
    assert _clean("lets meet on monday, I mean tuesday") == "lets meet on tuesday"
    assert _clean("monday I mean tuesday") == "tuesday"
    assert _clean("send it to John scratch that Sarah") == "send it to Sarah"


# --- self-correction negative corpus: ordinary speech is untouched -----------------------
def test_self_correction_negatives():
    safe = [
        "I'm sorry I'm late for the meeting",
        "what do you mean by that",
        "the mean value is high",
        "I mean it sincerely",         # no word precedes the cue -> no match
        "rather warm today",
    ]
    for s in safe:
        assert _clean(s) == s, f"self-correction wrongly fired on {s!r} -> {_clean(s)!r}"


# --- filler removal -----------------------------------------------------------------------
def test_filler_removal():
    assert _clean("um I think uh we should go") == "I think we should go"
    assert _clean("the patient is uh stable") == "the patient is stable"


def test_filler_does_not_eat_words():
    for s in ["an error occurred", "the umbrella is wet", "her demeanour"]:
        assert _clean(s) == s, f"filler ate into a word: {s!r} -> {_clean(s)!r}"


# --- raw mode disables self-correction (clinical safety), keeps filler --------------------
def test_raw_mode_no_self_correction():
    cfg = W1Config(correction_mode=CorrectionMode.raw)
    # word-deleting self-correction must NOT run in raw mode
    assert correct("give 5mg I mean 10mg", cfg).text == "give 5mg I mean 10mg"


def test_cleanup_toggle_off():
    out = _clean("um monday I mean tuesday", remove_fillers=False, apply_self_corrections=False)
    assert out == "um monday I mean tuesday"
