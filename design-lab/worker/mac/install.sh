#!/bin/bash
# Design Lab worker v1.7.3 (2026-10-31) — one-time setup on the Mac.
# v1.7.3 (owner: "sort it once and for all"): the setup no longer depends on which Python the
#   Mac has. It brings its own Python 3.12 (via "uv", Astral's free installer — a private copy
#   inside the worker folder, nothing else on the Mac changes), and it first pulls the latest
#   version of this program itself, so a forgotten "Pull" in GitHub Desktop no longer matters.
#   If uv can't be fetched it falls back to a python.org / Homebrew Python 3.10–3.13.
# Run from Terminal:   bash ~/Documents/GitHub/nrg-report-service/design-lab/worker/mac/install.sh
set -e
DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR"
echo "== Design Lab worker setup in $DIR"
BRANCH="claude/3d-design-walkthrough-videos-pim15v"
PYVER="3.12"   # NREL SAM (month-wise generation) supports 3.10–3.13; 3.12 is the safest

# 0. Get the latest version of this program first (once), then start again with it
export GIT_TERMINAL_PROMPT=0 GCM_INTERACTIVE=never   # never stop to ask for a GitHub password
if [ -z "$NRG_UPDATED" ] && command -v git >/dev/null 2>&1 && git -C "$DIR" rev-parse --git-dir >/dev/null 2>&1; then
  echo "== 0/4  Getting the latest version"
  BEFORE="$(git -C "$DIR" rev-parse HEAD)"
  git -C "$DIR" fetch --quiet origin "$BRANCH" 2>/dev/null || true
  git -C "$DIR" checkout --quiet "$BRANCH" 2>/dev/null || true
  git -C "$DIR" merge --quiet --ff-only "origin/$BRANCH" 2>/dev/null || echo "   (could not update automatically — carrying on with this version)"
  if [ "$(git -C "$DIR" rev-parse HEAD)" != "$BEFORE" ]; then
    echo "   Updated to $(cat "$DIR/VERSION") — starting again with it"
    NRG_UPDATED=1 exec bash "$DIR/mac/install.sh"
  fi
fi
echo "   Version $(cat "$DIR/VERSION")"

# 1. A private Python for the worker
rm -rf .venv
UV=""
for c in "$(command -v uv 2>/dev/null)" "$HOME/.local/bin/uv" "$HOME/.cargo/bin/uv"; do
  if [ -n "$c" ] && [ -x "$c" ]; then UV="$c"; break; fi
done
if [ -z "$UV" ]; then
  echo "   Fetching uv (the tool that brings the worker its own Python, once)"
  if curl -LsSf https://astral.sh/uv/install.sh | env UV_NO_MODIFY_PATH=1 INSTALLER_NO_MODIFY_PATH=1 sh >/dev/null 2>&1; then
    [ -x "$HOME/.local/bin/uv" ] && UV="$HOME/.local/bin/uv"
  fi
fi
if [ -n "$UV" ]; then
  echo "   Setting up a private Python $PYVER (download ~20 MB, once)"
  if ! "$UV" venv --quiet --seed --python "$PYVER" --python-preference only-managed .venv; then
    echo "   uv could not set up Python — trying a Python already on this Mac instead"
    UV=""
    rm -rf .venv
  fi
fi
if [ -z "$UV" ]; then
  OK_RANGE='import sys; sys.exit(0 if (3, 10) <= sys.version_info[:2] <= (3, 13) else 1)'
  PY=""
  for v in 3.12 3.13 3.11 3.10; do
    for c in "/Library/Frameworks/Python.framework/Versions/$v/bin/python3" "/opt/homebrew/bin/python$v" "/usr/local/bin/python$v" "$(command -v python$v 2>/dev/null)"; do
      if [ -n "$c" ] && [ -x "$c" ] && "$c" -c "$OK_RANGE" 2>/dev/null; then PY="$c"; break 2; fi
    done
  done
  if [ -z "$PY" ]; then
    cat <<MSG
Could not get a suitable Python automatically (no internet to astral.sh?).
Install Python 3.12 or 3.13 from https://www.python.org/downloads/macos/ ("macOS 64-bit universal2 installer"),
then run this again:   bash "$DIR/mac/install.sh"
MSG
    exit 1
  fi
  echo "   Using $PY ($("$PY" --version))"
  CERTS="/Applications/Python $("$PY" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')/Install Certificates.command"
  [ -f "$CERTS" ] && { bash "$CERTS" >/dev/null 2>&1 || true; }
  "$PY" -m venv .venv
fi
echo "   Worker Python: $(.venv/bin/python --version)"

echo "== 1/4  Installing the worker's Python packages (private to this folder)"
if [ -n "$UV" ]; then
  "$UV" pip install --quiet --python .venv/bin/python -r requirements.txt
else
  .venv/bin/pip install --quiet --upgrade pip
  .venv/bin/pip install --quiet -r requirements.txt
fi
.venv/bin/python3 -m playwright install chromium     # the browser the 3D pictures and video are rendered in (~150 MB, once)
mkdir -p logs

echo "== 2/4  Settings (.env)"
if [ ! -f .env ]; then
  cp .env.example .env
  chmod 600 .env
  echo "   Opening .env in TextEdit — paste the values from Railway, save, close TextEdit, then press Return here."
  open -e .env
  read -r _
fi

echo "== 3/4  Self-test"
if ! .venv/bin/python3 worker.py --selftest; then
  echo "Fix .env (open -e $DIR/.env) and run this script again."
  exit 1
fi

echo "== 4/4  Start automatically at login"
PLIST="$HOME/Library/LaunchAgents/com.nrg.designlab.worker.plist"
mkdir -p "$HOME/Library/LaunchAgents"
sed "s#__WORKER_DIR__#$DIR#g" mac/com.nrg.designlab.worker.plist > "$PLIST"
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "   Worker started. It will start by itself every time you log in."

cat <<MSG

== Last step (needs your Mac password once): wake the Mac every night for the overnight video
   sudo pmset repeat wakeorpoweron MTWRFSU 20:55:00

   Keep the MacBook plugged in and the lid OPEN at night (a closed lid sleeps no matter what).
   To see what it is doing:   tail -f "$DIR/logs/worker.log"
MSG
