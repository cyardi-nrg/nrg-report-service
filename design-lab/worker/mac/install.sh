#!/bin/bash
# Design Lab worker v1.7.0 (2026-10-31) — one-time setup on the Mac.
# v1.7: finds Python 3.10+ wherever it is installed (python.org, Homebrew) — the Mac's own python3
#       is 3.9; the old advice (xcode-select) never gives 3.10.
# Run from Terminal:   bash design-lab/worker/mac/install.sh
set -e
DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR"
echo "== Design Lab worker setup in $DIR"

# The Mac's own python3 (/usr/bin/python3, from Apple's command-line tools) is 3.9 — too old.
# Look for a newer one: python.org installs, Homebrew, then anything on the PATH.
PY=""
for c in /Library/Frameworks/Python.framework/Versions/3.1[0-9]/bin/python3 \
         /opt/homebrew/bin/python3.1[0-9] /usr/local/bin/python3.1[0-9] /opt/homebrew/bin/python3 /usr/local/bin/python3 \
         "$(command -v python3.13 2>/dev/null)" "$(command -v python3.12 2>/dev/null)" "$(command -v python3.11 2>/dev/null)" \
         "$(command -v python3.10 2>/dev/null)" "$(command -v python3 2>/dev/null)"; do
  if [ -n "$c" ] && [ -x "$c" ] && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
    PY="$c"; break
  fi
done
if [ -z "$PY" ]; then
  cat <<MSG
Python 3.10 or newer is needed (this Mac only has $(python3 --version 2>/dev/null || echo 'no Python')).
  1. Open https://www.python.org/downloads/macos/ and download the latest "macOS 64-bit universal2 installer" (Python 3.12 or 3.13).
  2. Open the downloaded .pkg and click Continue / Install (asks for your Mac password).
  3. Then run this again:   bash "$DIR/mac/install.sh"
MSG
  exit 1
fi
echo "   Using $PY ($("$PY" --version))"
# python.org's Python needs its security certificates installed once, or every download fails with an SSL error
PYVER="$("$PY" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')"
CERTS="/Applications/Python $PYVER/Install Certificates.command"
if [ -f "$CERTS" ]; then
  echo "   Installing Python's security certificates (once)"
  bash "$CERTS" >/dev/null 2>&1 || true
fi

echo "== 1/4  Installing the worker's Python packages (private to this folder)"
rm -rf .venv
"$PY" -m venv .venv
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt
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
