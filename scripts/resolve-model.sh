#!/usr/bin/env bash
# Resolve abstract ADLC5 model tier → host model ID (JSON on stdout).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLATFORM=""
TIER=""
STEP=""
WORKSPACE=""
FEATURE=""

usage() {
  cat <<'EOF'
Usage: ./scripts/resolve-model.sh --tier TIER [OPTIONS]

  --tier TIER         reasoning | balanced | execution | implementation | fast
                      (implementation is an alias for execution)
  --platform NAME     cursor | claude | codex | opencode | hermes | gemini | antigravity
                      (optional; auto-detect via env heuristics — best-effort)
  --step ID           optional lifecycle step for notice context
  --workspace DIR     optional consumer workspace (loads .adlc5/config.yaml)
  --feature NAME      optional; loads persona knobs from feature policies only
  -h, --help          show help

Merge order: config.example.yaml ← repo config.yaml ← workspace .adlc5/config.yaml
Feature policies (.adlc5/{feature}/policies.yaml) affect persona knobs
(fresh_session, verifier_different_model) and may override execution_policy
via model_routing.execution_policy — inherit|explicit — which wins over the
config.yaml default for that feature only. See core/guides/model-matrix.md.

Platform detection limitations: env heuristics are best-effort; pass --platform when known.

Stdout: JSON {tier, model_id, spawn_policy, fresh_session, platform, notice, version, ...}
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --platform) PLATFORM="${2:?}"; shift 2 ;;
    --tier) TIER="${2:?}"; shift 2 ;;
    --step) STEP="${2:?}"; shift 2 ;;
    --workspace) WORKSPACE="${2:?}"; shift 2 ;;
    --feature) FEATURE="${2:?}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ -n "$TIER" ]] || { usage >&2; exit 2; }

ARGS=(--root "$ROOT" --tier "$TIER")
[[ -n "$PLATFORM" ]] && ARGS+=(--platform "$PLATFORM")
[[ -n "$STEP" ]] && ARGS+=(--step "$STEP")
[[ -n "$WORKSPACE" ]] && ARGS+=(--workspace "$WORKSPACE")
[[ -n "$FEATURE" ]] && ARGS+=(--feature "$FEATURE")

export PYTHONPATH="${ROOT}/scripts${PYTHONPATH:+:$PYTHONPATH}"
exec python3 "${ROOT}/scripts/lib/model_routing.py" "${ARGS[@]}"
