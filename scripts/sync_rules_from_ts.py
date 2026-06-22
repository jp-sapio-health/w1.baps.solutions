#!/usr/bin/env python3
"""Generate w1_data/*.json from the Mandir web app's TypeScript rule files.

This is a ONE-WAY sync: the Mandir web app (``Mandir/web/lib/rules/*.ts``) remains the
single source of truth for BAPS sacred terminology. We never hand-port the rules into
Python — we parse the ``.ts`` files and emit language-neutral JSON that ``w1_core``
consumes as data. A term-count check guards against silent drift.

Why this matters: the terminology rules are SIX distinct families, not one. Only the
``sacred_terminology`` family is safe to apply during live dictation; the editorial
families (forbidden-vocab, hedging, place/personal-name, date) would corrupt ordinary
clinical/English speech and are tagged ``document``-mode (off by default).

Usage:
    python3 scripts/sync_rules_from_ts.py [--src DIR] [--out DIR] [--check]

``--check`` parses and reports counts without writing (CI drift guard).

Pure standard library — no third-party dependencies, no network.
"""
from __future__ import annotations

import argparse
import codecs
import json
import re
import sys
from pathlib import Path

# --- Paths -------------------------------------------------------------------
_HERE = Path(__file__).resolve()
_REPOS = _HERE.parents[2]  # w1/scripts/sync_rules_from_ts.py -> Repositories/
DEFAULT_SRC = _REPOS / "Mandir" / "web" / "lib" / "rules"
DEFAULT_OUT = _HERE.parents[1] / "src" / "w1_data"

# Source-array -> (family, default-enabled modes). ``raw`` mode bypasses ALL families.
RULE_FAMILIES: dict[str, tuple[str, list[str]]] = {
    "TERMINOLOGY_RULES": ("sacred_terminology", ["dictation", "document"]),
    "PERSONAL_NAME_RULES": ("personal_name", ["document"]),
    "PLACE_NAME_RULES": ("place_name", ["document"]),
    "FORBIDDEN_VOCAB_RULES": ("forbidden_vocab", ["document"]),
    "HEDGING_RULES": ("hedging", ["document"]),
    "DATE_FORMAT_RULES": ("date", ["document"]),
}

# High-value terms that MUST seed the Whisper bias prompt even if absent from glossary.ts
# (proper nouns Whisper mangles most). Tuned later from real usage.
EXTRA_BIAS_TERMS = [
    "Swaminarayan", "Bhagwan Swaminarayan", "Pramukh Swami Maharaj", "Mahant Swami Maharaj",
    "Akshardham", "Vachanamrut", "Shriji Maharaj", "satsang", "mandir", "murti", "darshan",
    "arti", "Satpurush", "sadhu", "Swami", "thal", "annakut", "sewa", "katha", "kirtan",
]


# --- Parsers -----------------------------------------------------------------
def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_glossary(text: str) -> list[dict]:
    """Parse the ``KEY_GLOSSARY`` template literal into structured entries."""
    m = re.search(r"KEY_GLOSSARY\s*=\s*`(.*?)`", text, re.S)
    if not m:
        raise ValueError("KEY_GLOSSARY template literal not found in glossary.ts")
    block = m.group(1)
    entries: list[dict] = []
    category = None
    for raw in block.splitlines():
        line = raw.strip()
        if not line:
            continue
        head = re.match(r"^-+\s*(.*?)\s*-+$", line)  # --- CATEGORY ---
        if head:
            category = head.group(1).strip() or category
            continue
        if line.upper().startswith("MASTER THEOLOGICAL GLOSSARY"):
            continue
        if line.startswith("(use these"):
            continue
        mm = re.match(r"^([^:]+):\s+(.*)$", line)  # term: definition (split on first ": ")
        if not mm:
            continue
        term_field = mm.group(1).strip()
        definition = mm.group(2).strip()
        aliases = [t.strip() for t in term_field.split("/") if t.strip()]
        if not aliases:
            continue
        nevers = re.findall(r'NEVER(?:\s+just)?\s+["\']([^"\']+)["\']', definition)
        entries.append(
            {
                "canonical": aliases[0],
                "aliases": aliases,
                "category": category,
                "definition": definition,
                "never_alternatives": nevers,
            }
        )
    return entries


def _parse_replacement(rep: str) -> dict:
    """Parse a TerminologyRule replacement (literal string or case-preserving fn)."""
    fn = re.match(
        r"\(m[^)]*\)\s*=>\s*m\[0\]\s*===\s*'(.)'\s*\?\s*'([^']*)'\s*:\s*'([^']*)'",
        rep.strip(),
    )
    if fn:
        return {
            "type": "case_preserve",
            "when_first_char": fn.group(1),
            "if_match": fn.group(2),
            "else": fn.group(3),
        }
    lit = re.match(r"'((?:[^'\\]|\\.)*)'", rep.strip())
    if lit is not None:
        return {"type": "literal", "value": codecs.decode(lit.group(1), "unicode_escape")}
    return {"type": "unknown", "raw": rep.strip()}


