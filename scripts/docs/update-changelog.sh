#!/usr/bin/env bash
# Append conventional-commit summary to CHANGELOG Unreleased section (v2 helper).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CHANGELOG="${ROOT}/CHANGELOG.md"
MSG="${1:-}"

if [[ -z "$MSG" ]]; then
  echo "Usage: ./scripts/docs/update-changelog.sh \"description of change\"" >&2
  exit 1
fi

[[ -f "$CHANGELOG" ]] || { echo "ERROR: CHANGELOG.md missing" >&2; exit 1; }

ENTRY="- ${MSG}"
if grep -qF "$ENTRY" "$CHANGELOG" 2>/dev/null; then
  echo "Entry already present"
  exit 0
fi

python3 <<PY
from pathlib import Path
path = Path("${CHANGELOG}")
text = path.read_text(encoding="utf-8")
needle = "### Added\n"
entry = "- ${MSG}\n"
if needle in text:
    text = text.replace(needle, needle + entry, 1)
else:
    text = "## [Unreleased]\n\n### Added\n" + entry + "\n" + text
path.write_text(text, encoding="utf-8")
print("Updated CHANGELOG.md")
PY
