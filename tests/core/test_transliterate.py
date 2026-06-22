"""Tests for the Gujarati-script -> ā-only Roman transliterator (katha mode)."""
import pytest

from w1_core.correction.transliterate import transliterate_gujarati


@pytest.mark.parametrize(
    "gujarati, roman",
    [
        ("મંદિર", "mandir"),                 # word-final schwa deletion + anusvara->n
        ("કથા", "kathā"),                    # matra ā retained
        ("ભગવાન", "bhagavān"),               # long-a kept, final schwa dropped
        ("સ્વામી", "svāmi"),                 # virama cluster + ī->i
        ("શાંતિ", "shānti"),                 # anusvara before dental -> n
        ("અંબરીષ", "ambarish"),              # anusvara before labial -> m; ષ -> sh
        ("સ્વામિનારાયણ", "svāminārāyan"),    # full name, final schwa dropped
        ("હરિ", "hari"),                     # short i kept, no final schwa to drop
    ],
)
def test_known_terms(gujarati, roman):
    assert transliterate_gujarati(gujarati) == roman


def test_only_diacritic_is_long_a():
    out = transliterate_gujarati("ગુણાતીતાનંદ સ્વામી શ્રીજી મહારાજ અક્ષરધામ")
    for c in out:
        assert c.isascii() or c == "ā", f"unexpected non-ascii/diacritic char: {c!r}"


def test_mixed_script_passthrough():
    # Latin words, digits and punctuation survive unchanged around Gujarati.
    assert transliterate_gujarati("Jay મંદિર, 2026!") == "Jay mandir, 2026!"


def test_empty_string():
    assert transliterate_gujarati("") == ""


def test_gujarati_digits_become_ascii():
    assert transliterate_gujarati("૧૨૩") == "123"
