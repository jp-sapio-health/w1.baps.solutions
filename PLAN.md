# w1 — Implementation Plan

> **Vāṇī** (Sanskrit/Gujarati: *speech, the spoken word*) — a free, local, privacy-first
> dictation tool that replaces Wispr Flow. Press a hotkey, speak, and your words are typed
> into the focused app. 100% on-device. Bilingual-aware: natural English stays natural;
> BAPS Gujarati sacred terms come out in correct canonical spelling.

**Status:** Planning complete · authored from the BMAD party-mode synthesis (Mary, Winston,
Sally, Amelia, Quinn, John, Paige → BMad Master). This document is the single source of truth
for execution. No time/effort estimates by design — phases are logical, complete, and each
independently shippable.

---

## 1. What we are building (and explicitly not)

**The job:** eliminate the editing tax. Jay dictates sewa notes, clinical notes, founder
emails, and code comments. The 95% English path must match Wispr Flow on the boring stuff
(speed, punctuation, reliability, works in any app). The 5% that matters — BAPS terms like
*Akshardham, Pramukh Swami Maharaj, Vachanamrut, satsang, mandir, murti, darshan* — must come
out perfect, which vanilla Whisper does not do.

**In scope for v1:** local hotkey-driven batch dictation, MLX large-v3-turbo, two-stage
bilingual correction, dictation/raw modes, menu-bar app, guided permissions, offline accuracy
harness, one-command install (for Jay).

**Explicitly OUT (deferred or never):** live streaming insertion (Phase 2), signed/notarized
`.app` for non-technical volunteers (Phase 3a), iOS/Android (Phase 3b), and — *never* — cloud
sync, AI rewrite/commands, multi-device, voice-driven editing. Parity means matching Wispr's
dictation core, not its whole product.

---

## 2. Architecture — layered for portability

The bet: the **correction engine is the crown jewel**, and it must be the most portable,
most tested part of the repo so iOS/Android inherit bilingual correction for free. The
platform boundary is enforced **mechanically** (import-linter + a CI job that installs only
the core and runs the suite), not by discipline.

