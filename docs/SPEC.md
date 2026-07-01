# W1 System Specification

W1 is a local macOS dictation app. Hold Right-Option, speak, release; corrected text is pasted
into the focused app. Whisper runs on-device via Apple MLX. Nothing leaves the machine.

Version: 1.1.0. Platform: Apple Silicon macOS 13+. Python 3.12.

## 1. Architecture

Three layers, boundary enforced by import-linter (`w1_core` may not import any desktop,
audio-device, or ML library at module level):

```
src/w1_core     portable engine: config, pipeline, correction, backends (lazy ML imports)
src/w1_data     generated JSON: glossary, terminology rules, protected terms, bias seed
src/w1_macos    adapter: menu-bar app, floating widget, hotkey, mic, paste, focus, panel
```

`w1_data` is generated from the Mandir web app's TypeScript rule files by
`scripts/sync_rules_from_ts.py`. It is never hand-edited. Current counts: 64 rules,
20 protected terms, 74 bias terms.

## 2. Runtime pipeline (one dictation cycle)

```
Right-Option down
  -> Controller.start_recording          sounddevice InputStream, 16 kHz mono float32
       audio callback: frames buffered; RMS -> level 0..11 -> widget waveform (live)
Right-Option up
  -> Controller.stop_recording           stream closed, frames concatenated
  -> worker thread: transcribe_and_correct(audio, config)
       1. bias prompt      build_initial_prompt(224 tokens) from bias seed
                           (skipped in Gujarati mode; it would skew decoding)
       2. transcribe       MLXWhisperBackend -> text + per-segment
                           avg_logprob / no_speech_prob
       3. artifact gate    known Whisper hallucinations ("thank you.", "[BLANK_AUDIO]",
                           "you", ...) -> gated, reason "artifact"
       4. confidence gate  mean no_speech_prob > 0.6 or mean avg_logprob < -1.0
                           -> gated, reason "low_confidence"; never gates without
                           segment evidence
       5a. Gujarati mode   transliterate_gujarati(text): syllable walk over U+0A80..U+0AFF,
                           word-final schwa deletion, anusvara place assimilation,
                           output is ASCII plus the single diacritic ā
       5b. other modes     correct(text, config):
                           cleanup (fillers, self-corrections; deletions off in raw mode)
                           -> mask protected terms -> fuzzy OOV snap (off in raw)
                           -> mode-filtered terminology rules -> unmask
  -> result routing
       gated       -> widget plays red X morph, collapses to rest; nothing pasted
       text, focus is editable        -> inject.paste_and_restore (clipboard preserved)
       text, no editable focus (AX)   -> PastePanel floats the text; global Cmd+Shift+V
                                         pastes it later, then disarms
  -> Controller returns to idle
```

Modes (menu labels -> CorrectionMode values):
Dictate = raw (verbatim, clinical-safe), Default = dictation (sacred terms only),
Clean + = document (adds editorial rules), Gujarati (katha) = gujarati (language forced
to "gu", ā-only Roman output).

Model: `mlx-community/whisper-large-v3-turbo` (~1.5 GB, downloaded once to the Hugging Face
cache). Swappable via `W1Config.model_id`.

## 3. UI

- Menu bar: monochrome template icon (filled while active), mode switcher, Relaunch, About.
- Floating widget: borderless NSPanel + frosted glass, screen-bottom centre. States: idle
  (static line, 44 px lozenge), listening (9-bar waveform, 12 amplitude frames driven by live
  mic RMS, 86 px pill), processing (rotating dots), rejected (red X, then collapse). Frames
  are pre-rendered PNGs; regenerate with `scripts/gen_widget_frames.py` (headless Chrome).
- Paste panel: separate glass NSPanel showing held text with a Cmd+Shift+V footer.

## 4. Quality gates

- 52 unit tests (`pytest tests/ -q`), 96% coverage over w1_core.correction/pipeline/config,
  gate at 80%.
- import-linter contract: w1_core stays platform-agnostic.
- `./w1 doctor` checks deps, model, rule data.
- Golden behaviours covered by tests: hallucination gating, confidence gating on synthetic
  segments, Gujarati transliteration (mandir, kathā, bhagavān, svāminārāyan), protected-term
  invariance, bias-prompt budget.

## 5. Distribution

Two supported paths.

Developer path (fully working today):
```
git clone https://github.com/jp-sapio-health/w1.baps.solutions.git w1
cd w1 && ./install.sh && ./w1 app
```
Grant Microphone, Accessibility, Input Monitoring to the terminal.

Packaged app (`packaging/`): py2app 0.28.10 builds `dist/W1.app`, then `build.sh` signs it
with the first Apple Development identity in the keychain (override with `W1_SIGN_IDENTITY`)
and packages `W1.dmg` from the signed copy. Build constraints, all encoded in
`packaging/setup_app.py` and `build.sh`:

- run py2app from `packaging/` so setuptools does not ingest the root pyproject
  (its install_requires is rejected by py2app)
- setuptools < 80 (py2app uses the removed legacy keyword)
- exclude torch (mlx-whisper weight-conversion dep, unused at inference)
- point builtin zlib at a real extension .so (uv standalone CPython quirk)
- sign OUTSIDE iCloud paths (iCloud stamps xattrs codesign rejects); never run the
  installed app from an iCloud-synced folder
- `LSEnvironment PYTHONDONTWRITEBYTECODE=1` so first launch cannot write .pyc into the
  bundle and break the signature seal

macOS permissions bind to the signing identity, so grants persist across rebuilds signed
with the same certificate. The bundle id is `health.baps.w1`.

## 6. Website

`web/`: Vite + React 19 + darwin-ui (Tailwind v4), light theme, BAPS glass navbar, install
and CLI sections rendered as dark terminal code boxes in self-hosted Ubuntu Sans Mono.
Deployed on Vercel; root `vercel.json` builds the `web/` subdirectory. Live at
https://w1.baps.solutions.

## 7. Known limits

- Whisper hallucination gating is heuristic; rare artifacts may pass.
- Gujarati schwa deletion is word-final only; medial schwa needs a lexicon.
- The packaged app is signed with a Development certificate, not notarized. First launch on
  another Mac requires right-click Open. Wider distribution needs a Developer ID and
  notarization (docs/PACKAGING.md).
- Focus detection is conservative: when the Accessibility API is unsure, W1 pastes rather
  than floating the panel.
