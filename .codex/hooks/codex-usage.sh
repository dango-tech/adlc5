#!/usr/bin/env bash
set -euo pipefail

event="${1:?hook event is required}"
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

collector="${adlc5_root}/scripts/codex-usage.py"
if [[ -n "$adlc5_root" && -f "$collector" ]]; then
  printf '%s' "$payload" | python3 "$collector" hook "$event" >/dev/null 2>&1 || true
fi
exit 0
