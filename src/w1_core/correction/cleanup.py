"""Light disfluency + spoken self-correction cleanup. Deliberately conservative.

This stage NEVER changes meaning — it only removes verbal filler and resolves explicit spoken
self-corrections ("X, I mean Y" -> Y). It runs before glossary correction and is fully
toggleable, because for clinical dictation even light edits must be opt-out-able.
"""
from __future__ import annotations

import re

# Standalone filler only (whole-word) — never touches content words.
_FILLER = re.compile(r"(?<!\w)(?:um+|uh+|er+|erm+|hmm+)\b[,]?\s?", re.IGNORECASE)

# Explicit spoken self-correction: "<word>, I mean <Y>" -> "<Y>".
# Conservative by design: removes only the SINGLE immediately-corrected word + an unambiguous
# cue ("I mean"/"I meant"/"scratch that"). Cues like "sorry"/"rather" are excluded — they occur
# too often in ordinary speech ("I'm sorry I'm late") and would delete real content.
_SELF_CORRECTION = re.compile(
    r"\b\w+[,]?\s+(?:i mean|i meant|scratch that)[,]?\s+",
    re.IGNORECASE,
)

_MULTISPACE = re.compile(r"\s{2,}")


def cleanup_text(text: str, *, remove_fillers: bool = True, apply_self_corrections: bool = True):
    """Return (clean_text, applied_log)."""
    applied: list[dict] = []

    if apply_self_corrections:
        new = _SELF_CORRECTION.sub("", text)
        if new != text:
            applied.append({"rule_id": "cleanup:self_correction", "label": "spoken self-correction", "count": 1})
            text = new

    if remove_fillers:
        new = _FILLER.sub("", text)
        if new != text:
            applied.append({"rule_id": "cleanup:filler", "label": "filler removed", "count": 1})
            text = new

    collapsed = _MULTISPACE.sub(" ", text).strip()
    return collapsed, applied
