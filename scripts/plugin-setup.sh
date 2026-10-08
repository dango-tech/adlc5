#!/usr/bin/env bash
# Set up (or verify) a consumer repository for an ADLC5 host plugin. Host-neutral:
# the Claude plugin calls it as `adlc5-run plugin-setup.sh`; Codex can reuse it.
#
#   plugin-setup.sh [--project DIR] [--host claude|codex] [--check] [--yes]
#
# --check  report only (preflight, consumer root, what would be created, duplicates)
# default  initialize missing workspace scaffolding via init-workspace.sh; never
#          overwrites AGENTS.md, constitution files, customized config, state or evidence.
# Installs no global or project skills and no Cursor artifacts.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT=""
HOST="claude"
CHECK=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project) PROJECT="${2:?}"; shift 2 ;;
    --host) HOST="${2:?}"; shift 2 ;;
    --check) CHECK=1; shift ;;
    --yes) shift ;;
    -h|--help) sed -n '2,12p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

problems=0
need() { echo "  MISSING: $1" >&2; problems=1; }

echo "== Preflight"
command -v git >/dev/null 2>&1 && echo "  git: $(git --version)" || need "git (install Git)"
if (( BASH_VERSINFO[0] > 3 || (BASH_VERSINFO[0] == 3 && BASH_VERSINFO[1] >= 2) )); then
  echo "  bash: ${BASH_VERSION}"
else
  need "Bash 3.2+ (found ${BASH_VERSION})"
fi
if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
  echo "  python3: $(python3 --version 2>&1)"
else
  need "Python 3.10+ (python3)"
fi
command -v jq >/dev/null 2>&1 && echo "  jq: $(jq --version)" || need "jq (install jq)"
if (( problems )); then
  echo "Setup stopped: install the missing tools above, then re-run." >&2
  exit 1
fi

# Consumer root: explicit --project, else the repository containing the project/cwd.
start="${PROJECT:-${CLAUDE_PROJECT_DIR:-$PWD}}"
[[ -d "$start" ]] || { echo "ERROR: not a directory: $start" >&2; exit 2; }
start="$(cd "$start" && pwd -P)"
if top="$(git -C "$start" rev-parse --show-toplevel 2>/dev/null)"; then
  PROJECT="$(cd "$top" && pwd -P)"
else
  PROJECT="$start"
  echo "  note: ${PROJECT} is not a Git repository; lifecycle exclusions go to .gitignore"
fi
# shellcheck source=lib/adlc5-dirs.sh
source "${ROOT}/scripts/lib/adlc5-dirs.sh"
if adlc5_inside_package "$ROOT" "$PROJECT"; then
  echo "ERROR: ${PROJECT} is inside the installed ADLC5 package; run setup from your repository" >&2
  exit 2
fi

echo "== Consumer"
echo "  repository: ${PROJECT}"
echo "  runtime:    ${ROOT} ($(tr -d '[:space:]' <"${ROOT}/core/VERSION"))"
if git -C "$PROJECT" rev-parse --git-dir >/dev/null 2>&1 \
   && [[ "$(git -C "$PROJECT" rev-parse --absolute-git-dir)" != "$(git -C "$PROJECT" rev-parse --path-format=absolute --git-common-dir 2>/dev/null || echo x)" ]]; then
  echo "  linked worktree: static artifacts are shared via the common .git dir; feature state stays per worktree"
fi

echo "== Tracked additions to review and commit (existing files are never overwritten)"
for path in AGENTS.md .agents/architecture.yaml .agents/boundaries.yaml .agents/commands.yaml docs/adr; do
  if [[ -e "${PROJECT}/${path}" ]]; then echo "  exists:       ${path}"; else echo "  will create:  ${path}"; fi
done
echo "  Local only (excluded from diffs): .adlc5/ workspace + features, .agent-cache/"

if (( CHECK )); then
  python3 "${ROOT}/scripts/rebind-runtime.py" --workspace "$PROJECT" --adlc5-root "$ROOT" --dry-run >/dev/null || true
else
  echo "== Initialize"
  "${ROOT}/scripts/init-workspace.sh" --project "$PROJECT" --adlc5-root "$ROOT" \
    --no-skills --no-council-agents --refresh-runtime
fi

echo "== Coexistence"
python3 - "$PROJECT" "$ROOT" <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[2]) / "scripts"))
from lib.coexistence import find_duplicates

items = find_duplicates(Path(sys.argv[1]))
if not items:
    print("  no classic ADLC5 duplicates found")
for item in items:
    print(f"  DUPLICATE ({item['kind']}): {item['path']}\n    {item['message']}")
PY
echo
if (( CHECK )); then echo "Check complete (nothing written)."; else echo "Setup complete. Start a feature: invoke the adlc5 skill ('adlc5 for <feature>')."; fi
