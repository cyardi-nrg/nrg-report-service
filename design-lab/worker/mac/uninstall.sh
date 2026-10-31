#!/bin/bash
# Design Lab worker v1.0.0 (2026-10-31) — stop the worker and remove the login item (keeps the folder and .env).
PLIST="$HOME/Library/LaunchAgents/com.nrg.designlab.worker.plist"
launchctl unload "$PLIST" 2>/dev/null || true
rm -f "$PLIST"
echo "Worker stopped and removed from login. To also stop the nightly wake:  sudo pmset repeat cancel"
