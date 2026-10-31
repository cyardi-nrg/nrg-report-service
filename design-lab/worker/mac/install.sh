#!/bin/bash
# Design Lab worker v1.0.0 (2026-10-31) — one-time setup on the Mac.
# Run from Terminal:   bash design-lab/worker/mac/install.sh
set -e
DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR"
echo "== Design Lab worker setup in $DIR"

if ! command -v python3 >/dev/null 2>&1 || ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
  echo "Python 3.10 or newer is needed. Install it with:  xcode-select --install   (or from python.org), then run this again."
  exit 1
fi

echo "== 1/4  Installing the worker's Python packages (private to this folder)"
python3 -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt
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
