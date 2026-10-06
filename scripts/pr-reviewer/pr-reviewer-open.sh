#!/usr/bin/env bash
# Open or update a pull request (GitHub via gh; other providers emit instructions JSON).
set -euo pipefail

FEATURE=""
WORKSPACE="."
TITLE=""
BODY_FILE=""
BASE=""
DRAFT=false

usage() {
  cat <<'EOF'
Usage: pr-reviewer-open.sh --feature NAME [--workspace DIR] [--title TITLE] [--body-file FILE] [--base BRANCH] [--draft]

Exit 0 PR opened (GitHub). Exit 1 blocked. Exit 2 manual required (JSON instructions on stdout).
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --feature) FEATURE="${2:?}"; shift 2 ;;
    --workspace) WORKSPACE="${2:?}"; shift 2 ;;
    --title) TITLE="${2:?}"; shift 2 ;;
    --body-file) BODY_FILE="${2:?}"; shift 2 ;;
    --base) BASE="${2:?}"; shift 2 ;;
    --draft) DRAFT=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown: $1" >&2; exit 2 ;;
  esac
done

[[ -n "$FEATURE" ]] || { usage >&2; exit 2; }
command -v jq >/dev/null || { echo '{"error":"jq required"}' >&2; exit 2; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DETECT=$("${SCRIPT_DIR}/pr-reviewer-detect.sh" --workspace "$WORKSPACE")
PROVIDER=$(echo "$DETECT" | jq -r '.provider')
BRANCH=$(echo "$DETECT" | jq -r '.branch')
HAS_GH=$(echo "$DETECT" | jq -r '.has_gh')
[[ -n "$BASE" ]] || BASE=$(echo "$DETECT" | jq -r '.base_branch')
[[ -n "$TITLE" ]] || TITLE="feat(${FEATURE}): ADLC5 delivery"

if [[ ! -f "$BODY_FILE" ]]; then
  TMP_BODY="$(mktemp)"
  "${SCRIPT_DIR}/pr-reviewer-compose-body.sh" --feature "$FEATURE" --workspace "$WORKSPACE" --out "$TMP_BODY"
  BODY_FILE="$TMP_BODY"
  trap 'rm -f "$TMP_BODY"' EXIT
fi

if [[ "$PROVIDER" == "github" && "$HAS_GH" == "true" ]]; then
  GH_AUTH=$(echo "$DETECT" | jq -r '.gh_authenticated')
  PR_NUM=$(echo "$DETECT" | jq -r '.pr_number // empty')
  if [[ "$GH_AUTH" != "true" ]]; then
    jq -nc '{status:"failed",provider:"github",error:"gh not authenticated; run: gh auth login"}'
    exit 1
  fi
  if [[ -n "$PR_NUM" && "$PR_NUM" != "null" ]]; then
    set +e
    URL=$(gh pr view "$PR_NUM" --json url -q .url 2>&1)
    EC=$?
    set -e
    if [[ "$EC" -eq 0 ]]; then
      jq -nc --arg url "$URL" --arg branch "$BRANCH" --argjson num "$PR_NUM" \
        '{status:"exists",provider:"github",url:$url,branch:$branch,pr_number:$num,message:"PR already open for branch"}'
      exit 0
    fi
  fi
  ARGS=(pr create --base "$BASE" --head "$BRANCH" --title "$TITLE" --body-file "$BODY_FILE")
  [[ "$DRAFT" == true ]] && ARGS+=(--draft)
  set +e
  OUT=$(gh "${ARGS[@]}" 2>&1)
  EC=$?
  set -e
  if [[ "$EC" -eq 0 ]]; then
    jq -nc --arg url "$OUT" --arg branch "$BRANCH" '{status:"opened",provider:"github",url:$url,branch:$branch}'
    exit 0
  fi
  jq -nc --arg err "$OUT" '{status:"failed",provider:"github",error:$err}'
  exit 1
fi

jq -nc \
  --arg provider "$PROVIDER" \
  --arg branch "$BRANCH" \
  --arg base "$BASE" \
  --arg title "$TITLE" \
  --arg body_file "$BODY_FILE" \
  '{status:"manual",provider:$provider,message:"Open PR in your host UI or MCP",branch:$branch,base:$base,title:$title,body_file:$body_file}'
exit 2
