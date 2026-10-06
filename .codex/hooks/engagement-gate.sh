#!/usr/bin/env bash
# ADLC5 engagement gate for Codex CLI (UserPromptSubmit and PreToolUse).
#
# Codex's `apply_patch` tool reports its edit as an opaque `tool_input.command`
# patch string rather than a path list, so both events use the worktree scan:
# the gate derives the session's touched-file set from `git status --porcelain`
# instead of from the payload. Same threshold, same message.
#
# Argument selects the event being served (default: user-prompt-submit):
#   user-prompt-submit  plain stdout, surfaced as prompt context
#   pre-tool-use        JSON, because Codex ignores plain stdout on PreToolUse
set -euo pipefail

event="${1:-user-prompt-submit}"
case "$event" in
  # Codex documents the same `hookSpecificOutput` PreToolUse shape Claude Code
  # uses (hookEventName/permissionDecision/permissionDecisionReason/
  # additionalContext), so the gate's `claude` payload format is valid here.
  pre-tool-use) emit_format="claude" ;;
  *) emit_format="plain" ;;
esac

payload="$(cat)"
project_dir="${CODEX_PROJECT_DIR:-$(pwd)}"

adlc5_root="$(
  python3 - "$project_dir" <<'PY'
import json
import sys
from pathlib import Path

workspace = Path(sys.argv[1])
config = workspace / ".adlc5" / "workspace.json"
if config.is_file():
    try:
        value = json.loads(config.read_text(encoding="utf-8"))
        print(value.get("adlc5_root", ""))
    except (json.JSONDecodeError, OSError):
        pass
PY
)"

gate="${adlc5_root}/scripts/engagement-gate.py"
if [[ -n "$adlc5_root" && -f "$gate" ]]; then
  printf '%s' "$payload" | python3 "$gate" scan \
    --workspace "$project_dir" --platform codex --emit "$emit_format" 2>/dev/null || true
fi
exit 0
