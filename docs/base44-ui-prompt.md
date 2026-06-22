# Base44 UI prompt — w1

> Paste the block below into Base44. It builds the companion **dashboard + settings web app**
> and a visual **prototype of the floating dictation widget**. The real always-on-top widget,
> global hotkey, and on-device Whisper are native/local (the Python `w1` engine) — Base44 is
> for the UI/dashboard that pairs with it.

---

**Build "w1" — a local, privacy-first dictation app with a companion dashboard.**

w1 turns speech into text entirely on-device (no cloud, no account). Its superpower: it
understands BAPS Gujarati sacred terminology mixed into natural English — so a doctor and sewa
(community-service) volunteer can dictate *"we did darshan at the mandir for satsang"* and every
sacred term comes out perfectly spelled, while ordinary and clinical English is never altered.
Build the companion dashboard, settings, and a visual prototype of the floating dictation widget.

**Primary user:** a busy NHS doctor who is also a BAPS sewa volunteer — dictates clinical notes,
messages, documents, and meeting minutes; wants speed, perfect sacred-term spelling, and total
privacy.

**Brand & visual design**
- Mood: calm, premium, privacy-first — "sacred meets modern."
- Colours: deep slate surfaces (#171B26 / #232838); warm **saffron** accent gradient
  (#F4A024 → #E8870E) for active/primary; off-white text (#F4F5F8); muted grey (#5B6478) for
  secondary; success green (#37C892); danger red (#F0473E).
- Type: clean modern sans (Inter / SF). Rounded corners (16–28px), soft shadows, generous
  spacing. Dark mode by default, with a light mode. Show a small Devanagari "वाणी" lockup beside
  the word "w1".

**Screens**

1. **Dashboard (home).** Privacy-first hero line: *"100% on-device. Nothing leaves your Mac."*
   A status card (engine ready · model: large-v3-turbo · microphone permission granted). Quick
   stats: words dictated today, sacred terms corrected, meetings transcribed. A large saffron mic
   button to start dictation (pulses softly when listening). A recent-activity feed.

2. **Floating widget (live preview component).** A rounded pill with three zones: **✕ discard**
   (left), an **audio waveform** (centre), **✓ insert** (right). Show its three states:
   *Idle* (dim, flat waveform), *Listening* (saffron animated bars + a red record dot),
   *Processing* (three pulsing saffron dots). Style it as a small, draggable, always-on-top pill.

3. **Modes.** Three selectable correction modes, with a prominent toggle and the active mode
   glanceable:
   - **Dictation (Sewa)** — default. Corrects BAPS sacred terms (temple→mandir, aarti→arti) and
     snaps mis-heard Gujarati words to their canonical spelling.
   - **Raw (Clinical)** — no terminology changes; for clinical notes where "temple" is anatomy.
   - **Document** — full editorial polish (removes filler/hedging; formal phrasing).

4. **Dictation history.** A list of recent transcripts. Each row: the final text, a "raw vs
   corrected" diff toggle, the mode used, a timestamp, and chips for the corrections that fired
   (e.g. "temple→mandir", "fuzzy: mandhir→mandir"). Copy button. Search and filter.

5. **Glossary.** Manage BAPS sacred terms in a searchable table (term · category · definition ·
   aliases). An "Add / correct a term" action to teach a new spelling once. Mark the protected
   terms (never altered) with a shield icon. Category filter chips: Doctrinal, Ritual, Titles,
   Scriptures, Food & Cultural, Realms.

6. **Meetings.** Meeting transcription. Start/stop a capture and pick a **destination folder**. A
   live, speaker-labelled, timestamped transcript (Me · Speaker 1 · Speaker 2…) with inline
   speaker rename. A saved-meetings list (title, date, duration, participant count); open one to
   read the full Markdown transcript and export it.

7. **Settings.** Hotkey (default: hold **Right-Option** = push-to-talk, double-tap = toggle;
   rebindable). Insert mode (paste vs type). Model picker (large-v3-turbo default). Audio cues
   on/off. Launch at login. A **Privacy** panel reaffirming on-device processing and "no audio or
   transcript is stored unless you choose to."

**Data model**
- **Transcript**: text, raw_text, mode (dictation|raw|document), created_at, corrections
  (list of {label, type}), inserted_into_app.
- **GlossaryTerm**: canonical, aliases (list), category, definition, protected (bool).
- **Meeting**: title, date, duration, destination_path, speakers (list of {label, display_name}),
  segments (list of {speaker, start_time, end_time, text}).

**Tone & details.** Warm, calm, confident; privacy reassurance throughout. Saffron primary
buttons. Friendly empty states (e.g. *"Nothing dictated yet — press your hotkey and speak."*).
A subtle footer: *"Built for sewa. Private by design."*
