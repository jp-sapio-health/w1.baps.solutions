#!/usr/bin/env bash
# w1 installer — sets up a local, on-device dictation environment on Apple Silicon macOS.
#
#   ./install.sh
#
# It creates a Python 3.12 virtualenv, installs w1 with the MLX + macOS extras, pre-downloads
# the Whisper model, and prints the three macOS permissions you must grant. No data leaves the
# machine; the model is fetched once from Hugging Face and cached locally.
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

MODEL_ID="mlx-community/whisper-large-v3-turbo"
PY_VERSION="3.12"

bold() { printf "\033[1m%s\033[0m\n" "$1"; }
ok()   { printf "  \033[32m✓\033[0m %s\n" "$1"; }
warn() { printf "  \033[33m!\033[0m %s\n" "$1"; }

bold "w1 installer"

# 1. Platform check ----------------------------------------------------------
if [ "$(uname -s)" != "Darwin" ]; then
  echo "w1 targets macOS. Detected $(uname -s) — aborting." >&2
  exit 1
fi
if [ "$(uname -m)" != "arm64" ]; then
  warn "Not Apple Silicon (arm64). The MLX backend needs Apple Silicon; the faster-whisper"
  warn "fallback will be used instead. Install will continue."
fi
ok "macOS $(sw_vers -productVersion) ($(uname -m))"

# 2. uv (fast Python package manager) ---------------------------------------
if ! command -v uv >/dev/null 2>&1; then
  warn "uv not found. Install it with:  curl -LsSf https://astral.sh/uv/install.sh | sh"
  warn "then re-run ./install.sh"
  exit 1
fi
ok "uv $(uv --version | awk '{print $2}')"

# 3. Virtualenv + dependencies ----------------------------------------------
bold "Creating virtualenv (.venv, Python ${PY_VERSION})"
uv venv --python "$PY_VERSION" .venv
ok ".venv created"

bold "Installing w1 + dependencies (this pulls PyTorch-free MLX wheels; a few minutes)"
if [ "$(uname -m)" = "arm64" ]; then
  uv pip install --python .venv/bin/python -e '.[mlx,macos,dev]'
else
  uv pip install --python .venv/bin/python -e '.[faster,macos,dev]'
fi
ok "dependencies installed"

# 4. Pre-download the Whisper model -----------------------------------------
bold "Downloading Whisper model: ${MODEL_ID} (~1.5 GB, one time)"
if [ "$(uname -m)" = "arm64" ]; then
  .venv/bin/python - "$MODEL_ID" <<'PY'
import sys
from huggingface_hub import snapshot_download
snapshot_download(sys.argv[1])
print("model cached")
PY
  ok "model cached locally"
else
  warn "Skipping MLX model pre-fetch on non-Apple-Silicon; faster-whisper fetches on first use."
fi

# 5. Wrapper + health check --------------------------------------------------
chmod +x w1
ok "./w1 is executable"

bold "Environment check"
./w1 doctor || true

# 6. Permissions -------------------------------------------------------------
bold "Grant these macOS permissions (System Settings ▸ Privacy & Security)"
cat <<'PERMS'
  1. Microphone        — so w1 can hear you
  2. Accessibility     — so w1 can paste into the focused app
  3. Input Monitoring  — so the global hotkey (hold Right-Option) works

  Open the panes directly:
    open "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone"
    open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
    open "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent"

  Add (or tick) your terminal app — or the packaged w1.app — in each list.
PERMS

bold "Done. Launch the menu-bar app with:  ./w1 app"
