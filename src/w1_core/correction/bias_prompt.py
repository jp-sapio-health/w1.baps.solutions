"""Stage 1 of correction: build the Whisper ``initial_prompt`` from the curated bias seed.

Whisper's prompt window is ~224 tokens, so we cannot list all ~230 glossary terms. We pack the
highest-value seed terms until the budget is reached (a conservative word->token estimate) and
assert we never overflow.
"""
from __future__ import annotations

from .loader import load_rule_data


def _estimate_tokens(term: str) -> int:
    # Conservative: ~1.3 tokens per whitespace word, +1 for the separator.
    return max(1, round(len(term.split()) * 1.3)) + 1


def build_initial_prompt(budget: int = 224, seed: list[str] | None = None) -> str:
    """Assemble a comma-separated glossary prompt that fits within ``budget`` tokens."""
    terms = list(seed) if seed is not None else list(load_rule_data().bias_seed)
    chosen: list[str] = []
    used = 4  # "Glossary: " + trailing "."
    for term in terms:
        cost = _estimate_tokens(term)
        if used + cost > budget:
            break
        chosen.append(term)
        used += cost
    if not chosen:
        return ""
    return "Glossary: " + ", ".join(chosen) + "."
