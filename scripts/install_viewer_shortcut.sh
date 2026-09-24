#!/usr/bin/env bash
# macOS: a double-clickable "OKF Viewer.command" launcher in ~/Applications
# that starts OKF Server (`okf serve`, ADR-0008) and lets it open the viewer
# itself — the Mac counterpart to install_viewer_shortcut.ps1's Start-menu
# shortcut. Idempotent: overwrites on every run. Non-fatal — the notebook
# works without it (run `okf serve` from a terminal instead).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OKF_BIN="$REPO_ROOT/.venv/bin/okf"

if [ ! -x "$OKF_BIN" ]; then
  echo "warn: $OKF_BIN not found (run pip install -e . first); skipping OKF Viewer launcher"
  exit 0
fi

LAUNCHER_DIR="$HOME/Applications"
LAUNCHER="$LAUNCHER_DIR/OKF Viewer.command"
mkdir -p "$LAUNCHER_DIR"
cat > "$LAUNCHER" <<EOF
#!/bin/bash
"$OKF_BIN" serve
EOF
chmod +x "$LAUNCHER"

echo "installed OKF Viewer launcher -> $LAUNCHER (okf serve)"
