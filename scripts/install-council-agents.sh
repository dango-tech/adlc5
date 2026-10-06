#!/usr/bin/env bash
# Install LLM Council Cursor subagents from config council_models.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DRY_RUN=0
TARGET_OVERRIDE=""
CONFIG_OVERRIDE=""

usage() {
  cat <<'EOF'
Usage: ./scripts/install-council-agents.sh [OPTIONS]

  --target DIR   Install agents here (default: cursor_agents_install_target from config)
  --config FILE  Read council_models from this yaml (default: config.yaml in adlc5 root)
  --dry-run      Print actions without writing agent files
  -h, --help     Show help

Installs discover-council-* and council-* agents for @discover / @ideate council runs.
Project-local .cursor/agents/ takes precedence over ~/.cursor/agents/ in Cursor.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target) TARGET_OVERRIDE="${2:?}"; shift 2 ;;
    --config) CONFIG_OVERRIDE="${2:?}"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown: $1" >&2; usage >&2; exit 1 ;;
  esac
done

CONFIG="${CONFIG_OVERRIDE:-${ROOT}/config.yaml}"
[[ -f "$CONFIG" ]] || CONFIG="${ROOT}/config.example.yaml"
[[ -f "$CONFIG" ]] || { echo "ERROR: no config file (tried config.yaml and config.example.yaml)" >&2; exit 1; }

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
  if [[ -z "$val" ]]; then val="$default"; fi
  printf '%s\n' "$val"
}

expand_path() {
  local path="$1"
  if [[ "$path" == "~" ]]; then printf '%s\n' "$HOME"
  elif [[ "$path" == "~/"* ]]; then printf '%s/%s\n' "$HOME" "${path:2}"
  else printf '%s\n' "$path"; fi
}

BODY_FILE="${ROOT}/templates/cursor-agents/_body.md"
[[ -f "$BODY_FILE" ]] || { echo "ERROR: missing ${BODY_FILE}" >&2; exit 1; }

# Match icarus/.cursor/agents — context=300k + effort=xhigh (not context=1m or effort=max; those show "Auto")
MODEL_CLAUDE="$(get_council_model claude "claude-opus-4-7[thinking=true,context=300k,effort=xhigh,fast=false]")"
MODEL_GPT="$(get_council_model gpt "gpt-5.3-codex[reasoning=extra-high,fast=true]")"
MODEL_GEMINI="$(get_council_model gemini "gemini-3.5-flash")"

if [[ -n "$TARGET_OVERRIDE" ]]; then
  TARGET="$(expand_path "$TARGET_OVERRIDE")"
else
  TARGET_RAW="$(get_yaml_value cursor_agents_install_target "$CONFIG")"
  [[ -z "$TARGET_RAW" ]] && TARGET_RAW="~/.cursor/agents"
  TARGET="$(expand_path "$TARGET_RAW")"
fi

write_agent() {
  local name="$1" model="$2" description="$3"
  local out="${TARGET}/${name}.md"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] ${out} (model: ${model})"
    return 0
  fi
  mkdir -p "$TARGET"
  {
    printf '%s\n' "---"
    printf 'name: %s\n' "$name"
    printf 'model: %s\n' "$model"
    printf 'description: %s\n' "$description"
    printf '%s\n' "---"
    printf '\n'
    cat "$BODY_FILE"
  } >"$out"
  echo "Installed ${out} (model: ${model})"
}

echo "Council models (from ${CONFIG}):"
echo "  claude: ${MODEL_CLAUDE}"
echo "  gpt:    ${MODEL_GPT}"
echo "  gemini: ${MODEL_GEMINI}"
echo "Target: ${TARGET}"
echo

write_agent "discover-council-claude" "$MODEL_CLAUDE" \
  "Discover LLM Council (Claude Opus 4.7 xhigh thinking). Use subagent_type discover-council-claude — not built-in council-claude."
write_agent "discover-council-gpt" "$MODEL_GPT" \
  "Discover LLM Council (GPT). Stateless exploration/risk member — use this agent name in Task, not built-in council-gpt."
write_agent "discover-council-gemini" "$MODEL_GEMINI" \
  "Discover LLM Council (Gemini 3.5 Flash). Use subagent_type discover-council-gemini — not built-in council-gemini. (Cursor lists 3.5 Flash, not 3.5 Pro.)"

write_agent "council-claude" "$MODEL_CLAUDE" \
  "LLM Council member for the Ideate skill. Receives a problem framing or risk challenge brief and returns structured solution directions or risk findings. Used in Phase 1 (Exploration) and Phase 2b (Risk Challenge)."
write_agent "council-gpt" "$MODEL_GPT" \
  "LLM Council member for the Ideate skill. Receives a problem framing or risk challenge brief and returns structured solution directions or risk findings. Used in Phase 1 (Exploration) and Phase 2b (Risk Challenge)."
write_agent "council-gemini" "$MODEL_GEMINI" \
  "LLM Council member for the Ideate skill. Receives a problem framing or risk challenge brief and returns structured solution directions or risk findings. Used in Phase 1 (Exploration) and Phase 2b (Risk Challenge)."

echo
echo "Council agents ready. Re-run after editing council_models in config."
