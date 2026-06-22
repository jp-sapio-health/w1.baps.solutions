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

echo "Cleaning previous build…"
rm -rf build dist

echo "Building dist/w1.app…"
"$PY" packaging/setup_app.py py2app

echo "Built: dist/w1.app"

if [ "${1:-}" = "--dmg" ]; then
  echo "Creating dist/w1.dmg…"
  hdiutil create -volname "w1" -srcfolder dist/w1.app -ov -format UDZO dist/w1.dmg
  echo "Built: dist/w1.dmg"
fi

echo "Done. First launch: right-click w1.app ▸ Open (unsigned builds) and grant permissions."
