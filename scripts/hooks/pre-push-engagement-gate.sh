#!/usr/bin/env bash
# ADLC5 engagement gate — git pre-push backstop.
# adlc5-engagement-gate: installed by init-workspace.sh --with-git-hooks
#
# Safety net for work that never passed through an agent hook (manual commits,
# non-agent editors). Warn only: always exits 0, the push always proceeds.
set -uo pipefail

project_dir="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

adlc5_root="$(
  python3 - "$project_dir" <<'PY' 2>/dev/null
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
  python3 "$gate" check-branch --workspace "$project_dir" || true
fi
exit 0
