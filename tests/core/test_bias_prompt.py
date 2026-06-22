"""Tests for the Whisper bias-prompt builder (stage 1 of correction)."""
from w1_core.correction.bias_prompt import _estimate_tokens, build_initial_prompt


def test_empty_seed_yields_empty_prompt():
    assert build_initial_prompt(budget=224, seed=[]) == ""


def test_prompt_is_formatted_and_contains_seed_terms():
    out = build_initial_prompt(budget=224, seed=["mandir", "darshan", "satsang"])
    assert out.startswith("Glossary: ") and out.endswith(".")
    assert "mandir" in out and "satsang" in out


def test_budget_truncates_and_never_overflows():
    seed = [f"term{i}" for i in range(500)]  # far more than any budget allows
    out = build_initial_prompt(budget=40, seed=seed)
    used = 4 + sum(_estimate_tokens(t) for t in out[len("Glossary: ") : -1].split(", "))
    assert used <= 40
    # a larger budget includes strictly more terms
    assert build_initial_prompt(budget=200, seed=seed).count(",") > out.count(",")


def test_tiny_budget_includes_nothing():
    assert build_initial_prompt(budget=4, seed=["mandir", "darshan"]) == ""


def test_real_seed_fits_default_budget():
    out = build_initial_prompt()  # uses the loaded bias seed
    assert out.startswith("Glossary: ")
    # conservative token estimate must stay within Whisper's prompt window
    body = out[len("Glossary: ") : -1].split(", ")
    assert 4 + sum(_estimate_tokens(t) for t in body) <= 224
