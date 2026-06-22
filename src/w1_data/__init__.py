"""w1_data — language-neutral rule data, generated from Mandir/web/lib/rules/*.ts.

Do not edit the JSON by hand. Regenerate with ``python scripts/sync_rules_from_ts.py``.
The Mandir web app remains the single source of truth.
"""
from __future__ import annotations

import json
from importlib import resources
from typing import Any

_DATASETS = (
    "glossary",
    "terminology_rules",
    "protected_terms",
    "diacritics",
    "bias_seed",
)


def load(name: str) -> Any:
    """Load a generated dataset by name (e.g. ``load("glossary")``)."""
    if name not in _DATASETS:
        raise KeyError(f"unknown w1_data dataset {name!r}; expected one of {_DATASETS}")
    with resources.files(__name__).joinpath(f"{name}.json").open("r", encoding="utf-8") as fh:
        return json.load(fh)