# One rule per object. Anchoring on the field structure (rather than splitting on braces)
# survives regex quantifiers like \d{1,2} that contain literal braces. Pattern bodies here
# never contain an unescaped "/", so .*? to the closing delimiter is safe; replacements never
# contain a comma, so .*? up to ", rule:" is safe.
_RULE_RE = re.compile(
    r"pattern:\s*/(?P<pat>.*?)/(?P<flags>[gimsuy]*)\s*,\s*"
    r"replacement:\s*(?P<rep>.*?)\s*,\s*"
    r"rule:\s*'(?P<label>(?:[^'\\]|\\.)*)'",
    re.S,
)


def parse_rule_array(text: str, name: str) -> list[dict]:
    m = re.search(name + r"[^=]*=\s*\[(.*?)\];", text, re.S)
    if not m:
        raise ValueError(f"rule array {name} not found")
    body = m.group(1)
    family, modes = RULE_FAMILIES[name]
    rules: list[dict] = []
    for i, mo in enumerate(_RULE_RE.finditer(body)):
        rules.append(
            {
                "rule_id": f"{family}:{i:03d}",
                "family": family,
                "modes": modes,
                "pattern": mo.group("pat"),
                "flags": mo.group("flags"),
                "replacement": _parse_replacement(mo.group("rep")),
                "label": codecs.decode(mo.group("label"), "unicode_escape"),
            }
        )
    return rules


def parse_diacritics(text: str) -> dict[str, str]:
    m = re.search(r"DIACRITICS_MAP[^=]*=\s*\{(.*?)\}", text, re.S)
    if not m:
        raise ValueError("DIACRITICS_MAP not found")
    out: dict[str, str] = {}
    for k, v in re.findall(r"'((?:\\u[0-9a-fA-F]{4})|[^'])'\s*:\s*'([^']*)'", m.group(1)):
        key = codecs.decode(k, "unicode_escape") if k.startswith("\\u") else k
        out[key] = v
    return out


def parse_protected(text: str) -> list[str]:
    m = re.search(r"PROTECTED_TERMS_LIST\s*=\s*\[(.*?)\]", text, re.S)
    if not m:
        raise ValueError("PROTECTED_TERMS_LIST not found")
    return re.findall(r"'([^']+)'", m.group(1))


def build_bias_seed(glossary: list[dict], protected: list[str]) -> list[str]:
    """Auto-generate the Whisper bias seed: proper nouns + protected + high-value terms."""
    seed: list[str] = []
    seen: set[str] = set()

    def add(term: str) -> None:
        key = term.lower()
        if term and key not in seen:
            seen.add(key)
            seed.append(term)

    for t in EXTRA_BIAS_TERMS:
        add(t)
    for p in protected:
        add(p)
    for e in glossary:  # proper nouns (capitalised canonicals) are the worst-mangled
        c = e["canonical"]
        if c[:1].isupper() and " " not in c and "(" not in c:
            add(c)
    return seed


# --- Main --------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", type=Path, default=DEFAULT_SRC)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--check", action="store_true", help="report counts without writing")
    args = ap.parse_args(argv)

    gloss_txt = _read(args.src / "glossary.ts")
    term_txt = _read(args.src / "terminology.ts")
    prot_txt = _read(args.src / "protected-terms.ts")

    glossary = parse_glossary(gloss_txt)
    rules: list[dict] = []
    for name in RULE_FAMILIES:
        rules.extend(parse_rule_array(term_txt, name))
    diacritics = parse_diacritics(term_txt)
    protected = parse_protected(prot_txt)
    bias_seed = build_bias_seed(glossary, protected)

    # Drift guard: source line-count of "term:" entries should match parsed glossary count.
    raw_terms = len(
        re.findall(r"^\s*[^:\n-][^:\n]*:\s+\S", re.search(r"`(.*?)`", gloss_txt, re.S).group(1), re.M)
    )
    families = {}
    for r in rules:
        families[r["family"]] = families.get(r["family"], 0) + 1

    print("=== sync_rules_from_ts ===")
    print(f"glossary entries : {len(glossary)} (raw 'term:' lines ~{raw_terms})")
    print(f"protected terms  : {len(protected)}")
    print(f"diacritics       : {len(diacritics)}")
    print(f"terminology rules: {len(rules)}  by family: {families}")
    print(f"bias seed        : {len(bias_seed)} terms")
    dictation_rules = [r for r in rules if "dictation" in r["modes"]]
    print(f"  -> dictation-mode rules: {len(dictation_rules)} (sacred only)")
    print(f"  -> document-only rules : {len(rules) - len(dictation_rules)} (off by default)")

    if abs(raw_terms - len(glossary)) > 2:
        print(f"WARNING: glossary parse drift ({raw_terms} raw vs {len(glossary)} parsed)", file=sys.stderr)

    if args.check:
        print("--check: no files written.")
        return 0

    args.out.mkdir(parents=True, exist_ok=True)
    writes = {
        "glossary.json": glossary,
        "terminology_rules.json": rules,
        "protected_terms.json": protected,
        "diacritics.json": diacritics,
        "bias_seed.json": bias_seed,
        "_meta.json": {
            "source": str(args.src),
            "counts": {
                "glossary": len(glossary),
                "protected": len(protected),
                "diacritics": len(diacritics),
                "rules": len(rules),
                "bias_seed": len(bias_seed),
            },
            "families": families,
            "note": "Generated by sync_rules_from_ts.py — do not edit by hand. Source of truth: Mandir/web/lib/rules/*.ts",
        },
    }
    for name, data in writes.items():
        (args.out / name).write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"wrote {args.out / name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
