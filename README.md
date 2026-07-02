# W1

Local dictation for macOS. Hold Right-Option, speak, release. Corrected text lands in whatever
app has focus. Everything runs on your Mac: the speech model, the correction rules, the
transliteration. There is no server, no account, and no network call at runtime.

W1 exists because generic dictation mangles BAPS Gujarati. Say "Pramukh Swami Maharaj" to most
tools and you get three guesses and a spelling lottery. W1 ships a terminology layer built from
the same rule set that powers the Aksharpith transliteration pipeline, so katha vocabulary comes
out right, in the ā-only romanisation the sampradāy's publications use.

Live site: [w1.baps.solutions](https://w1.baps.solutions)

## Install

Packaged app, if you were given `W1.dmg`: drag W1 to Applications, right-click it, Open. macOS
asks for Microphone, Accessibility and Input Monitoring. All three are required; Input
Monitoring is the one people miss, and the hotkey stays dead without it. The menu bar icon
shows an exclamation mark until every grant is in place.

From source, on a bare Apple Silicon Mac:

```
git clone https://github.com/jp-sapio-health/w1.baps.solutions.git w1
cd w1
./install.sh
./w1 app
```

`install.sh` installs uv if you do not have it, builds a Python 3.12 virtualenv, pulls the MLX
wheels, and pre-downloads the model (about 1.5 GB, one time, cached in `~/.cache/huggingface`).
Grant the same three permissions to your terminal app.

## The model, and what it was trained on

W1 does not train or fine-tune anything. Recognition is `mlx-community/whisper-large-v3-turbo`,
a conversion of OpenAI's Whisper large-v3-turbo to Apple's MLX array format, running float16 on
the Mac's GPU through Metal.

Some provenance, since it matters for a tool aimed at a specific speech community:

- Whisper large-v3 was trained by OpenAI on roughly 1 million hours of weakly labelled audio
  plus 4 million hours of audio pseudo-labelled by large-v2, spanning 90+ languages. Gujarati
  is in the training mix, but as a long-tail language: its share of that corpus is small, which
  is exactly why raw Whisper output needs a domain layer for katha vocabulary.
- large-v3-turbo is OpenAI's distilled variant: the encoder is unchanged, the decoder is cut
  from 32 layers to 4, then fine-tuned on the same multilingual transcription data. It keeps
  most of large-v3's accuracy at a fraction of the decode cost, which is what makes real-time
  local dictation practical on a laptop.
- The MLX conversion changes the container, not the numbers: same weights, reformatted for
  Apple Silicon's unified memory and Metal kernels.

The part W1 does own is data, not weights: a generated dataset compiled from the Aksharpith
rule files (the Mandir project's TypeScript sources, converted by `scripts/sync_rules_from_ts.py`
into JSON under `src/w1_data/`). Currently 64 terminology rules, 20 protected terms, and 74
bias terms. It is used three ways at inference time:

1. **Decoder biasing.** The bias terms are packed into Whisper's `initial_prompt` within its
   224-token budget, nudging decoding toward sampradāy vocabulary before any correction runs.
2. **Protected terms.** Names like Swaminarayan are masked before any fuzzy matching, so
   cleanup can never rewrite them.
3. **Terminology rules.** Deterministic post-corrections, filtered by mode, applied after
   cleanup. Rules rather than model output, so they are reviewable and testable.

## Pipeline

One dictation cycle, end to end:

```
hold Right-Option   mic opens (16 kHz mono float32), live RMS drives the widget waveform
release             frames concatenate, a worker thread takes over
transcribe          MLX Whisper, with the bias prompt (skipped in Gujarati mode)
gate 1: artifacts   known Whisper hallucinations ("thank you.", "[BLANK_AUDIO]") are dropped
gate 2: confidence  mean no_speech_prob > 0.6 or mean avg_logprob < -1.0 drops the take
correct             cleanup, protected-term masking, fuzzy OOV snap, terminology rules
                    (Gujarati mode instead runs the deterministic transliterator)
paste               into the focused field, clipboard restored; if nothing editable has
                    focus, a panel floats the text and Cmd+Shift+V pastes it later
```

A gated take shows a red X on the widget and pastes nothing. Bad audio producing no text is a
feature: the gates exist because Whisper hallucinates fluent English on silence.

The Gujarati transliterator is not the model. It is a syllable-walking state machine over
U+0A80 to U+0AFF with word-final schwa deletion and anusvara place assimilation, emitting ASCII
plus a single diacritic, ā. `મંદિર કથા ભગવાન` comes out as `mandir kathā bhagavān`,
deterministically, every time.

## Modes

| Menu label | Behaviour |
|---|---|
| Dictate | Verbatim. No deletions, no rewrites. Safe for clinical notes. |
| Default | Light cleanup plus sacred-term corrections. |
| Clean + | Adds editorial rules: fillers out, self-corrections resolved. |
| Gujarati (katha) | Forces Gujarati decoding, outputs ā-only romanisation. |

## CLI

```
./w1 app          menu-bar app + floating widget
./w1 dictate      record from the terminal, print the correction
./w1 transcribe   run a .wav / .m4a file through the pipeline
./w1 correct      run text through the correction engine alone
./w1 doctor       environment, model, rule data, permission status
./w1 debug-keys   print every key event the listener receives
```

## Architecture

```
src/w1_core    engine: config, pipeline, gates, correction, backends. No macOS imports;
               an import-linter contract enforces the boundary.
src/w1_data    the generated JSON dataset described above. Never hand-edited.
src/w1_macos   menu-bar app, floating widget, hotkey listener, mic capture, paste
               injection, focus detection, permissions.
```

52 unit tests cover the gates, the corrector, the transliterator and the bias-prompt budget
(96% line coverage on w1_core). `packaging/build.sh` will not produce a dmg unless the signed
bundle passes a 7-point runtime self-test (portaudio, MLX, tokenizer, backend selection) run
from inside the bundle.

## Troubleshooting

Everything the packaged app does is logged to `~/Library/Logs/W1.log`. If the hotkey does
nothing, check the menu bar: Permissions shows live grant status and opens the right Settings
pane. macOS ties permission grants to the app's code signature, so replacing the app bundle
resets them; grant once, keep the bundle.

## Privacy

Audio is held in memory, transcribed on the GPU, and discarded. Nothing is written to disk
except the log (text you can read) and the model cache (weights from Hugging Face). The only
network call W1 ever makes is the one-time model download.
