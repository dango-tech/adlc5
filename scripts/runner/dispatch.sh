#!/usr/bin/env bash
# Local ADLC5 navigator — init feature + emit the next host-executor handoff.
set -euo pipefail

FEATURE=""
WORKSPACE="."
MAX_ITER="${ADLC5_MAX_ITER:-200}"
MODE="brownfield"

usage() {
  cat <<'EOF'
Usage: ./scripts/runner/dispatch.sh --feature NAME [--workspace DIR] [--max-iter N]

Runs the deterministic pilot navigator without an agent host. Emits `done`,
`halted`, or `needs_executor` JSON to stdout; a host adapter must execute
spawn/advance/heal actions and invoke this command again.
EOF
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --feature) FEATURE="${2:?}"; shift 2 ;;
    --workspace) WORKSPACE="${2:?}"; shift 2 ;;
    --max-iter) MAX_ITER="${2:?}"; shift 2 ;;
    --mode) MODE="${2:?}"; shift 2 ;;
    -h|--help) usage ;;
    *) echo "Unknown: $1" >&2; usage ;;
  esac
done

[[ -n "$FEATURE" ]] || usage
command -v jq >/dev/null || { echo "ERROR: jq required" >&2; exit 1; }

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORKSPACE="$(cd "$WORKSPACE" && pwd)"
export ADLC5_WORKSPACE="$WORKSPACE"

STATE="${WORKSPACE}/.adlc5/${FEATURE}/state.json"
if [[ ! -f "$STATE" ]]; then
  "${ROOT}/scripts/init-feature.sh" --feature "$FEATURE" --workspace "$WORKSPACE" --mode "$MODE" --interaction autonomous >&2
fi

iter=0
LAST='{}'
while [[ "$iter" -lt "$MAX_ITER" ]]; do
  iter=$((iter + 1))
  set +e
  OUT=$("${ROOT}/scripts/pilot-autopilot.sh" --feature "$FEATURE" --workspace "$WORKSPACE" 2>&1)
  EC=$?
  set -e
  LAST="$OUT"
  ACTION=$(echo "$OUT" | jq -r '.action // empty')
  case "$ACTION" in
    done)
      echo "$OUT" | jq '. + {dispatch:"completed","iterations":'"$iter"'}'
      exit 0
      ;;
    halt)
      echo "$OUT" | jq '. + {dispatch:"halted","iterations":'"$iter"'}'
      exit 1
      ;;
    spawn|advance|heal)
      PERSONA=$(echo "$OUT" | jq -r '.persona // empty')
      FRESH=$(echo "$OUT" | jq -c '.fresh_session // false')
      echo "$OUT" | jq '. + {
        dispatch:"needs_executor",
        executor_required:true,
        iterations:'"$iter"',
        persona_hint:$p,
        fresh_session:$f
      }' --arg p "$PERSONA" --argjson f "$FRESH"
      exit 1
      ;;
    *)
      echo "$OUT" | jq '. + {dispatch:"error","iterations":'"$iter"'}'
      exit 2
      ;;
  esac
  [[ "$EC" -eq 3 ]] && echo "$OUT" | jq '. + {dispatch:"completed"}' && exit 0
done

echo "$LAST" | jq '. + {dispatch:"max_iter","iterations":'"$iter"'}'
exit 1
