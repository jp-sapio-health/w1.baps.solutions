# Packaging w1 as a macOS app

w1 ships two ways. For developers, `./install.sh` + `./w1 app` is the tested path. To hand a
double-clickable app to non-technical users, build a `.app` bundle with py2app.

## Build

```bash
# one-time: add the build tool to the venv (asks before installing — see supply-chain policy)
uv pip install --python .venv/bin/python -e '.[mlx,macos,dev,build]'

packaging/build.sh            # -> dist/w1.app
packaging/build.sh --dmg      # -> dist/w1.app + dist/w1.dmg
```

The bundle is **menu-bar only** (`LSUIElement`) and does **not** embed the Whisper model — it
downloads once on first run to `~/.cache/huggingface`. This keeps the app small and avoids
redistributing model weights.

## Permissions

The app needs three TCC permissions, prompted on first use:

- **Microphone** — declared via `NSMicrophoneUsageDescription` (prompts automatically).
- **Accessibility** — to paste into the focused app.
- **Input Monitoring** — for the global Right-Option hotkey.

A stable bundle identifier (`health.baps.w1`) matters here: macOS keys granted permissions to
the bundle ID, so re-signed rebuilds keep their grants.

## Signing & notarization

| Audience | What to do |
|----------|------------|
| **Yourself / a few trusted people** | Ship the **unsigned** `.app`. First launch: right-click ▸ **Open** to bypass Gatekeeper once. |
| **Wider distribution** | Sign + notarize with an Apple **Developer ID** ($99/yr). No right-click dance, no "unidentified developer" warning. |

Signed build outline (Developer ID Application certificate in the keychain):

```bash
codesign --deep --force --options runtime \
  --entitlements packaging/w1.entitlements \
  --sign "Developer ID Application: YOUR NAME (TEAMID)" \
  dist/w1.app

xcrun notarytool submit dist/w1.dmg \
  --apple-id you@example.com --team-id TEAMID --password APP_SPECIFIC_PW --wait
xcrun stapler staple dist/w1.app
```

The entitlements in `packaging/w1.entitlements` allow the bundled Python/MLX runtime to JIT and
`dlopen` Metal libraries under the hardened runtime (required for notarization).

## Notes / gotchas

- `argv_emulation` is **off** — it breaks pynput's global key handling and AppKit's run loop.
- If you bundle the MLX backend, expect a large `.app`; the recipe keeps `mlx_whisper`/`mlx` out
  of `packages` by default since they download + Metal-link fine from the bundled site-packages.
- Verify the frozen bundle actually launches and records before sharing — py2app freezing can
  miss a lazily-imported module; add it to `OPTIONS["includes"]` in `packaging/setup_app.py`.
