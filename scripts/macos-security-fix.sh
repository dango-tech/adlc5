#!/usr/bin/env bash
# macOS Headless Security Scan Fix
# Addresses exit code 45 issues on macOS CI runners (GitHub Actions, etc.)
# Run this before executing security scanning tools on macOS headless environments.

set -euo pipefail

echo "Applying macOS headless security scan fixes..."

# 1. Unlock login keychain for headless operation
# Security tools like gitleaks, codesign, notarytool need keychain access
if [[ "$(uname)" == "Darwin" ]]; then
  echo "Unlocking login keychain..."
  security unlock-keychain -p "" ~/Library/Keychains/login.keychain-db 2>/dev/null || {
    echo "Warning: Could not unlock login keychain (may not exist in CI)"
  }

  # Create a temporary keychain if needed (for codesign/notarytool)
  if ! security list-keychains | grep -q "ci-keychain"; then
    echo "Creating CI keychain..."
    security create-keychain -p "" ci-keychain.keychain 2>/dev/null || true
    security list-keychains -s ~/Library/Keychains/login.keychain-db ci-keychain.keychain
    security default-keychain -s ci-keychain.keychain
    security unlock-keychain -p "" ci-keychain.keychain 2>/dev/null || true
  fi

  # 2. Disable Gatekeeper for downloaded tools (allows semgrep, gitleaks binaries to run)
  echo "Configuring Gatekeeper..."
  sudo spctl --master-disable 2>/dev/null || {
    echo "Warning: Could not disable Gatekeeper (requires sudo)"
  }

  # 3. Allow unsigned binaries from identified developers
  sudo spctl --disable --label "Developer ID" 2>/dev/null || true

  # 4. Set up environment variables for headless operation
  export CI=true
  export SECURITY_SCAN_HEADLESS=true

  # 5. Fix for semgrep on macOS (disable version check to avoid network calls)
  export SEMGREP_DISABLE_VERSION_CHECK=1

  # 6. Fix for gitleaks (disable git history scan if causing issues)
  export GITLEAKS_NO_GIT=false

  echo "macOS headless security scan fixes applied."
else
  echo "Not on macOS, skipping fixes."
fi