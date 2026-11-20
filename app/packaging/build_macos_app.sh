#!/usr/bin/env bash
set -euo pipefail

# CloudPilot Native macOS App (.app) & Installable Disk Image (.dmg) Builder (Phase 6 / M5)
# Compiles app/frontend/CloudPilotApp.swift natively on this Apple M4 Mac using swiftc,
# bundles Info.plist and local offline runtime launchers, signs ad-hoc locally,
# exports real SwiftUI screenshots, and packages release/artifacts/CloudPilot-v1.0-macOS.dmg.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
APP_NAME="CloudPilot"
APP_BUNDLE="${ROOT_DIR}/release/artifacts/${APP_NAME}.app"
DMG_PATH="${ROOT_DIR}/release/artifacts/${APP_NAME}-v1.0-macOS.dmg"
DMG_STAGING="${ROOT_DIR}/build/dmg_staging"

mkdir -p "${ROOT_DIR}/release/artifacts" "${ROOT_DIR}/build"
rm -rf "${APP_BUNDLE}" "${DMG_STAGING}" "${DMG_PATH}"

mkdir -p "${APP_BUNDLE}/Contents/MacOS"
mkdir -p "${APP_BUNDLE}/Contents/Resources"

echo "1. Compiling native SwiftUI macOS binary (${APP_NAME}) for arm64-apple-macosx14.0..."
swiftc \
  -O \
  -parse-as-library \
  -target arm64-apple-macosx14.0 \
  -sdk "$(xcrun --show-sdk-path --sdk macosx)" \
  "${ROOT_DIR}/app/frontend/CloudPilotApp.swift" \
  -o "${APP_BUNDLE}/Contents/MacOS/${APP_NAME}"

cat > "${APP_BUNDLE}/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>CloudPilot</string>
    <key>CFBundleIdentifier</key>
    <string>local.cloudpilot.macos</string>
    <key>CFBundleName</key>
    <string>CloudPilot</string>
    <key>CFBundleDisplayName</key>
    <string>CloudPilot — Local AI Agent</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSMinimumSystemVersion</key>
    <string>14.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>CloudPilotSigningStatus</key>
    <string>Ad-hoc locally signed; not Apple Developer ID notarized (disclosed per agent.md Section 11.6)</string>
</dict>
</plist>
EOF

# Include lightweight model metadata & local runtime pointer inside Resources
cp "${ROOT_DIR}/model/MODEL_CARD.md" "${APP_BUNDLE}/Contents/Resources/MODEL_CARD.md" 2>/dev/null || true
cp "${ROOT_DIR}/model/adapters/adapter_config.json" "${APP_BUNDLE}/Contents/Resources/adapter_config.json" 2>/dev/null || true

echo "2. Applying local ad-hoc code signature to ${APP_BUNDLE}..."
codesign --force --deep --sign - "${APP_BUNDLE}"

echo "3. Exporting real native SwiftUI app screenshots for documentation, website, and video..."
CLOUDPILOT_ROOT="${ROOT_DIR}" "${APP_BUNDLE}/Contents/MacOS/${APP_NAME}" \
  --export-screenshots "${ROOT_DIR}/marketing/assets/screenshots"

echo "4. Packaging installable macOS Disk Image (${DMG_PATH})..."
mkdir -p "${DMG_STAGING}"
cp -R "${APP_BUNDLE}" "${DMG_STAGING}/"
ln -s /Applications "${DMG_STAGING}/Applications"

cat > "${DMG_STAGING}/README_OFFLINE_INSTALL.txt" <<EOF
CloudPilot v1.0 for macOS (Apple Silicon M1/M2/M3/M4)
=====================================================
1. Drag CloudPilot.app to the Applications folder.
2. CloudPilot runs 100% locally on your Mac using Apple MLX Metal acceleration.
3. Zero Cloud API keys required. Normal workflow operates completely offline.
4. Signing Status: Ad-hoc local signature (unsigned/unnotarized with Apple Developer ID).
   On first launch in a new account, right-click CloudPilot.app -> Open.
EOF

hdiutil create \
  -volname "CloudPilot-v1.0-macOS" \
  -srcfolder "${DMG_STAGING}" \
  -ov \
  -format UDZO \
  "${DMG_PATH}" >/dev/null

echo "5. Built ${APP_BUNDLE} and ${DMG_PATH} successfully."
