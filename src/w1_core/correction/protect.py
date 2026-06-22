"""Mask protected sacred terms before correction, restore (canonically cased) after.

The 20 protected terms must never be mutated by fuzzy snapping or terminology rules. We
replace each occurrence with an inert placeholder before those stages run, then restore the
canonical form. Casing is preserved safely: capitalised canonicals (Akshardham, Swamishri)
always win; lowercase canonicals keep a leading capital if the speaker used one — so the
name "Maya" survives as "Maya" rather than being forced to the term "maya".
"""
from __future__ import annotations

import re

from .loader import load_rule_data

# Private-use sentinel (U+F8FF) wrapping the index, e.g. "0". This code point is
# never produced by Whisper and is a non-word char, so a \b-anchored terminology rule can
# never match across it, and the fuzzy stage (alpha tokens only) ignores it.
_SENTINEL = ""


def _placeholder(index: int) -> str:
    return f"{_SENTINEL}{index}{_SENTINEL}"


def _canonical_form(occurrence: str, canonical: str) -> str:
    if canonical[:1].isupper():
        return canonical
    if occurrence[:1].isupper():  # preserve sentence-initial / proper-name capital
        return canonical[:1].upper() + canonical[1:]
    return canonical


def _protected_regex() -> tuple[re.Pattern, dict[str, str]]:
    data = load_rule_data()
    # longest-first so multi-word protected terms win over any substring
    terms = sorted(data.protected, key=len, reverse=True)
    pattern = r"\b(" + "|".join(re.escape(t) for t in terms) + r")\b"
    return re.compile(pattern, re.IGNORECASE), {t.lower(): t for t in data.protected}


def mask_protected(text: str) -> tuple[str, list[str]]:
    """Replace protected terms with placeholders. Returns (masked_text, restorations)."""
    regex, canon = _protected_regex()
    store: list[str] = []

    def _sub(m: re.Match) -> str:
        occurrence = m.group(0)
        store.append(_canonical_form(occurrence, canon[occurrence.lower()]))
        return _placeholder(len(store) - 1)

    return regex.sub(_sub, text), store


def unmask_protected(text: str, store: list[str]) -> str:
    """Restore placeholders to canonical forms (reverse order avoids prefix collisions)."""
    for i in range(len(store) - 1, -1, -1):
        text = text.replace(_placeholder(i), store[i])
    return text
