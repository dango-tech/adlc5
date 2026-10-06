#!/usr/bin/env bash
# Compatibility entry point; one implementation assembles the handoff.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/generate-pack.py" "$@"
