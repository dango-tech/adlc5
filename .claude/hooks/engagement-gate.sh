#!/usr/bin/env bash
# ADLC5 engagement gate for Claude Code (PreToolUse).
# Thin wrapper: all decision logic lives in scripts/engagement-gate.py.
set -euo pipefail

payload="$(cat)"
project_dir="${CLAUDE_PROJECT_DIR:-$(pwd)}"

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
  printf '%s' "$payload" | python3 "$gate" session-edit \
    --workspace "$project_dir" --platform claude --emit claude 2>/dev/null || true
fi
exit 0
