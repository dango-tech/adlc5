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

  --tier TIER         reasoning | balanced | execution | implementation
                      (implementation is an alias for execution; fast routes to execution with a notice)
  --platform NAME     cursor | claude | codex | opencode | hermes | gemini | antigravity
                      (optional; auto-detect via env heuristics — best-effort)
  --step ID           optional lifecycle step for notice context
  --workspace DIR     optional consumer workspace (loads shared repo config)
  --feature NAME      optional; loads persona knobs from feature policies only
  -h, --help          show help

Config is chosen with `adlc5 setup models`: master settings in ~/.adlc5/config.yaml,
then repository overrides in the Git common directory. config.example.yaml is documentation only.

Pass --platform or configure default_host. With no configured choice, host default is used.

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
