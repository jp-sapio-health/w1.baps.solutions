#!/usr/bin/env bash
# Build w1.app (and optionally a .dmg) with py2app.
#
#   packaging/build.sh            # build dist/w1.app
#   packaging/build.sh --dmg      # also produce dist/w1.dmg
#
# Prereqs: the project venv with the build extra installed:
#   uv pip install --python .venv/bin/python -e '.[mlx,macos,dev,build]'
# See docs/PACKAGING.md for signing & notarization (needed for sharing without Gatekeeper warnings).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PY="$ROOT/.venv/bin/python"

if ! "$PY" -c "import py2app" >/dev/null 2>&1; then
  echo "py2app not installed in .venv. Run:" >&2
  echo "  uv pip install --python .venv/bin/python -e '.[mlx,macos,dev,build]'" >&2
  exit 1
fi

# py2app's setup machinery uses the legacy install_requires keyword, which setuptools 80+
# rejects ("install_requires is no longer supported"). Pin a compatible setuptools for the build.
"$PY" -c "import setuptools,sys; sys.exit(0 if tuple(map(int,setuptools.__version__.split('.')[:1]))<(80,) else 1)" \
  || uv pip install --python "$PY" "setuptools<80"

echo "Cleaning previous build…"
rm -rf build dist

# Run from packaging/ (which has NO pyproject.toml) so setuptools doesn't auto-load the
# project's [project] table and inject install_requires — py2app rejects that. Output dirs are
# redirected back to the repo root. setup_app.py uses absolute paths, so cwd doesn't matter.
echo "Building dist/W1.app…"
( cd packaging && "$PY" setup_app.py py2app --dist-dir ../dist --bdist-base ../build )

echo "Built: dist/W1.app"

# mlx is a namespace package (no __init__.py), which py2app's packages option cannot collect.
# Copy it wholesale (compiled extensions + libmlx.dylib + mlx.metallib) before signing so it
# sits inside the sealed bundle. The self-test below verifies it imports.
SITE="$("$PY" -c "import sysconfig; print(sysconfig.get_paths()['purelib'])")"
if [ -d "$SITE/mlx" ]; then
  echo "Copying mlx (namespace package, excluded from py2app) into the bundle…"
  # Verbatim copy of the self-contained site-packages layout: core.so resolves its dylibs via
  # @loader_path/lib, so keeping the directory intact is all that is needed.
  ditto "$SITE/mlx" "dist/W1.app/Contents/Resources/lib/python3.12/mlx"
else
  echo "WARNING: mlx not found in $SITE; bundle will fail its self-test." >&2
fi

# Code-sign with a real identity when one is available, so macOS TCC grants (Input Monitoring,
# Accessibility) attach to a STABLE code identity and survive rebuilds. Without this the bundle is
# ad-hoc/linker-signed and the key listener silently gets no events. Set W1_SIGN_IDENTITY to a
# codesigning identity (see `security find-identity -v -p codesigning`); falls back to the first
# "Apple Development" identity in the keychain. Leaves the ad-hoc signature if none is found.
SIGN_ID="${W1_SIGN_IDENTITY:-$(security find-identity -v -p codesigning 2>/dev/null | grep -m1 "Apple Development" | sed -E 's/.*"(.*)"/\1/')}"
if [ -n "$SIGN_ID" ]; then
  echo "Signing with: $SIGN_ID"
  # IMPORTANT: codesign rejects "detritus" xattrs (com.apple.FinderInfo / fileprovider) that
  # iCloud Drive stamps onto everything under ~/Desktop and ~/Documents. They can't be stripped
  # in place (iCloud re-applies them), so copy the bundle OUT of iCloud first with ditto (which
  # drops xattrs/resource forks), sign there, then bring it back. Install/run from the signed
  # copy or the .dmg — not from the iCloud-synced dist/ (re-syncing would break the seal).
  SIGNED="$(mktemp -d)/W1.app"
  ditto --norsrc --noextattr --noacl dist/W1.app "$SIGNED"
  codesign --force --deep --options runtime \
    --entitlements "$ROOT/packaging/w1.entitlements" \
    --identifier health.baps.w1 \
    --sign "$SIGN_ID" "$SIGNED"
  codesign --verify --strict "$SIGNED" && echo "Signature OK ($SIGN_ID)"
  ditto "$SIGNED" dist/W1.app   # mirror back for the .dmg step (dmg is the clean deliverable)
  echo "$SIGNED" > "$ROOT/dist/.signed-app-path"
  # Runtime self-test INSIDE the signed bundle: imports the full dictation stack (portaudio,
  # mlx, mlx_whisper, tokenizer, backend selection). A bundle that launches but cannot dictate
  # must never ship again.
  echo "Running bundle self-test…"
  if ! W1_SELFTEST=1 "$SIGNED/Contents/MacOS/W1"; then
    echo "BUNDLE SELF-TEST FAILED — aborting." >&2
    exit 1
  fi
else
  echo "No codesigning identity found — leaving ad-hoc signature (grants won't persist across rebuilds)."
fi

if [ "${1:-}" = "--dmg" ]; then
  echo "Creating dist/W1.dmg…"
  # Package from the signed, xattr-free copy when we have one, so the .dmg's bundle keeps a valid
  # signature (the iCloud-synced dist/W1.app may have been re-stamped with FinderInfo).
  SRC="dist/W1.app"
  [ -f "$ROOT/dist/.signed-app-path" ] && SRC="$(cat "$ROOT/dist/.signed-app-path")"
  hdiutil create -volname "W1" -srcfolder "$SRC" -ov -format UDZO dist/W1.dmg
  echo "Built: dist/W1.dmg"
fi

echo "Done. Install: drag W1.app to /Applications, then grant Microphone + Accessibility +"
echo "Input Monitoring (System Settings ▸ Privacy & Security). Run from /Applications, not the"
echo "iCloud-synced Desktop (iCloud xattrs can invalidate the signature)."
