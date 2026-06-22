"""Correction-engine unit tests (pure — no audio, model, or OS).

The load-bearing safety property: dictation mode applies ONLY sacred terminology, never the
editorial rules that would corrupt ordinary/clinical English; raw mode changes nothing.
"""
from w1_core.correction.loader import load_rule_data
from w1_core.correction.protect import mask_protected, unmask_protected
from w1_core.correction.rules import apply_terminology


def test_rule_data_loads():
    d = load_rule_data()
    assert len(d.rules) == 64
    assert len(d.protected) == 20
    assert "akshardham" in d.in_vocab
    assert d.canonical_by_lower["akshardham"] == "Akshardham"


# --- dictation mode: sacred terminology fires (with case preservation) -------------------
def test_dictation_sacred_substitutions():
    cases = {
        "We visited the temple today": "We visited the mandir today",
        "the aarti was beautiful": "the arti was beautiful",
        "Shrijimaharaj spoke": "Shriji Maharaj spoke",
        "the saints gathered": "the swamis gathered",      # lowercase preserved
        "Saints gathered": "Swamis gathered",              # capital preserved
        "read the scriptures": "read the shastras",
        "the congregation prayed": "the satsang prayed",
        "join the fellowship": "join the satsang",
        "daily recitation matters": "daily mukhpath matters",
    }
    for src, want in cases.items():
        got, _ = apply_terminology(src, "dictation")
        assert got == want, f"{src!r} -> {got!r} (wanted {want!r})"


# --- dictation mode: editorial families MUST NOT fire (clinical-safety) ------------------
def test_dictation_does_not_apply_editorial_rules():
    for src in [
        "perhaps we will meet",        # hedging (document-only)
        "a major milestone",           # forbidden-vocab (document-only)
        "our main stakeholder",        # forbidden-vocab (document-only)
        "we drove through Saurashtra",  # place-name (document-only)
    ]:
        got, _ = apply_terminology(src, "dictation")
        assert got == src, f"editorial rule leaked into dictation: {src!r} -> {got!r}"


def test_dictation_negative_corpus_is_byte_identical():
    """Ordinary English / clinical / tech speech must pass through untouched in dictation mode."""
    safe = [
        "I gave him a hand with the array index",
        "we hit a project milestone for our main stakeholder",
        "I had dal and rice for lunch",
        "the meeting is probably on Tuesday",
        "seven patients were seen on the ward",
    ]
    for s in safe:
        got, log = apply_terminology(s, "dictation")
        assert got == s, f"false correction: {s!r} -> {got!r}"
        assert log == []


# --- document mode: editorial families fire ----------------------------------------------
def test_document_mode_applies_editorial():
    assert apply_terminology("a major milestone", "document")[0] == "a major occasion"
    assert apply_terminology("we drove through Saurashtra", "document")[0] == "we drove through Kathiawad"
    assert "perhaps" not in apply_terminology("perhaps we will meet", "document")[0].lower()


# --- raw mode: nothing changes ------------------------------------------------------------
def test_raw_mode_changes_nothing():
    for src in ["We visited the temple", "the saints gathered", "perhaps a milestone"]:
        got, log = apply_terminology(src, "raw")
        assert got == src and log == []


# --- protected terms ----------------------------------------------------------------------
def test_protect_roundtrip_canonical_casing():
    masked, store = mask_protected("we went to akshardham for satsang")
    assert "akshardham" not in masked and "satsang" not in masked
    assert unmask_protected(masked, store) == "we went to Akshardham for satsang"


def test_protect_preserves_name_maya():
    masked, store = mask_protected("Maya went home")
    assert unmask_protected(masked, store) == "Maya went home"


def test_protect_blocks_rule_mutation_but_allows_others():
    # 'shastra' is protected (masked); 'scripture' is not -> rule converts it to 'shastra'
    masked, store = mask_protected("the shastra and the scripture")
    ruled, _ = apply_terminology(masked, "dictation")
    out = unmask_protected(ruled, store)
    assert out == "the shastra and the shastra"
