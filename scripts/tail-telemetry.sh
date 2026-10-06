#!/usr/bin/env bash
# Tail ADLC5 feature telemetry (events.jsonl).
set -euo pipefail

FEATURE=""
WORKSPACE="."
LINES=20
FOLLOW=false

usage() {
  cat <<'EOF'
Usage: tail-telemetry.sh --feature NAME [--workspace DIR] [-n LINES] [-f]

Prints last N telemetry events (JSON lines). With -f, follows the file.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --feature) FEATURE="${2:?}"; shift 2 ;;
    --workspace) WORKSPACE="${2:?}"; shift 2 ;;
    -n) LINES="${2:?}"; shift 2 ;;
    -f) FOLLOW=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown: $1" >&2; exit 2 ;;
  esac
done

[[ -n "$FEATURE" ]] || { usage >&2; exit 2; }

WORKSPACE="$(cd "$WORKSPACE" && pwd)"
EVENTS="${WORKSPACE}/.adlc5/${FEATURE}/telemetry/events.jsonl"

if [[ ! -f "$EVENTS" ]]; then
  echo "No telemetry at ${EVENTS}" >&2
  exit 1
fi

if [[ "$FOLLOW" == "true" ]]; then
  tail -n "$LINES" -f "$EVENTS"
else
  tail -n "$LINES" "$EVENTS"
fi
