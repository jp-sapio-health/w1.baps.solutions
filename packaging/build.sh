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

if [ "${1:-}" = "--dmg" ]; then
  echo "Creating dist/W1.dmg…"
  hdiutil create -volname "W1" -srcfolder dist/W1.app -ov -format UDZO dist/W1.dmg
  echo "Built: dist/W1.dmg"
fi

echo "Done. First launch: right-click W1.app ▸ Open (unsigned builds) and grant permissions."
