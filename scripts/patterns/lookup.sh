#!/usr/bin/env bash
# Thin wrapper — OKF catalog lookup (ids/paths only). See lookup.py.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
exec python3 "${ROOT}/scripts/patterns/lookup.py" "$@"
