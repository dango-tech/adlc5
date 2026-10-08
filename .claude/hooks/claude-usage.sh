#!/usr/bin/env bash
set -euo pipefail

event="${1:?hook event is required}"
payload="$(cat)"
project_dir="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# shellcheck source=_adlc5-root.sh
source "$(dirname "${BASH_SOURCE[0]}")/_adlc5-root.sh"
adlc5_root="$(adlc5_resolve_root "$project_dir")"

collector="${adlc5_root}/scripts/claude-usage.py"
if [[ -n "$adlc5_root" && -f "$collector" ]]; then
  printf '%s' "$payload" | python3 "$collector" hook "$event" >/dev/null 2>&1 || true
fi
exit 0
