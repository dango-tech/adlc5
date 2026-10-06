#!/usr/bin/env bash
# Check whether merging base into HEAD would conflict (local git only).
set -euo pipefail

WORKSPACE="."
BASE=""

usage() {
  cat <<'EOF'
Usage: pr-reviewer-check-merge.sh [--workspace DIR] [--base BRANCH]

Stdout JSON: { mergeable, base, head, conflicts[] }
Exit 0 mergeable, 1 conflicts, 2 not a repo
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workspace) WORKSPACE="${2:?}"; shift 2 ;;
    --base) BASE="${2:?}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown: $1" >&2; exit 3 ;;
  esac
done

command -v jq >/dev/null || { echo '{"error":"jq required"}' >&2; exit 3; }
WORKSPACE="$(cd "$WORKSPACE" && pwd)"
cd "$WORKSPACE"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  jq -nc '{mergeable:false,error:"not a git repository"}'
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DETECT=$("${SCRIPT_DIR}/pr-reviewer-detect.sh" --workspace "$WORKSPACE")
[[ -n "$BASE" ]] || BASE=$(echo "$DETECT" | jq -r '.base_branch')
HEAD=$(echo "$DETECT" | jq -r '.branch')

git fetch origin "$BASE" 2>/dev/null || true
TARGET="origin/${BASE}"
git rev-parse --verify "$TARGET" >/dev/null 2>&1 || TARGET="$BASE"

CONFLICTS=()
set +e
git merge --no-commit --no-ff "$TARGET" >/dev/null 2>&1
EC=$?
git merge --abort >/dev/null 2>&1
git reset --hard HEAD >/dev/null 2>&1
set -e
if [[ "$EC" -ne 0 ]]; then
  CONFLICTS+=("merge ${TARGET} into ${HEAD} would fail")
fi

if [[ ${#CONFLICTS[@]} -eq 0 ]]; then
  jq -nc --arg base "$BASE" --arg head "$HEAD" '{mergeable:true,base:$base,head:$head,conflicts:[]}'
  exit 0
fi

CONFLICTS_JSON=$(printf '%s\n' "${CONFLICTS[@]}" | jq -R -s 'split("\n") | map(select(length>0))')
jq -nc --arg base "$BASE" --arg head "$HEAD" --argjson conflicts "$CONFLICTS_JSON" \
  '{mergeable:false,base:$base,head:$head,conflicts:$conflicts}'
exit 1
