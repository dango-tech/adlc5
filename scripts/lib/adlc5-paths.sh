#!/usr/bin/env bash
# Canonical ADLC5 workspace paths with explicit legacy fallbacks.
set -euo pipefail

adlc5_feature_root() {
  local workspace="$1" feature="$2"
  echo "${workspace}/.adlc5/${feature}"
}

adlc5_state() {
  adlc5_feature_root "$1" "$2"/state.json
}

# Compatibility name for callers written before the unified-state migration.
adlc5_lifecycle_state() {
  adlc5_state "$1" "$2"
}

# Legacy delivery path; new code writes only state.json.
adlc5_delivery_state() {
  adlc5_feature_root "$1" "$2"/delivery/state.json
}

# Prefer canonical schema-v3 state; read legacy delivery/forge only for compatibility.
adlc5_valid_canonical_state() {
  local path="$1" scripts_dir
  scripts_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  python3 - "$scripts_dir" "$path" <<'PY' >/dev/null 2>&1
import json
import sys

sys.path.insert(0, sys.argv[1])
from lib.state_v2 import validate_against_schema

with open(sys.argv[2], encoding="utf-8") as handle:
    state = json.load(handle)
raise SystemExit(1 if validate_against_schema(state) else 0)
PY
}

adlc5_resolve_state() {
  local workspace="$1" feature="$2"
  local root canonical delivery forge
  root="$(adlc5_feature_root "$workspace" "$feature")"
  canonical="${root}/state.json"
  delivery="${root}/delivery/state.json"
  forge="${root}/forge/state.json"
  if [[ -f "$canonical" ]] && adlc5_valid_canonical_state "$canonical"; then
    echo "$canonical"
    return 0
  fi
  if [[ -f "$delivery" ]]; then
    [[ "${ADLC5_SUPPRESS_LEGACY_WARNINGS:-0}" == "1" ]] || \
      echo "WARN: using legacy delivery/state.json; canonical schema-v3 state.json is missing" >&2
    echo "$delivery"
    return 0
  fi
  if [[ -f "$forge" ]]; then
    [[ "${ADLC5_SUPPRESS_LEGACY_WARNINGS:-0}" == "1" ]] || \
      echo "WARN: using legacy forge/state.json; re-run init-feature.sh to create canonical state.json" >&2
    echo "$forge"
    return 0
  fi
  echo "$canonical"
}

adlc5_current_step() {
  local state
  state="$(adlc5_resolve_state "$1" "$2")"
  [[ -f "$state" ]] || return 0
  jq -r '.current_step // .current_phase // empty' "$state" 2>/dev/null || true
}

# Deprecated compatibility alias.
adlc5_resolve_delivery_state() {
  adlc5_resolve_state "$1" "$2"
}
