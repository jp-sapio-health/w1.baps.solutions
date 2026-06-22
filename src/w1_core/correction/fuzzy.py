"""Conservative fuzzy/phonetic snapping of OOV near-misses to canonical glossary spellings.

This is what fixes Whisper mishearing Gujarati terms ("mandhir"->"mandir",
"vachanamrit"->"Vachanamrut"). It is deliberately cautious — the cardinal sin is snapping an
ordinary English word onto a sacred term. Guards, ALL must pass before a token is snapped:

  * the token is out-of-vocabulary (not already a known glossary/protected spelling)
  * the token is not an ordinary English word (checked against the system dictionary + a
    bundled common-word fallback)
  * the token is >= ``min_term_length`` chars (ultra-short terms collide with English)
  * it is not an ALL-CAPS acronym and contains no apostrophe
  * similarity to the best glossary target clears the threshold, OR the phonetic key matches
    and similarity clears a slightly lower relaxed threshold
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import jellyfish
from rapidfuzz import fuzz, process

from .loader import load_rule_data

_WORD = re.compile(r"[A-Za-z][A-Za-z’'\-]*")

# Small fallback so the English guard still works off-macOS (mobile/Linux) where the system
# word list may be absent. The system dictionary (loaded below) is the primary source.
_COMMON_EN = frozenset(
    """the be to of and a in that have i it for not on with he as you do at this but his by from
    they we say her she or an will my one all would there their what so up out if about who get
    which go me when make can like time no just him know take people into year your good some
    could them see other than then now look only come its over think also back after use two how
    our work first well way even new want because any these give day most us is are was were been
    has had did said hand table array seven eight nine value index meeting patient drug dose ward
    temple tender major project main rather sorry mean""".split()
)


@lru_cache(maxsize=1)
def _english_words() -> frozenset[str]:
    words: set[str] = set(_COMMON_EN)
    p = Path("/usr/share/dict/words")
    if p.exists():
        try:
            words |= {
                w.strip().lower()
                for w in p.read_text(encoding="utf-8", errors="ignore").splitlines()
                if w.strip()
            }
        except OSError:
            pass
    return frozenset(words)


@lru_cache(maxsize=1)
def _fuzzy_targets() -> dict[str, str]:
    """Matchable key (lowercased; also a space/hyphen-stripped variant) -> canonical spelling."""
    data = load_rule_data()
    targets: dict[str, str] = {}
    for lower, canonical in data.canonical_by_lower.items():
        if len(lower) < 4:
            continue  # ultra-short terms are never fuzzy targets
        targets.setdefault(lower, canonical)
        compact = lower.replace(" ", "").replace("-", "")
        if compact != lower and len(compact) >= 4:
            targets.setdefault(compact, canonical)
    return targets


def _match_case(original: str, canonical: str) -> str:
    if original[:1].isupper() and canonical[:1].islower():
        return canonical[:1].upper() + canonical[1:]
    return canonical


def snap_fuzzy(text: str, *, min_similarity: float = 0.88, min_term_length: int = 4):
    """Snap OOV near-miss tokens to canonical glossary spellings. Returns (text, applied_log)."""
    data = load_rule_data()
    targets = _fuzzy_targets()
    keys = list(targets.keys())
    english = _english_words()
    primary = min_similarity * 100
    relaxed = max(78.0, primary - 8)
    applied: list[dict] = []

    def _repl(m: re.Match) -> str:
        token = m.group(0)
        low = token.lower()
        if (
            len(low) < min_term_length
            or "'" in low
            or "’" in low
            or token.isupper()
            or low in data.in_vocab
            or low in english
        ):
            return token

        best = process.extractOne(low, keys, scorer=fuzz.ratio, score_cutoff=relaxed)
        if best is None:
            return token
        key, score, _ = best
        canonical = targets[key]
        if canonical.lower() == low:
            return token

        phonetic_match = jellyfish.metaphone(low) == jellyfish.metaphone(key)
        if score >= primary or (phonetic_match and score >= relaxed and len(low) >= 5):
            applied.append({"rule_id": "fuzzy:snap", "label": f"{token}->{canonical}", "count": 1})
            return _match_case(token, canonical)
        return token

    return _WORD.sub(_repl, text), applied
