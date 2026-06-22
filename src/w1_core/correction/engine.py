"""The two-stage correction orchestrator (stage 2 — deterministic post-correction).

Order is load-bearing: cleanup -> mask protected -> [fuzzy snap*] -> ordered terminology
rules (mode-filtered) -> unmask. Every transformation contributes to a structured log.

* The fuzzy OOV-snap stage is added in a subsequent iteration; the hook is marked below so the
  pipeline is correct and complete without it (it only adds recall, never changes these guarantees).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..config import W1Config
from .cleanup import cleanup_text
from .fuzzy import snap_fuzzy
from .protect import mask_protected, unmask_protected
from .rules import apply_terminology


@dataclass
class CorrectionResult:
    text: str
    applied: list[dict] = field(default_factory=list)


def correct(text: str, config: W1Config) -> CorrectionResult:
    """Apply the full deterministic correction chain for the configured mode."""
    applied: list[dict] = []
    mode = config.correction_mode.value

    if config.cleanup.enabled:
        # Clinical/raw mode never deletes words via self-correction — too risky for notes.
        self_corr = config.cleanup.apply_self_corrections and mode != "raw"
        text, log = cleanup_text(
            text,
            remove_fillers=config.cleanup.remove_fillers,
            apply_self_corrections=self_corr,
        )
        applied.extend(log)

    masked, store = mask_protected(text)

    # Fuzzy snap of OOV near-misses (off in raw/clinical mode — never invent sacred terms there).
    if config.fuzzy.enabled and mode != "raw":
        masked, fuzzy_log = snap_fuzzy(
            masked,
            min_similarity=config.fuzzy.min_similarity,
            min_term_length=config.fuzzy.min_term_length,
        )
        applied.extend(fuzzy_log)

    ruled, rule_log = apply_terminology(masked, mode)
    applied.extend(rule_log)

    return CorrectionResult(text=unmask_protected(ruled, store), applied=applied)
