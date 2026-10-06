#!/usr/bin/env bash
# Validate context paths against v2 Delivery Persona memory walls.
set -euo pipefail

FEATURE=""
PERSONA=""
WORKSPACE="."
PATHS=()

usage() {
  cat <<'EOF'
Usage: ./scripts/memory/persona-pack-filter.sh --feature NAME --persona ID [--workspace DIR] [--paths PATH ...]

Exit 0 when all paths comply with personas.yaml allow/deny for the persona.
Exit 1 on violation (JSON on stdout).
EOF
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --feature) FEATURE="${2:?}"; shift 2 ;;
    --persona) PERSONA="${2:?}"; shift 2 ;;
    --workspace) WORKSPACE="${2:?}"; shift 2 ;;
    --paths)
      shift
      while [[ $# -gt 0 && "$1" != --* ]]; do
        PATHS+=("$1")
        shift
      done
      ;;
    -h|--help) usage ;;
    *) echo "Unknown: $1" >&2; usage ;;
  esac
done

[[ -n "$FEATURE" && -n "$PERSONA" ]] || usage

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
WORKSPACE="$(cd "$WORKSPACE" && pwd)"

if [[ ${#PATHS[@]} -eq 0 ]]; then
  echo '{"status":"warn","message":"no paths supplied"}'
  exit 2
fi

PATHS_JSON=$(printf '%s\n' "${PATHS[@]}" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read().splitlines()))')

python3 - <<PY
import json
import sys
sys.path.insert(0, "${ROOT}/scripts")
from lib.personas_load import check_persona_context

paths = json.loads('''${PATHS_JSON}''')
result = check_persona_context("${PERSONA}", paths, "${FEATURE}")
print(json.dumps(result, indent=2))
sys.exit(0 if result["status"] == "pass" else 1)
PY
