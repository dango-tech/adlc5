#!/usr/bin/env bash
# H2 — Scope guard (agent-discipline).
# Default when activated: warn (allow + agent_message).
# Hard-fail: ADLC5_SCOPE_GUARD=enforce or policies.yaml scope_guard.mode: enforce.
# Inactive when no scope metadata / env mode (allow + audit log only).
set -euo pipefail

input="$(cat)"
project_dir="${CURSOR_PROJECT_DIR:-.}"
log_dir="${project_dir}/.cursor/hooks/state"
log_file="${log_dir}/scope-guard.log"
mkdir -p "$log_dir"

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECKER="${HOOK_DIR}/scope-guard-check.py"
if [[ ! -f "$CHECKER" ]]; then
  # Consumer copy may live beside this script after init-workspace --with-hooks
  CHECKER="$(dirname "$0")/scope-guard-check.py"
fi

redacted="$(printf '%s' "$input" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
except json.JSONDecodeError:
    sys.exit(1)
data.pop('user_email', None)
print(json.dumps(data, separators=(',', ':')))
" 2>/dev/null || printf '%s' "$input")"
printf '%s\n' "$redacted" >> "$log_file"

if [[ -f "$CHECKER" ]]; then
  result="$(
    printf '%s' "$input" | ADLC5_SCOPE_GUARD="${ADLC5_SCOPE_GUARD:-}" \
      python3 "$CHECKER" --project "$project_dir" 2>>"$log_file" \
      || printf '{ "permission": "allow" }\n'
  )"
else
  result='{ "permission": "allow" }'
fi

printf '%s\n' "$result" >> "$log_file"
printf '%s\n' "$result"
exit 0
