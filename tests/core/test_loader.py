"""Tests for the rule-data loader: JS->Python translation and the compiled index."""
import re

import pytest

from w1_core.correction.loader import (
    _compile_flags,
    _literal_repl,
    _make_repl,
    load_rule_data,
)


def test_literal_backref_js_to_python():
    # JS "$1" backrefs become Python "\1".
    assert _literal_repl("$1-x") == r"\1-x"
    assert _literal_repl("no backref") == "no backref"


def test_compile_flags_maps_known_and_ignores_meaningless():
    assert _compile_flags("i") & re.IGNORECASE
    assert _compile_flags("ms") & re.MULTILINE and _compile_flags("ms") & re.DOTALL
    assert _compile_flags("guy") == 0  # g/u/y are no-ops for Python re


def test_make_repl_literal():
    assert _make_repl({"type": "literal", "value": "$1!"}) == r"\1!"


def test_make_repl_case_preserve():
    fn = _make_repl(
        {"type": "case_preserve", "when_first_char": "M", "if_match": "Mandir", "else": "mandir"}
    )
    assert fn(re.match(r"\w+", "Mandir")) == "Mandir"
    assert fn(re.match(r"\w+", "mandir")) == "mandir"


def test_make_repl_unknown_spec_raises():
    with pytest.raises(ValueError):
        _make_repl({"type": "nonsense"})


def test_load_rule_data_is_populated_and_indexed():
    d = load_rule_data()
    assert d.rules and d.protected and d.bias_seed
    # every compiled rule carries a usable regex + at least one mode
    for r in d.rules:
        assert isinstance(r.regex, re.Pattern) and r.modes
    # the in-vocab index is lowercased and covers canonical glossary spellings
    assert all(t == t.lower() for t in d.in_vocab)
    for entry in d.glossary:
        assert entry["canonical"].lower() in d.canonical_by_lower


def test_load_rule_data_is_cached():
    assert load_rule_data() is load_rule_data()  # lru_cache -> identity
