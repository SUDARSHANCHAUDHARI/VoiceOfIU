#!/bin/bash
# Install VoiceOfIU as a macOS LaunchAgent: auto-start on login + restart on crash.
# Opt-in — run this only if you want IU AI running in the background always.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PY="$PROJECT_DIR/.venv/bin/python"
RUN="$PROJECT_DIR/run.py"
LABEL="com.sudarshantechlabs.voiceofiu"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$HOME/Library/Logs/VoiceOfIU"

if [[ ! -x "$PY" ]]; then
  echo "❌ venv python not found at $PY — create the venv first." >&2
  exit 1
fi

mkdir -p "$LOG_DIR" "$(dirname "$PLIST")"

cat > "$PLIST" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>            <string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PY</string>
        <string>$RUN</string>
    </array>
    <key>WorkingDirectory</key> <string>$PROJECT_DIR</string>
    <key>RunAtLoad</key>        <true/>
    <key>KeepAlive</key>        <true/>
    <key>StandardOutPath</key>  <string>$LOG_DIR/stdout.log</string>
    <key>StandardErrorPath</key><string>$LOG_DIR/stderr.log</string>
</dict>
</plist>
PLIST_EOF

# Validate before loading
plutil -lint "$PLIST"

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"

echo "✅ Installed. VoiceOfIU will start on login and restart if it crashes."
echo "   Logs: $LOG_DIR/"
echo "   Stop/remove: scripts/uninstall_autostart.sh"
