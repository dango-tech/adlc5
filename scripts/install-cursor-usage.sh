#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="${HOME}/.adlc5/cursor-usage.env"
LABEL="com.adlc5.cursor-usage"
PLIST="${HOME}/Library/LaunchAgents/${LABEL}.plist"
ACTION="configure"

usage() {
  cat <<'EOF'
Usage: ./scripts/install-cursor-usage.sh [--enable|--disable]

Creates ~/.adlc5/cursor-usage.env with mode 0600.
On macOS, --enable installs an hourly LaunchAgent that reconciles registered
ADLC5 workspaces with Cursor's official usage API. Fill in the config first.

The LaunchAgent runs `sync-cloud-all` (Cloud Agent API, works with a personal
User API key) by default. `sync-all` (Admin API, needs a Team/Org Admin key)
is not scheduled automatically — run it manually once you have that key type.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --enable) ACTION="enable"; shift ;;
    --disable) ACTION="disable"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ "$ACTION" == "disable" ]]; then
  if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "ERROR: --disable currently supports macOS LaunchAgents only." >&2
    exit 2
  fi
  launchctl bootout "gui/${UID}" "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"
  echo "Disabled ${LABEL}"
  exit 0
fi

mkdir -p "${HOME}/.adlc5"
if [[ ! -f "$CONFIG" ]]; then
  cat >"$CONFIG" <<'EOF'
# Personal Cursor API key (Dashboard → API Keys). Works with Cloud Agent API
# endpoints (/v1/agents, /v1/agents/{id}/usage) used by sync-cloud/sync-cloud-all.
CURSOR_API_KEY=

# Team OR Organization Admin API key. Only works if your account has that key
# type (see docs/cursor-usage.md); needed for sync/sync-all (Admin API,
# /teams/filtered-usage-events) and left blank otherwise.
CURSOR_ADMIN_API_KEY=

# Team email whose Cursor usage should be reconciled — only used by sync/sync-all.
CURSOR_USAGE_EMAIL=
EOF
  echo "Created ${CONFIG}"
else
  echo "Config exists: ${CONFIG}"
fi
chmod 600 "$CONFIG"

if [[ "$ACTION" == "configure" ]]; then
  echo "Edit ${CONFIG}, then run: $0 --enable"
  exit 0
fi

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "ERROR: --enable currently supports macOS LaunchAgents only." >&2
  exit 2
fi

python3 - "$ROOT" "$CONFIG" <<'PY'
import importlib.util
import sys
from pathlib import Path

module_path = Path(sys.argv[1]) / "scripts" / "cursor-usage.py"
spec = importlib.util.spec_from_file_location("cursor_usage", module_path)
if spec is None or spec.loader is None:
    raise SystemExit(f"ERROR: cannot load {module_path}")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
config = module.read_config(Path(sys.argv[2]))
if not (config.get("CURSOR_API_KEY") or config.get("CURSOR_ADMIN_API_KEY")):
    raise SystemExit(
        "ERROR: fill in CURSOR_API_KEY (or CURSOR_ADMIN_API_KEY) before --enable"
    )
PY

mkdir -p "$(dirname "$PLIST")" "${HOME}/.adlc5/logs"
# Resolve the real interpreter binary this install actually ran with --
# /usr/bin/python3 doesn't exist on machines where python3 comes from
# Homebrew, pyenv, or conda, and launchd has no shell/PATH to fall back on.
PYTHON3_BIN="$(python3 -c 'import sys; print(sys.executable)')"
python3 - "$PLIST" "$ROOT" "$CONFIG" "$LABEL" "$PYTHON3_BIN" <<'PY'
import plistlib
import sys
from pathlib import Path

plist, root, config, label, python3_bin = sys.argv[1:]
home = Path.home()
value = {
    "Label": label,
    "ProgramArguments": [
        python3_bin,
        str(Path(root) / "scripts" / "cursor-usage.py"),
        "sync-cloud-all",
        "--config",
        config,
    ],
    "StartInterval": 3600,
    "RunAtLoad": True,
    "StandardOutPath": str(home / ".adlc5" / "logs" / "cursor-usage.log"),
    "StandardErrorPath": str(home / ".adlc5" / "logs" / "cursor-usage-error.log"),
}
with Path(plist).open("wb") as handle:
    plistlib.dump(value, handle)
PY

launchctl bootout "gui/${UID}" "$PLIST" 2>/dev/null || true
launchctl bootstrap "gui/${UID}" "$PLIST"
echo "Enabled hourly Cursor usage reconciliation: ${PLIST}"
