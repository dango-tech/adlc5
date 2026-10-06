#!/usr/bin/env bash
# Validate evidence path:line-range exists at workspace HEAD.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=wiki-lib.sh
source "${SCRIPT_DIR}/wiki-lib.sh"

WORKSPACE="."
EVIDENCE=""
GREP_PATTERN=""

usage() {
  cat <<'EOF'
Usage: validate-claim.sh --evidence "path:start-end" [--workspace DIR]
       validate-claim.sh --grep "pattern" --path path/to/file [--workspace DIR]

Exit 0 if evidence resolves; 1 otherwise.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workspace) WORKSPACE="${2:?}"; shift 2 ;;
    --evidence) EVIDENCE="${2:?}"; shift 2 ;;
    --grep) GREP_PATTERN="${2:?}"; shift 2 ;;
    --path) GREP_PATH="${2:?}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown: $1" >&2; exit 1 ;;
  esac
done

WS="$(wiki_resolve_workspace "$WORKSPACE")"

if [[ -n "$GREP_PATTERN" ]]; then
  [[ -n "${GREP_PATH:-}" ]] || { echo "ERROR: --path required with --grep" >&2; exit 1; }
  TARGET="${WS}/${GREP_PATH}"
  [[ -f "$TARGET" ]] || { echo "FAIL: file not found: ${GREP_PATH}" >&2; exit 1; }
  if grep -qE "$GREP_PATTERN" "$TARGET" 2>/dev/null; then
    echo "OK: pattern found in ${GREP_PATH}"
    exit 0
  fi
  echo "FAIL: pattern not found in ${GREP_PATH}" >&2
  exit 1
fi

[[ -n "$EVIDENCE" ]] || { echo "ERROR: --evidence or --grep required" >&2; exit 1; }

wiki_parse_evidence "$EVIDENCE"
TARGET="${WS}/${WIKI_EVIDENCE_PATH}"

[[ -f "$TARGET" ]] || { echo "FAIL: file not found: ${WIKI_EVIDENCE_PATH}" >&2; exit 1; }

LINES="$(wc -l <"$TARGET" | tr -d ' ')"
if [[ "$WIKI_EVIDENCE_START" -gt "$LINES" ]]; then
  echo "FAIL: start line ${WIKI_EVIDENCE_START} > file lines ${LINES}" >&2
  exit 1
fi

if [[ "$WIKI_EVIDENCE_END" -lt "$WIKI_EVIDENCE_START" ]]; then
  echo "FAIL: invalid line range" >&2
  exit 1
fi

SNIP="$(sed -n "${WIKI_EVIDENCE_START},${WIKI_EVIDENCE_END}p" "$TARGET" | head -c 200)"
echo "OK: ${WIKI_EVIDENCE_PATH}:${WIKI_EVIDENCE_START}-${WIKI_EVIDENCE_END}"
echo "Preview: ${SNIP}..."
exit 0
