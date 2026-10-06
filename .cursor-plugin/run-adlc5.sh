#!/usr/bin/env bash
# Plugin-local entry → distribution kernel façade (repo root = ADLC5_ROOT).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export ADLC5_ROOT="$ROOT"
exec python3 "${ROOT}/scripts/adlc5" "$@"
