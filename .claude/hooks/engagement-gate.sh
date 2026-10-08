#!/usr/bin/env bash
# ADLC5 engagement gate for Claude Code (PreToolUse).
# Thin wrapper: all decision logic lives in scripts/engagement-gate.py.
set -euo pipefail

payload="$(cat)"
project_dir="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# shellcheck source=_adlc5-root.sh
source "$(dirname "${BASH_SOURCE[0]}")/_adlc5-root.sh"
adlc5_root="$(adlc5_resolve_root "$project_dir")"

gate="${adlc5_root}/scripts/engagement-gate.py"
if [[ -n "$adlc5_root" && -f "$gate" ]]; then
  printf '%s' "$payload" | python3 "$gate" session-edit \
    --workspace "$project_dir" --platform claude --emit claude 2>/dev/null || true
fi
exit 0
