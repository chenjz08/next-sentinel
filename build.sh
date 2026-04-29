#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP="$ROOT/dist/Next Sentinel.app"
CONTENTS="$APP/Contents"
MACOS="$CONTENTS/MacOS"
RESOURCES="$CONTENTS/Resources"
INSTALL_DIR="${NEXT_SENTINEL_INSTALL_DIR:-"$HOME/Applications"}"
INSTALLED_APP="$INSTALL_DIR/Next Sentinel.app"

python3 "$ROOT/Sources/render_icon.py"

rm -rf "$APP"
mkdir -p "$MACOS" "$RESOURCES"

iconutil -c icns "$ROOT/build/NextSentinel.iconset" -o "$RESOURCES/NextSentinel.icns"
cp "$ROOT/Assets/StatusIcon.png" "$RESOURCES/StatusIcon.png"

swiftc -parse-as-library "$ROOT/Sources/NextSentinel.swift" \
  -framework AppKit \
  -framework Foundation \
  -o "$MACOS/Next Sentinel"

cat > "$CONTENTS/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleExecutable</key>
  <string>Next Sentinel</string>
  <key>CFBundleIdentifier</key>
  <string>local.codex.next-sentinel</string>
  <key>CFBundleName</key>
  <string>Next Sentinel</string>
  <key>CFBundleDisplayName</key>
  <string>Next Sentinel</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleIconFile</key>
  <string>NextSentinel</string>
  <key>CFBundleVersion</key>
  <string>1</string>
  <key>CFBundleShortVersionString</key>
  <string>1.0</string>
  <key>LSMinimumSystemVersion</key>
  <string>13.0</string>
  <key>LSUIElement</key>
  <true/>
  <key>NSHighResolutionCapable</key>
  <true/>
</dict>
</plist>
PLIST

mkdir -p "$INSTALL_DIR"
rsync -a --delete "$APP/" "$INSTALLED_APP/"

echo "$APP"
echo "$INSTALLED_APP"
