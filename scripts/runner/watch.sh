#!/usr/bin/env bash
# Poll ADLC5 telemetry and kill-switch for a running dispatch.
set -euo pipefail

FEATURE=""
WORKSPACE="."
INTERVAL="${ADLC5_WATCH_INTERVAL:-5}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --feature) FEATURE="${2:?}"; shift 2 ;;
    --workspace) WORKSPACE="${2:?}"; shift 2 ;;
    --interval) INTERVAL="${2:?}"; shift 2 ;;
    -h|--help) exit 0 ;;
    *) echo "Unknown: $1" >&2; exit 1 ;;
  esac
done

[[ -n "$FEATURE" ]] || exit 1

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORKSPACE="$(cd "$WORKSPACE" && pwd)"

while true; do
  set +e
  "${ROOT}/scripts/pilot-check-kill-switch.sh" --feature "$FEATURE" --workspace "$WORKSPACE" >/dev/null 2>&1
  KS=$?
  set -e
  if [[ "$KS" -ne 0 ]]; then
    echo '{"watch":"kill_switch_triggered"}'
    exit 1
  fi
  if [[ -f "${ROOT}/scripts/tail-telemetry.sh" ]]; then
    "${ROOT}/scripts/tail-telemetry.sh" --feature "$FEATURE" --workspace "$WORKSPACE" --lines 3 2>/dev/null || true
  fi
  sleep "$INTERVAL"
done
