#!/usr/bin/env bash
# Normalize alternate phase/stage IDs on read.
# Routers and scripts write canonical IDs only.
set -euo pipefail

normalize_phase_id() {
  local id="${1:-}"
  case "$id" in
    specify-*) echo "${id/specify-/plan-}" ;;
    1a) echo "plan-1-discovery" ;;
    1b) echo "plan-2-contracts" ;;
    1c) echo "plan-3-operations" ;;
    2) echo "plan-4-user-stories" ;;
    3) echo "plan-5-code-spec" ;;
    4) echo "build-1-implementation" ;;
    5) echo "assure-1-verification" ;;
    6) echo "assure-2-integration" ;;
    assure-4-pr-review) echo "assure-4-pr-reviewer" ;;
    *) echo "$id" ;;
  esac
}

# v2 gate ID normalization (see core/gates.yaml legacy_aliases)
normalize_v2_gate_id() {
  local gate="${1:-}"
  case "$gate" in
    specify-complete) echo "specify-complete" ;;
    plan-complete) echo "plan-complete" ;;
    tasks-complete) echo "tasks-complete" ;;
    implement-1-build) echo "build-1-implementation" ;;
    implement-2-verify) echo "assure-1-verification" ;;
    implement-3-integrate) echo "assure-2-integration" ;;
    implement-4-qa) echo "assure-3-qa" ;;
    implement-5-pr) echo "assure-4-pr-reviewer" ;;
    spec-4-exit) echo "specify-complete" ;;
    plan-5-code-spec) echo "tasks-complete" ;;
    *) echo "$gate" ;;
  esac
}

# v2 step ID from legacy delivery phase
normalize_v2_step_id() {
  local phase
  phase=$(normalize_phase_id "${1:-}")
  case "$phase" in
    plan-1-discovery) echo "plan-4-design-discovery" ;;
    plan-2-contracts) echo "plan-5-design-contracts" ;;
    plan-3-operations) echo "plan-6-design-operations" ;;
    plan-4-user-stories) echo "tasks-1-stories" ;;
    plan-5-code-spec) echo "tasks-2-code-spec" ;;
    build-1-implementation) echo "implement-1-build" ;;
    assure-1-verification) echo "implement-2-verify" ;;
    assure-2-integration) echo "implement-3-integrate" ;;
    assure-3-qa) echo "implement-4-qa" ;;
    assure-4-pr-reviewer) echo "implement-5-pr" ;;
    *) echo "$phase" ;;
  esac
}

normalize_lifecycle_stage() {
  local s="${1:-}"
  case "$s" in
    engineer) echo "engineering" ;;
    specify) echo "plan" ;;
    *) echo "$s" ;;
  esac
}

normalize_engineering_step() {
  local id="${1:-}"
  if [[ "$id" == engineer-* ]]; then
    echo "engineering-${id#engineer-}"
  else
    echo "$id"
  fi
}

phase_status_key_from_phase_id() {
  local id
  id=$(normalize_phase_id "$1")
  echo "${id//-/_}"
}

# Canonical plan_* keys; alternate keys merged on read
phase_status_get() {
  local phase_status_json="$1" phase_id="$2"
  local key legacy k v
  key=$(phase_status_key_from_phase_id "$phase_id")
  command -v jq >/dev/null || return 1
  v=$(jq -r --arg k "$key" '.[$k] // empty' <<<"$phase_status_json")
  if [[ -n "$v" && "$v" != "null" ]]; then
    echo "$v"
    return 0
  fi
  # alternate key fallbacks
  case "$key" in
    plan_discovery) legacy=design_1a ;;
    plan_contracts) legacy=design_1b ;;
    plan_operations) legacy=design_1c ;;
    plan_user_stories) legacy=user_stories ;;
    plan_code_spec) legacy=code_spec ;;
    build_implementation) legacy=implementation ;;
    assure_verification) legacy=verification ;;
    assure_integration) legacy=integration ;;
    *) legacy="${key/plan_/specify_}" ;;
  esac
  jq -r --arg k "$key" --arg l "$legacy" '.[$k] // .[$l] // "pending"' <<<"$phase_status_json"
}
