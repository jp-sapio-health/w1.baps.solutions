"""Deterministic Gujarati-script -> Roman transliteration for katha dictation.

House Rules §2.2 (BAPS): keep the long-a macron ``ā`` and strip every other diacritic, so
the only non-ASCII letter that ever appears in the output is ``ā`` (U+0101). The algorithm is
the standard syllable walk over the Gujarati Unicode block (U+0A80–U+0AFF): a consonant carries
an inherent ``a`` unless a vowel sign or a virama (halant) follows it. Word-final inherent
vowels are dropped (schwa deletion) so ``મંદિર`` reads ``mandir``, not ``mandira`` — matching
the conventional BAPS spelling. Medial schwa is left intact (deleting it reliably needs a
lexicon and would risk mangling real words).

Pure data + string logic — no imports, no ML, safe inside ``w1_core``.
"""
from __future__ import annotations

_AA = "ā"          # ā — the single permitted diacritic
_SCHWA = "\x01"    # internal marker for an inherent (consonant-carried) 'a' — resolved at the end

# Independent vowels (U+0A85–U+0A94, plus the candra/short forms folded onto their long peers).
_INDEPENDENT = {
    "અ": "a", "આ": _AA, "ઇ": "i", "ઈ": "i",
    "ઉ": "u", "ઊ": "u", "ઋ": "ru", "ઌ": "l",
    "ઍ": "e", "એ": "e", "ઐ": "ai", "ઑ": "o",
    "ઓ": "o", "ઔ": "au",
}

# Consonants (U+0A95–U+0AB9). Values are diacritic-free per the ā-only rule.
_CONSONANTS = {
    "ક": "k", "ખ": "kh", "ગ": "g", "ઘ": "gh", "ઙ": "n",
    "ચ": "ch", "છ": "chh", "જ": "j", "ઝ": "jh", "ઞ": "n",
    "ટ": "t", "ઠ": "th", "ડ": "d", "ઢ": "dh", "ણ": "n",
    "ત": "t", "થ": "th", "દ": "d", "ધ": "dh", "ન": "n",
    "પ": "p", "ફ": "ph", "બ": "b", "ભ": "bh", "મ": "m",
    "ય": "y", "ર": "r", "લ": "l", "ળ": "l", "વ": "v",
    "શ": "sh", "ષ": "sh", "સ": "s", "હ": "h",
}

# Dependent vowel signs / matras (U+0ABE–U+0ACC, plus candra forms).
_MATRAS = {
    "ા": _AA, "િ": "i", "ી": "i", "ુ": "u", "ૂ": "u",
    "ૃ": "ru", "ૄ": "ru", "ૅ": "e", "ે": "e", "ૈ": "ai",
    "ૉ": "o", "ો": "o", "ૌ": "au",
}

_VIRAMA = "્"          # halant — suppresses the inherent vowel
_ANUSVARA = "ં"        # nasal — m before labials, else n
_CHANDRABINDU = "ઁ"    # nasalised vowel -> n
_VISARGA = "ઃ"         # -> h
_NUKTA = "઼"           # ignored
_AVAGRAHA = "ઽ"        # ignored
_LABIALS = {"p", "b", "m"}

# Gujarati digits (U+0AE6–U+0AEF) -> ASCII.
_DIGITS = {chr(0x0AE6 + i): str(i) for i in range(10)}


def _nasal_for(following: str) -> str:
    """Anusvara assimilates to the place of articulation of the FOLLOWING consonant.

    Before a labial (p/b/m) it is 'm'; otherwise (and word-finally) 'n'.
    """
    base = _CONSONANTS.get(following, "")
    return "m" if base[:1] in _LABIALS else "n"


def transliterate_gujarati(text: str) -> str:
    """Transliterate Gujarati script to ā-only Roman.

    Non-Gujarati characters (spaces, punctuation, already-Latin words, numerals) pass through
    unchanged, so mixed-script katha transcripts degrade gracefully.
    """
    out: list[str] = []
    i, n = 0, len(text)

    while i < n:
        ch = text[i]

        if ch in _CONSONANTS:
            base = _CONSONANTS[ch]
            nxt = text[i + 1] if i + 1 < n else ""
            if nxt == _VIRAMA:                       # cluster: drop inherent vowel
                out.append(base)
                i += 2
            elif nxt in _MATRAS:                     # explicit vowel sign
                out.append(base + _MATRAS[nxt])
                i += 2
            else:                                    # inherent 'a' (marked, maybe deleted later)
                out.append(base + _SCHWA)
                i += 1
            continue

        if ch in _INDEPENDENT:
            out.append(_INDEPENDENT[ch])
        elif ch in _DIGITS:
            out.append(_DIGITS[ch])
        elif ch == _ANUSVARA:
            out.append(_nasal_for(text[i + 1] if i + 1 < n else ""))
        elif ch == _CHANDRABINDU:
            out.append("n")
        elif ch == _VISARGA:
            out.append("h")
        elif ch in (_NUKTA, _AVAGRAHA, _VIRAMA):
            pass                                     # standalone -> drop
        else:
            out.append(ch)                           # passthrough (ASCII, spaces, punctuation)
        i += 1

    return _resolve_schwa("".join(out))


def _resolve_schwa(s: str) -> str:
    """Drop a word-final inherent vowel; turn every remaining inherent marker into 'a'.

    A marker is "word-final" when the next character is not a Roman letter (end of string,
    space, or punctuation) — i.e. the consonant closes the word.
    """
    chars = list(s)
    last = len(chars) - 1
    resolved: list[str] = []
    for idx, c in enumerate(chars):
        if c != _SCHWA:
            resolved.append(c)
            continue
        nxt = chars[idx + 1] if idx < last else ""
        if nxt.isalpha():       # inside a word -> keep the vowel
            resolved.append("a")
        # else: word-final schwa -> deleted
    return "".join(resolved)
