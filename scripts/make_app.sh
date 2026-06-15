#!/bin/bash
# Build VoiceOfIU.app — a lightweight launcher bundle (double-click to run).
# Runs the project's venv directly rather than bundling Python (reliable with
# mlx-whisper / pyobjc, which PyInstaller struggles to freeze).
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP="$PROJECT_DIR/dist/VoiceOfIU.app"
PY="$PROJECT_DIR/.venv/bin/python"
ICON="$PROJECT_DIR/assets/AppIcon.icns"

if [[ ! -f "$ICON" ]]; then
  echo "Icon missing — generating it first…"
  "$PY" "$PROJECT_DIR/scripts/make_icon.py"
fi

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

# Launcher executable
cat > "$APP/Contents/MacOS/VoiceOfIU" <<LAUNCH_EOF
#!/bin/bash
cd "$PROJECT_DIR"
exec "$PY" run.py
LAUNCH_EOF
chmod +x "$APP/Contents/MacOS/VoiceOfIU"

cp "$ICON" "$APP/Contents/Resources/AppIcon.icns"

cat > "$APP/Contents/Info.plist" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>             <string>VoiceOfIU</string>
    <key>CFBundleDisplayName</key>      <string>VoiceOfIU</string>
    <key>CFBundleIdentifier</key>       <string>com.sudarshantechlabs.voiceofiu</string>
    <key>CFBundleVersion</key>          <string>0.1.0</string>
    <key>CFBundleShortVersionString</key><string>0.1.0</string>
    <key>CFBundleExecutable</key>       <string>VoiceOfIU</string>
    <key>CFBundleIconFile</key>         <string>AppIcon</string>
    <key>CFBundlePackageType</key>      <string>APPL</string>
    <key>LSMinimumSystemVersion</key>   <string>13.0</string>
    <key>LSUIElement</key>              <true/>
    <key>NSMicrophoneUsageDescription</key>      <string>VoiceOfIU listens for your wake word and commands.</string>
    <key>NSAppleEventsUsageDescription</key>     <string>VoiceOfIU reads your Calendar, Mail, and Notes when asked.</string>
</dict>
</plist>
PLIST_EOF

# Refresh icon cache
touch "$APP"

# Ad-hoc code-sign so macOS treats it as a stable, consistent app identity.
# For full Gatekeeper trust / distribution, replace `-s -` with your Developer
# ID cert and notarize:  codesign -s "Developer ID Application: <name>" --deep --options runtime "$APP"  then  xcrun notarytool submit ...
codesign --force --deep -s - "$APP" 2>/dev/null && echo "ad-hoc signed"

echo "✅ Built $APP"
echo "   Double-click it, or: open '$APP'"
