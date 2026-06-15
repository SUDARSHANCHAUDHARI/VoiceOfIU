#!/bin/bash
# Remove the VoiceOfIU LaunchAgent (stops auto-start).
set -euo pipefail

LABEL="com.sudarshantechlabs.voiceofiu"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

if [[ -f "$PLIST" ]]; then
  launchctl unload "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"
  echo "✅ VoiceOfIU auto-start removed."
else
  echo "Nothing to remove — no LaunchAgent installed."
fi
