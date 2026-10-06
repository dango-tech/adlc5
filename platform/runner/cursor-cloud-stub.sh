#!/usr/bin/env bash
# Stub — Cursor Cloud Agent runner adapter (wire when cloud API available).
set -euo pipefail
echo '{"status":"stub","message":"Use scripts/runner/dispatch.sh locally or integrate Cursor Cloud SDK"}' | jq .
exec "$(cd "$(dirname "$0")/../.." && pwd)/scripts/runner/dispatch.sh" "$@"
