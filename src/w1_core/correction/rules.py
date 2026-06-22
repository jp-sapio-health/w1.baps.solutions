"""Apply the mode-filtered terminology rules in their canonical (source) order.

Dictation mode applies only the ``sacred_terminology`` family; document mode additionally
applies the editorial families; raw mode applies none. Each firing is recorded in a
structured log so "why did my word change" is answerable without re-running audio.
"""
from __future__ import annotations

from .loader import load_rule_data


def apply_terminology(text: str, mode: str) -> tuple[str, list[dict]]:
    """Apply every rule whose ``modes`` include ``mode``. Returns (text, applied_log)."""
    data = load_rule_data()
    log: list[dict] = []
    for rule in data.rules:
        if mode not in rule.modes:
            continue
        new_text, count = rule.apply(text)
        if count:
            log.append(
                {"rule_id": rule.rule_id, "label": rule.label, "family": rule.family, "count": count}
            )
            text = new_text
    return text, log
