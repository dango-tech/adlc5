#!/usr/bin/env bash
# Smoke-test council agents: verify {discover-,}council-* files carry council_models slugs.
# Does NOT live-dispatch Tasks (only the host agent can spawn subagents). Exit 0 = match, 1 = mismatch.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TARGET_OVERRIDE=""
CONFIG_OVERRIDE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target) TARGET_OVERRIDE="${2:?}"; shift 2 ;;
    --config) CONFIG_OVERRIDE="${2:?}"; shift 2 ;;
    -h|--help)
      echo "Usage: ./scripts/smoke-test-council.sh [--target DIR] [--config FILE]"
      exit 0
      ;;
    *) echo "Unknown: $1" >&2; exit 1 ;;
  esac
done

CONFIG="${CONFIG_OVERRIDE:-${ROOT}/config.yaml}"
[[ -f "$CONFIG" ]] || CONFIG="${ROOT}/config.example.yaml"
[[ -f "$CONFIG" ]] || { echo "ERROR: no config.yaml or config.example.yaml" >&2; exit 2; }

get_yaml_value() {
  local key="$1" file="$2"
  grep -E "^${key}:" "$file" 2>/dev/null | head -1 | sed -E "s/^${key}:[[:space:]]*//" | sed -E 's/^["'\''](.*)["'\'']$/\1/' | sed -E 's/[[:space:]]+#.*$//' || true
}

get_council_model() {
  local member="$1" default="$2"
  local val
  val="$(awk -v member="$member" '
    /^council_models:/ { in_block=1; next }
    in_block && /^[^[:space:]]/ { in_block=0 }
    in_block && $1 == member":" {
      sub(/^[^:]*:[[:space:]]*/, "")
      gsub(/^["'\''"]|["'\''"]$/, "")
      gsub(/[[:space:]]+#.*$/, "")
      print
      exit
    }
  ' "$CONFIG")"
  if [[ -z "$val" && "$CONFIG" != "${ROOT}/config.example.yaml" && -f "${ROOT}/config.example.yaml" ]]; then
    val="$(awk -v member="$member" '
      /^council_models:/ { in_block=1; next }
      in_block && /^[^[:space:]]/ { in_block=0 }
      in_block && $1 == member":" {
        sub(/^[^:]*:[[:space:]]*/, "")
        gsub(/^["'\''"]|["'\''"]$/, "")
        gsub(/[[:space:]]+#.*$/, "")
        print
        exit
      }
    ' "${ROOT}/config.example.yaml")"
  fi
  [[ -z "$val" ]] && val="$default"
  printf '%s\n' "$val"
}

expand_path() {
  local path="$1"
  if [[ "$path" == "~" ]]; then printf '%s\n' "$HOME"
  elif [[ "$path" == "~/"* ]]; then printf '%s/%s\n' "$HOME" "${path:2}"
  else printf '%s\n' "$path"; fi
}

if [[ -n "$TARGET_OVERRIDE" ]]; then
  TARGET="$(expand_path "$TARGET_OVERRIDE")"
else
  TARGET_RAW="$(get_yaml_value cursor_agents_install_target "$CONFIG")"
  [[ -z "$TARGET_RAW" ]] && TARGET_RAW="~/.cursor/agents"
  TARGET="$(expand_path "$TARGET_RAW")"
fi

MODEL_CLAUDE="$(get_council_model claude "claude-opus-4-7[thinking=true,context=300k,effort=xhigh,fast=false]")"
MODEL_GPT="$(get_council_model gpt "gpt-5.3-codex[reasoning=extra-high,fast=true]")"
MODEL_GEMINI="$(get_council_model gemini "gemini-3.5-flash")"

echo "Council smoke test (config: ${CONFIG})"
echo "  Target dir: ${TARGET}"
echo

expected_for() {
  case "$1" in
    claude) printf '%s\n' "$MODEL_CLAUDE" ;;
    gpt) printf '%s\n' "$MODEL_GPT" ;;
    gemini) printf '%s\n' "$MODEL_GEMINI" ;;
  esac
}

errors=0
for prefix in "discover-council" "council"; do
  for member in claude gpt gemini; do
    f="${TARGET}/${prefix}-${member}.md"
    expected="$(expected_for "$member")"
    if [[ ! -r "$f" ]]; then
      echo "  FAIL: ${prefix}-${member}.md missing"
      errors=$((errors + 1))
      continue
    fi
    actual="$(grep -E '^model:' "$f" | head -1 | sed -E 's/^model:[[:space:]]*//')"
    if [[ "$actual" == "$expected" ]]; then
      echo "  OK:   ${prefix}-${member} -> ${actual}"
    else
      echo "  FAIL: ${prefix}-${member} -> got '${actual}', expected '${expected}'"
      errors=$((errors + 1))
    fi
  done
done

echo
if [[ "$errors" -eq 0 ]]; then
  echo "Config <-> agent file slugs match (3 members x 2 prefixes)."
else
  echo "MISMATCH (${errors}). Run: ./scripts/install-council-agents.sh --target ${TARGET}" >&2
fi

cat <<'NOTE'

NOTE: This script only verifies static config<->agent-file consistency.
To verify Cursor ACTUALLY routes each council member to the configured model,
ask the host agent to run the live smoke test:

  "Spawn discover-council-claude, discover-council-gpt, and
   discover-council-gemini in parallel and have each one self-identify
   its model family and version."

Project-local .cursor/agents/ overrides ~/.cursor/agents/ — install council
agents into the repo you are testing (init-workspace.sh does this automatically).

If Claude or Gemini show "Auto" in the Task header, the model slug is invalid for
your plan. Use context=300k and effort=xhigh (not context=1m or effort=max).
NOTE

[[ "$errors" -eq 0 ]] || exit 1
exit 0
