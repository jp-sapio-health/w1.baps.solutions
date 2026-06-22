<h1 align="center">वाणी · W1</h1>

<p align="center"><em>Local, privacy-first dictation. Press a key, speak, it types.</em></p>

> **Is my voice private?** Yes. W1 runs OpenAI's Whisper **entirely on your Mac** via Apple
> MLX. Nothing — no audio, no text — ever leaves your computer. No cloud, no account, no
> subscription. It is built to safely handle clinical and personal dictation.

W1 replaces paid dictation apps (e.g. Wispr Flow) and adds one thing they can't do: it knows
**BAPS Gujarati sacred terminology**. Speak natural English with terms like *Akshardham,
Pramukh Swami Maharaj, Vachanamrut, satsang, mandir, murti, darshan* mixed in, and they come out
in correct canonical spelling — while your ordinary English stays exactly as you said it.

```
   speak  ──▶  Whisper (MLX, on-device)  ──▶  bilingual correction  ──▶  pasted into any app
                                              (BAPS terms · never your clinical English)
```

## Quickstart
Apple Silicon Mac, [uv](https://docs.astral.sh/uv/) installed:

```bash
git clone <repo-url> w1 && cd w1
./install.sh          # venv + deps + model download + permission links
./w1 app             # launch the menu-bar app + floating widget
```

Then grant **Microphone**, **Accessibility**, and **Input Monitoring** when prompted (the
installer prints the direct System Settings links). Hold **Right-Option** and speak.

## Status
🚧 **In active development** — see [`PLAN.md`](./PLAN.md) for the full architecture and phased
build. v1 targets a single Mac (Apple Silicon); a signed, packaged app for wider sharing is a
planned phase.

## How it works
- **Hotkey:** hold **Right-Option** to talk (push-to-talk), or double-tap to toggle. Fully
  rebindable. Text is inserted into whatever app is focused.
- **Four modes,** switchable from the menu bar:
  - **Dictate** — verbatim; no terminology changes (clinical/normal dictation).
  - **Default** — corrects BAPS sacred terms, leaves your ordinary English untouched.
  - **Clean +** — Default plus light editorial tidy-up (filler removal, place/date casing).
  - **Gujarati (katha)** — transcribes spoken Gujarati and outputs Roman transliteration using
    the BAPS *ā*-only diacritic rule (keeps the long-*ā* macron, strips all others).
- **Confidence gate:** if Whisper isn't confident the audio was real speech, nothing is pasted —
  the widget flashes a red ✕ instead of inserting noise.
- **Model:** `whisper-large-v3-turbo`, swappable in one config line.

## CLI
| Command | What it does |
|---------|--------------|
| `./w1 app` | Launch the menu-bar app + floating widget |
| `./w1 dictate` | Record from the mic and paste the corrected text |
| `./w1 transcribe FILE [--mode …]` | Transcribe an audio file |
| `./w1 correct "text" [--mode …]` | Run text through the correction engine only |
| `./w1 doctor` | Check environment (deps, model, rule data, permission hints) |

`./w1` runs against the live source tree (no reinstall needed while developing).

## Tests
```bash
.venv/bin/python -m pytest tests/ -q                      # unit tests
.venv/bin/python -m pytest tests/ --cov=w1_core          # with coverage
.venv/bin/lint-imports                                    # platform-boundary contract
```

## Layout
`src/w1_core` — portable engine · `src/w1_data` — generated glossary/rule data ·
`src/w1_macos` — the macOS app · `scripts/` — rule sync, accuracy harness, widget-frame
generator · `docs/` — setup.

## Glossary source of truth
Sacred terminology is **generated** from the Mandir web app's rule files via
`scripts/sync_rules_from_ts.py` — never hand-edited here.

---
*Built for sewa. Private by design.*
