#!/usr/bin/env bash
# OKF system installer / upgrader (ADR-0005).
# Idempotent: re-run after every `git pull`. Never overwrites an existing
# ~/.okf/okf.yaml (the user's notebook); always refreshes skills and config.json.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OKF_HOME="$HOME/.okf"

# Agents and generated configs want native Windows paths; Git Bash gives POSIX.
to_native() {
  if command -v cygpath >/dev/null 2>&1; then
    cygpath -m "$1"
  else
    echo "$1"
  fi
}

echo "== OKF system: $REPO_ROOT"

# 1. KS library path — resolve before touching anything, so a failed prompt
#    (non-interactive run) can't leave a half-installed state.
NEED_NOTEBOOK=0
if [ ! -f "$OKF_HOME/okf.yaml" ]; then
  NEED_NOTEBOOK=1
  KS_LIBRARY="${KS_LIBRARY:-}"
  
  # Sibling of the system repo
  KS_LIBRARY_DEFAULT="$(to_native "$HOME/okf-knowledge-systems")"
  if [ -z "$KS_LIBRARY" ]; then
    # Bare Enter takes the default;
    read -r -p "KS library path (folder where your Knowledge Systems are cloned) [$KS_LIBRARY_DEFAULT]: " KS_LIBRARY || true
    KS_LIBRARY="${KS_LIBRARY:-$KS_LIBRARY_DEFAULT}"
  fi
  if [ -z "$KS_LIBRARY" ]; then
    echo "error: KS library path required — set KS_LIBRARY=<path> (HOME is unset)" >&2
    exit 1
  fi
  KS_LIBRARY="${KS_LIBRARY/#\~/$HOME}"
fi

# 2. venv + editable install
if [ ! -d "$REPO_ROOT/.venv" ]; then
  PY="${PYTHON:-}"
  if [ -z "$PY" ]; then
    # Probe by running each candidate, not `command -v`. On Windows,
    # %LOCALAPPDATA%\Microsoft\WindowsApps holds Store alias stubs named
    # python.exe/python3.exe that are on PATH by default: `command -v` matches
    # them, but running one prints "Python was not found" and exits nonzero.
    # `py` is the Python Launcher, which finds real installs not named python3.
    # Ask each candidate for its own sys.executable, so `py` resolves to a
    # real interpreter path rather than staying a two-word "py -3" command.
    probe='import sys; print(sys.executable) if sys.version_info >= (3, 11) else sys.exit(1)'
    for cand in python3.14 python3.13 python3.12 python3.11 python3 python py; do
      command -v "$cand" >/dev/null 2>&1 || continue
      if [ "$cand" = py ]; then
        found="$("$cand" -3 -c "$probe" 2>/dev/null)" || continue
      else
        found="$("$cand" -c "$probe" 2>/dev/null)" || continue
      fi
      found="${found//\\//}"  # Git Bash: make Windows paths executable (C:/...)
      [ -n "$found" ] && { PY="$found"; break; }
    done
  fi
  [ -n "$PY" ] || { echo "error: no working python 3.11+ found; set PYTHON=<path>" >&2; exit 1; }
  echo "== creating venv with $PY"
  "$PY" -m venv "$REPO_ROOT/.venv"
fi
if [ -x "$REPO_ROOT/.venv/Scripts/python.exe" ]; then
  VENV_PY="$REPO_ROOT/.venv/Scripts/python.exe"
  VENV_OKF="$REPO_ROOT/.venv/Scripts/okf.exe"
else
  VENV_PY="$REPO_ROOT/.venv/bin/python"
  VENV_OKF="$REPO_ROOT/.venv/bin/okf"
fi
echo "== pip install -e ."
"$VENV_PY" -m pip install --quiet --index-url https://pypi.org/simple/ -e "$REPO_ROOT"

# 3. copy every okf-* skill to both agents' user-level skill dirs
for agent_dir in "$HOME/.claude/skills" "$HOME/.cursor/skills"; do
  mkdir -p "$agent_dir"
  for src in "$REPO_ROOT/.cursor/skills"/okf-*/; do
    skill="$(basename "$src")"
    rm -rf "${agent_dir:?}/$skill"
    cp -r "$src" "$agent_dir/$skill"
    echo "== installed $skill -> $agent_dir/$skill"
  done
done

# 4. notebook home: create okf.yaml once, never overwrite. A fresh install
#    starts with the bundled football example copied into the user's KS library
#    and registered as the first KS.
mkdir -p "$OKF_HOME"
if [ "$NEED_NOTEBOOK" = "1" ]; then
  KS_LIBRARY_NATIVE="$(to_native "$KS_LIBRARY")"
  mkdir -p "$KS_LIBRARY"
  FOOTBALL_KS="$KS_LIBRARY/football"
  if [ ! -e "$FOOTBALL_KS" ]; then
    cp -r "$REPO_ROOT/examples/football" "$FOOTBALL_KS"
    echo "== installed football example -> $FOOTBALL_KS"
  elif [ ! -f "$FOOTBALL_KS/index.md" ]; then
    echo "error: $FOOTBALL_KS already exists but is not an OKF KS (index.md missing)" >&2
    exit 1
  else
    echo "== keeping existing football KS: $FOOTBALL_KS"
  fi
  cat > "$OKF_HOME/okf.yaml" <<EOF
version: 1
ks_library: $KS_LIBRARY_NATIVE
ks:
  football:
    path: football
    if_missing: error
link_search_order:
  - football
EOF
  echo "== wrote $OKF_HOME/okf.yaml (football KS onboarded)"
else
  echo "== keeping existing notebook: $OKF_HOME/okf.yaml"
fi

# 5. generated tool config for skills — install-time facts only, never the KS list
cat > "$OKF_HOME/config.json" <<EOF
{
  "version": "2",
  "system_root": "$(to_native "$REPO_ROOT")",
  "python": "$(to_native "$VENV_PY")",
  "okf_cli": "$(to_native "$VENV_OKF")",
  "okf_yaml": "$(to_native "$OKF_HOME")/okf.yaml",
  "scripts": {
    "ingest_okf_concept": "$(to_native "$REPO_ROOT")/scripts/ingest_okf_concept.py"
  }
}
EOF
echo "== wrote $OKF_HOME/config.json"

# 6. Desktop launcher for OKF Server (ADR-0008): Start-menu shortcut on
#    Windows, a ~/Applications/*.command on macOS. Non-fatal either way —
#    the notebook works without it via `okf serve` from a terminal.
if command -v powershell.exe >/dev/null 2>&1; then
  powershell.exe -NoProfile -ExecutionPolicy Bypass \
    -File "$(to_native "$REPO_ROOT/scripts/install_viewer_shortcut.ps1")" \
    || echo "warn: OKF Viewer shortcut install failed (non-fatal)"
elif [ "$(uname -s)" = "Darwin" ]; then
  "$REPO_ROOT/scripts/install_viewer_shortcut.sh" \
    || echo "warn: OKF Viewer launcher install failed (non-fatal)"
fi

echo "Done. The football example is ready in new notebooks; onboard additional KSs with the okf-onboard skill."
