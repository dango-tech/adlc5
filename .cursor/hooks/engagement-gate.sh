#!/usr/bin/env bash
# H3 — ADLC5 engagement gate (fail fast on unstructured feature-sized work).
# Thin wrapper: all decision logic lives in scripts/engagement-gate.py.
# Warn by default; ADLC5_ENGAGEMENT_GATE=enforce denies the tool call.
set -euo pipefail

payload="$(cat)"
project_dir="${CURSOR_PROJECT_DIR:-$(pwd)}"

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
  if output="$(printf '%s' "$payload" | python3 "$gate" session-edit \
      --workspace "$project_dir" --platform cursor --emit cursor 2>/dev/null)"; then
    printf '%s\n' "$output"
    exit 0
  fi
fi

printf '%s\n' '{"permission":"allow"}'