| Layer | Responsibility | Tech |
|---|---|---|
| **`w1_core`** | Platform-agnostic engine. AudioBuffer, `TranscriptionBackend` Protocol, two-stage correction, hallucination/empty gate, typed config, the single `pipeline` entrypoint. **Zero desktop/ML/audio imports.** | Python 3.12, pydantic, rapidfuzz, jellyfish |
| **`w1_data`** | Language-neutral rule data, **generated** (never hand-ported) from `Mandir/web/lib/rules/*.ts`. Glossary, mode-tagged terminology rules, protected terms, diacritics, bias seed. | JSON package data + `sync_rules_from_ts.py` |
| **`w1_asr`** (in `w1_core/backends`) | Concrete backends behind the Protocol. `MLXWhisperBackend` (default, Apple Silicon), `FasterWhisperBackend` (CI-validated fallback), `MockBackend` (tests). ML libs lazy-imported. | mlx-whisper `[mlx]`, faster-whisper `[faster]` |
| **`w1_macos`** | **All** desktop deps live here only. Global hotkey (toggle + PTT), mic capture, clipboard paste+restore, menu-bar states, onboarding, undo. | rumps, pynput, sounddevice, pyperclip |
| **Tooling/tests** | Fast pure unit suite (headless CI), gated audio/WER suite (Jay's Mac), offline eval harness. | pytest, jiwer, import-linter |

**Backend seam:** `w1_core/backends/base.py` defines a runtime-checkable Protocol —
`transcribe(audio: np.ndarray, *, initial_prompt: str|None, language: str|None) ->
TranscriptionResult(text, language, segments[...])`. `initial_prompt` is passed **per call**,
so all biasing logic stays in core where the glossary lives; swapping backends never touches
biasing. `select_backend(config)` picks MLX on `arm64 + import mlx`, else faster-whisper.

**Data flow:**
```
mic frames (adapter) → AudioBuffer.append (core)
  → on stop: finalize() → float32 16kHz mono ndarray
  → backend.transcribe(audio, initial_prompt=build_initial_prompt(seed, budget=224))
  → raw text + segment confidences
  → hallucination/empty gate (min duration, no_speech_prob, artifact denylist e.g. "Thank you.")
       ↳ if gated → "nothing to inject" (no paste, menubar blip)
  → correction.engine.correct(text, mode):
       (1) mask protected terms
       (2) conservative fuzzy/phonetic snap of OOV sacred near-misses → canonical
       (3) ordered regex rule families ENABLED FOR THE MODE
       (4) unmask
     → corrected text + structured (rule_id, before, after, span) log
  → adapter inject.paste_and_restore()  (snapshot clipboard → set text → Cmd+V → restore)
ZERO network. No raw audio or transcript written to disk/logs.
```

### Repo layout
```
w1/
  pyproject.toml                 # single package, requires-python ==3.12.*, extras: [mlx][faster][macos][eval][dev]
  install.sh / install.command   # one-command bootstrap (venv, pinned deps, model pull, permission deep-links)
  src/
    w1_core/                   # PLATFORM-AGNOSTIC. iOS-importable.
      config.py                  # pydantic W1Config
      audio/{buffer.py,types.py} # AudioBuffer, SAMPLE_RATE=16000
      backends/{base.py,factory.py,mock.py,mlx_whisper.py,faster_whisper.py}
      correction/{engine.py,bias_prompt.py,protect.py,fuzzy.py,rules.py,loader.py}
      pipeline.py                # transcribe_and_correct(audio, config) -> InjectResult
    w1_data/                   # GENERATED language-neutral JSON (package data)
      glossary.json terminology_rules.json protected_terms.json diacritics.json bias_seed.json
    w1_macos/                  # PLATFORM ADAPTER. all desktop deps here only.
      app.py hotkey.py mic.py inject.py controller.py onboarding.py doctor.py
  scripts/
    sync_rules_from_ts.py        # one-way TS→JSON regen from Mandir/web/lib/rules/*.ts
    eval.py                      # offline scorer: WER + glossary recall + protected recall + false-correction diff
  tests/
    core/                        # NO macOS, NO audio, NO model (MockBackend)
    data/golden/                 # raw→expected fixtures + pure-English do-not-corrupt corpus
    audio/                       # WER fixtures (wavs gitignored), @pytest.mark.slow
    macos/                       # adapter tests, skipped headless
  docs/  README.md  docs/macos/{first-run-permissions,gatekeeper,troubleshooting}.md  add-your-own-terms.md
  # future siblings, no core change: src/w1_ios/  src/w1_android/
```

---

## 3. The correction design (the crown jewel)

### Two correction MODES (the single most important safety decision)
The `.ts` terminology rules are **six distinct families**, not one safe set. Splitting them
prevents corrupting Jay's clinical/normal English:

- **`dictation` (DEFAULT):** sacred-terminology family + diacritics map + protected-term
  canonical casing **only**. (saint→Swami, temple→mandir, aarti→arti, scripture→shastra,
  congregation→satsang, fellowship→satsang, recitation→mukhpath, Shrijimaharaj→Shriji Maharaj…)
- **`raw` (per-session toggle):** bypasses **all** terminology rules — Unicode-safe insertion
  + protected-term casing only. The **clinical-note path** ("temple" stays anatomical, "Maya"
  stays a name). Glanceable in the menu bar so Jay knows before he speaks.
- **`document` (off by default, not v1-critical):** additionally enables the editorial
  families — `forbidden_vocab` (legendary→renowned, milestone→occasion), `hedging` (deletes
  "perhaps"/"probably"), `place_name`, `personal_name`, `date`. Built and tested, surfaced later.

### Fuzzy correction guardrails (prevents over-correction of English)
Fuzzy snapping fires **only** when ALL hold: token is **OOV** (not a common English word) ·
similarity above a **conservative threshold (~88)** · term length **≥ 4 chars**. Ultra-short
glossary terms (`man, dal, jal, tej, gau, jad`) are **exact-match only, never fuzzy** — they
collide with ordinary English ("hand", "deal"). Double Metaphone (jellyfish) is an *additional*
gate, not the primary mechanism.

### Invariants (high-signal tests)
- Protected terms (the 20) are **masked first**, never fuzzy targets, round-trip byte-identical.
- The pure-English **do-not-corrupt corpus** must come out **byte-identical** in dictation mode.
  False-correction count **== 0 is a hard release blocker**.

---

## 4. Build phases (risk-first)

Each phase ends with the code in a correct, shippable state. Nothing left broken between phases.

### Phase 0a — Risk spike: macOS permission + hotkey surface (HEADLESS, no Whisper)
Prove the scariest integration first. Deliverables: headless pynput listener (Right-Option
hold = PTT, double-tap = toggle) printing events across 3+ apps; clipboard round-trip spike
(snapshot → set Gujarati/Devanagari Unicode → synth Cmd+V → delayed restore, assert
byte-identical + prior clipboard restored); findings note on TCC identity stability for a
uv-launched Python and exact System Settings deep-links; confirmed conflict-free default hotkey
on macOS 26. **Exit:** hotkeys fire reliably across apps; Unicode paste lands and restores;
signed-launcher decision recorded.

### Phase 0b — Risk spike: correction beats vanilla Whisper (FILE-BASED, no UI)
De-risk the only thing that justifies the product. Deliverables: `sync_rules_from_ts.py` →
tagged `w1_data/*.json` with term-count check; `w1 transcribe sample.wav` printing
raw-vs-corrected side by side + a pure-text `correct` mode; captured **vanilla baseline** (WER
+ glossary recall) on 5–10 of Jay's real clips vs the same after correction (headline delta);
first cut of the frozen acceptance set (20 golden bilingual sentences + pure-English negative
corpus). **Exit:** every sacred term in the golden set is exact canonical; negative corpus
byte-identical (false-correction == 0); corrected output beats vanilla on glossary recall by a
clear margin; gold-spelling source-of-truth declared.

### Phase 1 — v1 MVP: Jay's daily driver (the line in the sand)
Integrate both spikes into a long-running local macOS app. Deliverables: `w1_core` finalized
behind the single pipeline entrypoint (AudioBuffer, Protocol + MLXWhisperBackend + factory,
hallucination gate, two-stage correction, pydantic config; import-linter + core-only CI both
green); `w1_macos` adapter (menu bar with idle/listening/processing/error + audio cues;
toggle gets recording pill + auto-stop timeout; sounddevice capture; clipboard paste+restore;
undo-last-insertion; both hotkey modes config-switchable); per-session dictation/raw toggle;
first-run onboarding (3-permission guided flow + live scratch-box test); single config file;
`w1 doctor`; startup zero-network assertion; offline eval harness wired to the frozen set;
fast unit suite green on a core-only install with ≥80% coverage on correction. **Exit:** 20
golden sentences pass with zero edits to BAPS terms + correct casing; negative corpus
byte-identical; glossary recall ≥95% (≥98% protected); clipboard restore verified across
Mail/VS Code/Slack/Notes/browser incl. Unicode; empty/silence inserts nothing; runs as a launch
agent, survives reboot; Jay uses it as default (off Wispr Flow) for one week.

### Phase 2 — Live streaming insertion
Upgrade batch→streaming behind the same config, no core/correction rewrite. **Exit:** streaming
passes the same golden + negative gates as batch; batch remains fully functional and selectable.

### Phase 3a — Volunteer-ready macOS distribution (signed/notarized .app)
Developer-ID-signed + notarized `.app` (py2app/briefcase) as a drag-to-Applications `.dmg`;
first-run permission wizard with screenshots + Gatekeeper "Open Anyway" path; user glossary in
`~/Library/Application Support/w1/` (updates merge-not-replace, timestamped backup);
privacy-first README + symptom-first troubleshooting; an "add/correct a term" affordance.
**Exit:** a non-developer on a clean macOS 26 account reaches first dictation from README +
wizard alone; quarantined build clears Gatekeeper via documented steps; updates preserve custom
glossary.

### Phase 3b — Mobile capability (iOS / Android)
Reuse **unchanged** `w1_core` + `w1_data`; add only a mobile adapter + an on-device backend
(e.g. whisper.cpp/CoreML) satisfying the same Protocol. **Exit:** core imported unchanged;
mobile backend satisfies the Protocol; golden + negative gates pass on-device.

---

## 5. Test strategy

- **3 suites:** `tests/core/correction` (pure, <2s, ≥80% branch coverage, ~100% achievable);
  `tests/core/capture` (hotkey/mic/clipboard with mocked OS); `tests/audio` (WER/recall,
  `@pytest.mark.slow`, skip-if-no-model, runs on Jay's Mac).
- **Headless-core CI job:** install **only** the core, import `w1_core`, run the correction
  suite → proves zero desktop/ML deps. Paired with an import-linter contract.
- **Golden positive corpus:** 20 bilingual sentences (one per glossary category) + per-rule
  near-miss→canonical cases (Temple→Mandir, aarti→arti, Shrijimaharaj→Shriji Maharaj,
  "Akshar dham"→"Akshardham"). Recall counts only exact canonical form **including casing**.
- **Negative do-not-corrupt corpus (highest-value asset):** "the patient's temple was tender",
  "a project milestone for our main stakeholder", "Greek mythology", "I had dal", "I gave him a
  hand", Maya/seven/karma homophones → **zero** mutations in dictation mode.
- **Mode-isolation, protected-term invariance, fuzzy guardrail, diacritics coverage, capture
  edge cases** (no mic, silence, very long audio, rapid toggle race, restore-in-finally),
  **backend tests** (select_backend, core imports neither mlx nor rumps, budget=224 assertion,
  hallucination gate).
- **Privacy hygiene:** committed clips are scripted/neutral (never real PHI); wavs gitignored;
  a test asserts no transcript/audio hits disk/logs and zero outbound network during a cycle.
- **Accuracy gates:** assert **strictly** on the deterministic correction layer (glossary recall
  ≥95%, ≥98% protected, false-correction == 0); assert **loosely** (threshold/trend, never exact
  string) on the probabilistic transcription layer (WER, bucketed clean vs realistic).

---

## 6. Dependencies (all pinned; all published > 1 month ago)

**Core (`w1_core`, always installed):**
| Package | Pin | Published |
|---|---|---|
| pydantic | 2.13.4 | 2026-05-06 |
| rapidfuzz | 3.14.5 | 2026-04-07 |
| jellyfish | 1.2.1 | 2025-10-11 |
| pyyaml | 6.0.3 | 2025-09-25 |

**Extras:** `[mlx]` mlx-whisper 0.4.3 (2025-08-29) · `[faster]` faster-whisper 1.2.1
(2025-10-31) · `[macos]` rumps 0.4.0 (2022-10-15), pynput 1.8.2 (2026-05-12), sounddevice
0.5.5 (2026-01-23), pyperclip 1.11.0 (2025-09-26) · `[eval]` jiwer 4.0.0 (2025-06-19) ·
`[dev]` pytest 9.0.3 (2026-04-07), pytest-cov 7.1.0 (2026-03-21), import-linter 2.11 (2026-03-06)

**Avoided (shipped < 1 month ago):** soundfile 0.14.0, scipy 1.18.0, pytest 9.1.1,
huggingface-hub 1.20.1, tqdm 4.68.3 → use older safe pins (e.g. tqdm 4.67.3, huggingface-hub
≤1.15.0) or stdlib (`wave`) instead. Transitive versions are locked in `uv.lock` and verified
> 1 month old before install.

**System:** Python 3.12.13 (already installed via uv — system 3.14 avoided), ffmpeg 8.1
(present), portaudio (brew, for sounddevice). Model: `mlx-community/whisper-large-v3-turbo`
(~1.5 GB; ~38 GB free).

---

## 7. Top risks & mitigations
1. **Editorial rules corrupt clinical English** *(high)* → mode-tagged data, dictation default
   = sacred-only; raw mode bypasses all.
2. **macOS 26 TCC silently drops hotkey/paste grants** *(high)* → Phase 0a proves it headless;
   app detects missing permissions and blocks with guided onboarding + deep-links.
3. **Fuzzy over-corrects English → sacred term** *(high)* → OOV-only, ~88 threshold, ≥4 chars,
   English stoplist, ultra-short terms exact-only.
4. **Whisper hallucinates "Thank you." into silence** *(high)* → core gate: min-duration +
   no_speech_prob + artifact denylist → "nothing to inject".
5. **Platform boundary erodes** *(high)* → import-linter contract + core-only CI install.
6. **Clipboard restore race** *(medium)* → snapshot → paste → restore after app-safe delay in
   a finally block; dedicated restore/undo hotkey.
7. **Supply chain** *(medium)* → every pin > 1 month old; flag + ask before install.

---

## 8. Decisions locked (Jay's autonomy grant + sensible defaults)
- **Acceptance bars:** WER ≤5% (loose/trend, bucketed); glossary recall ≥95% (≥98% protected,
  exact canonical incl. casing); **false-correction == 0 = hard gate**.
- **Latency target:** <1.5s stop→text on a ~15s utterance (M1 Pro). Target, not gate.
- **Gold source of truth:** the `.ts` files (web-app canonical, machine-readable). PDF
  reconciliation deferred.
- **Bias seed:** auto-generated ~50-term default (proper nouns + protected + high-mangling
  names); tune from real usage later.
- **Default hotkey:** hold Right-Option = PTT, double-tap Right-Option = toggle; Ctrl+Opt+Space
  documented alternative; fully rebindable. Never Cmd+M.
- **Clinical/non-BAPS use:** YES → raw mode + sacred-only default are mandatory in v1.
- **Kill-switch:** v1 includes a mic hard-off / pause hotkey.
- **Signing:** v1 ships unsigned (accept TCC wobble, documented); signing deferred to 3a unless
  Phase 0a proves it unworkable.

## 9. Open items needing Jay
- **Supply-chain go/no-go:** approve the §6 dependency table before any install.
- **Test audio:** does an existing corpus of Jay's real speech exist to mine, or record the
  20 golden sentences + a few free-form clips fresh? (Needed for Phase 0b/1 acceptance.)
- **Permissions:** Jay grants Microphone + Accessibility + Input Monitoring when Phase 0a/1 land.
- **Sharing channel** (Phase 3a): named volunteers vs open community; private GitHub release vs
  handed-over `.dmg` — sets notarization urgency. Deferred.

---

## 10. Scope additions (Jay, 2026-06-21)

### 10.1 Two surfaces: menu-bar **and** floating widget (both, v1)
- **Menu-bar (toolbar) item** (`rumps`): always present. Icon reflects state (idle/listening/
  processing/error) and active correction mode (sewa/raw). Menu: toggle dictation↔raw, switch
  hotkey mode, "last corrections" view, pause/mic-off, quit.
- **Floating widget** (`PyObjC` `NSPanel`, always-on-top, draggable, click-through when idle):
  the ✕ / waveform / ✓ pill from `assets/widget/`. ✕ discards, middle shows live mic level,
  ✓ inserts. Appears on listening, fades when idle. This is a new sub-component of `w1_macos`
  beyond `rumps` (rumps is menu-bar only) — folded into Phase 1.

### 10.2 Light cleanup stage — disfluencies + spoken self-corrections (v1, conservative)
A new `w1_core/correction/cleanup.py` stage, distinct from glossary correction, **off-able**
and deliberately light so it never changes meaning (critical for clinical dictation):
- **Spoken self-corrections:** "X, I mean Y" / "X — sorry, Y" / "X, scratch that, Y" → keep Y
  (Jay's example: said *"actively suggested… I meant selected"* → output *"selected"*).
- **Filler removal:** leading/standalone "um", "uh", "er", and filler "you know"/"like" — narrow,
  whitespace-normalised, never touching content words.
- Runs **before** glossary correction; guarded by the same negative-corpus discipline (zero
  meaning change on the do-not-corrupt set). Patterns kept narrow and individually tested.

### 10.3 Meeting mode — all-purpose meeting capture + diarization (new phase: **2c**)
A **second entrypoint** on the same `w1_core` (Whisper + glossary correction still apply —
great for BAPS meetings and clinical MDTs). Sequenced after the dictation v1 (Phase 1); parallel
to streaming (Phase 2).
- **Capture (all-purpose, any app — Meet/Teams/Zoom):** Apple **ScreenCaptureKit** captures
  *system audio* (everyone) + *mic* (you) as two streams — no third-party driver, just a
  Screen-Recording permission. Fallback: a BlackHole aggregate device.
- **Diarization:** mic stream = **"Me"**, system stream = **"Others"** — that split is free.
  Multiple remote speakers separated by on-device voice-embedding clustering (pyannote /
  whisperx-class). Labels default to *Speaker 1/2/3…*; reading real names from the meeting UI
  (Accessibility/OCR) is a later enhancement; manual rename in v1.
- **Destination:** user-chosen folder (e.g. `~/Documents/w1-meetings/`). Each meeting →
  timestamped folder with a **speaker-labelled, timestamped Markdown transcript** (same shape as
  the existing `/transcribe` skill), glossary-corrected; optional audio retention is opt-in and
  off by default (privacy).
- **New package:** `src/w1_meeting/` (capture + diarization + writer) using `w1_core`; macOS
  capture bits live in `w1_macos`. Architecture unchanged — additive.
- **Open question for Jay:** keep meeting audio after transcription, or transcript-only by default?

### 10.4 Build progress (live)
- ✅ Data layer (`w1_data`, generated + verified) · ✅ `config.py` · ✅ correction `loader`,
  `rules`, `protect` — **9/9 unit tests green**, clinical-English safety proven.
- ⏭️ Next: `fuzzy.py` → `cleanup.py` → `bias_prompt.py` → `engine.py` (orchestrator) → backends
  (`mock` + `mlx`) → `pipeline.py` → macOS adapter (menu-bar + widget + hotkey + capture + paste).
