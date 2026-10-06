#!/usr/bin/env bash
# H3 — Boy Scout reminder after agent file edits: run tests / lint on touched areas.
set -euo pipefail

input="$(cat)"

file_path="$(printf '%s' "$input" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
except json.JSONDecodeError:
    sys.exit(0)
path = data.get('file_path', '')
if isinstance(path, str):
    print(path, end='')
" 2>/dev/null || true)"

if [[ -n "$file_path" ]]; then
  echo "[adlc5 lint-hint] File edited: ${file_path}. Consider running relevant tests and lint before finishing (Boy Scout rule)." >&2
else
  echo "[adlc5 lint-hint] File edited. Consider running relevant tests and lint before finishing (Boy Scout rule)." >&2
fi

exit 0
