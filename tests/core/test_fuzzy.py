"""Fuzzy/phonetic snap tests — catch Whisper's Gujarati mishears, never corrupt English."""
from w1_core.config import CorrectionMode, W1Config
from w1_core.correction.engine import correct
from w1_core.correction.fuzzy import snap_fuzzy


def test_fuzzy_snaps_mishears():
    cases = {
        "we went to the mandhir": "mandir",
        "the vachanamrit was read": "Vachanamrut",
        "they did satsung together": "satsang",
        "offered to the morti": "murti",
    }
    for src, term in cases.items():
        out, _ = snap_fuzzy(src)
        assert term in out, f"{src!r} -> {out!r} (wanted {term})"


def test_fuzzy_no_false_positives():
    negatives = [
        "I gave him a hand with the array index",
        "we hit a project milestone for our main stakeholder",
        "seven patients were seen on the ward",
        "the patient's temple was tender",
        "please book the meeting room",
        "doing seva and darshan",  # darshan must NOT snap to "Darshans"
    ]
    for s in negatives:
        out, _ = snap_fuzzy(s)
        assert out == s, f"false positive: {s!r} -> {out!r}"


def test_fuzzy_off_in_raw_mode():
    cfg = W1Config(correction_mode=CorrectionMode.raw)
    assert correct("we went to the mandhir", cfg).text == "we went to the mandhir"


def test_fuzzy_via_engine_dictation():
    cfg = W1Config(correction_mode=CorrectionMode.dictation)
    out = correct("we went to the mandhir for satsung", cfg).text
    assert "mandir" in out and "satsang" in out
