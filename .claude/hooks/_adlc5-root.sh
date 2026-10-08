#!/usr/bin/env bash
# Sourced by the ADLC5 Claude hook wrappers. Prints the ADLC5 root to use.
#   1. Plugin hook: CLAUDE_PLUGIN_ROOT (this package's own, current runtime).
#   2. Classic hook: .adlc5/workspace.json -> adlc5_root recorded at init time.
adlc5_resolve_root() {
  local project_dir="${1:?}"
  if [[ -n "${CLAUDE_PLUGIN_ROOT:-}" && -f "${CLAUDE_PLUGIN_ROOT}/scripts/adlc5" ]]; then
    printf '%s' "$CLAUDE_PLUGIN_ROOT"
    return 0
  fi
  python3 - "$project_dir" <<'PY'
import json
import sys
from pathlib import Path

config = Path(sys.argv[1]) / ".adlc5" / "workspace.json"
if config.is_file():
    try:
        print(json.loads(config.read_text(encoding="utf-8")).get("adlc5_root", ""), end="")
    except (json.JSONDecodeError, OSError):
        pass
PY
}
