"""Load generated w1_data JSON into compiled, ready-to-apply runtime structures.

Translates the TypeScript-origin rules (JS regex source + flags, literal or case-preserving
replacements) into Python ``re`` patterns and callables, and builds the in-vocabulary index
used by the fuzzy stage to tell a known term from an out-of-vocabulary near-miss.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable

import w1_data

# JS regex flags we honour. ``g`` (global) is the default for re.sub/subn; ``u``/``y`` are
# meaningless for Python's unicode-native ``re`` and are ignored.
_FLAG_MAP = {"i": re.IGNORECASE, "m": re.MULTILINE, "s": re.DOTALL, "x": re.VERBOSE}


def _compile_flags(flags: str) -> int:
    out = 0
    for ch in flags:
        out |= _FLAG_MAP.get(ch, 0)
    return out


def _literal_repl(value: str) -> str:
    """Convert a JS replacement literal (``$1``-style backrefs) to a Python one (``\\1``)."""
    return re.sub(r"\$(\d+)", r"\\\1", value)


Replacement = Callable[[re.Match], str] | str


def _make_repl(rep: dict) -> Replacement:
    kind = rep.get("type")
    if kind == "literal":
        return _literal_repl(rep["value"])
    if kind == "case_preserve":
        when, if_match, otherwise = rep["when_first_char"], rep["if_match"], rep["else"]

        def _fn(m: re.Match, _w=when, _a=if_match, _b=otherwise) -> str:
            return _a if m.group(0)[:1] == _w else _b

        return _fn
    raise ValueError(f"unknown replacement spec: {rep!r}")


@dataclass(frozen=True)
class CompiledRule:
    rule_id: str
    family: str
    modes: tuple[str, ...]
    label: str
    regex: re.Pattern
    repl: Replacement

    def apply(self, text: str) -> tuple[str, int]:
        """Return (new_text, num_substitutions)."""
        return self.regex.subn(self.repl, text)


@dataclass(frozen=True)
class RuleData:
    rules: tuple[CompiledRule, ...]
    glossary: tuple[dict, ...]
    in_vocab: frozenset           # lowercased canonical + alias spellings (the "known word" set)
    canonical_by_lower: dict      # lower spelling -> canonical spelling (fuzzy snap target)
    protected: tuple[str, ...]
    diacritics: dict
    bias_seed: tuple[str, ...]


@lru_cache(maxsize=1)
def load_rule_data() -> RuleData:
    """Load and compile all rule data once (cached for process lifetime)."""
    glossary = w1_data.load("glossary")
    rules = tuple(
        CompiledRule(
            rule_id=r["rule_id"],
            family=r["family"],
            modes=tuple(r["modes"]),
            label=r["label"],
            regex=re.compile(r["pattern"], _compile_flags(r["flags"])),
            repl=_make_repl(r["replacement"]),
        )
        for r in w1_data.load("terminology_rules")
    )
    protected = tuple(w1_data.load("protected_terms"))

    in_vocab: set[str] = set()
    by_lower: dict[str, str] = {}
    for entry in glossary:
        for alias in entry["aliases"]:
            in_vocab.add(alias.lower())
            by_lower.setdefault(alias.lower(), alias)
        by_lower[entry["canonical"].lower()] = entry["canonical"]
    for term in protected:
        in_vocab.add(term.lower())
        by_lower.setdefault(term.lower(), term)

    # Bias-seed terms are known-good spellings (e.g. "darshan", "seva") — treat them as
    # in-vocabulary so the fuzzy stage never snaps a correct common term onto a rarer variant.
    bias_seed_raw = w1_data.load("bias_seed")
    for term in bias_seed_raw:
        in_vocab.add(term.lower())
        for word in term.split():
            if len(word) >= 3:
                in_vocab.add(word.lower())

    return RuleData(
        rules=rules,
        glossary=tuple(glossary),
        in_vocab=frozenset(in_vocab),
        canonical_by_lower=by_lower,
        protected=protected,
        diacritics=w1_data.load("diacritics"),
        bias_seed=tuple(w1_data.load("bias_seed")),
    )
