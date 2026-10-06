#!/usr/bin/env bash
# GitHub pull request operations via gh CLI (JSON stdout for @pr-reviewer).
set -euo pipefail

ACTION=""
WORKSPACE="."
BRANCH=""
BODY=""
PR_NUMBER=""

usage() {
  cat <<'EOF'
Usage: pr-reviewer-gh.sh --action ACTION [--workspace DIR] [--branch BRANCH] [--pr NUMBER] [--body TEXT]

Actions:
  status     PR metadata for current branch (or --pr)
  diff       PR diff text (or branch vs base)
  comments   Review/issue comments as JSON
  comment    Post issue comment (--body required)
  checks     CI/check rollup JSON

Requires: gh authenticated (gh auth login). Remote must be GitHub.
Exit 0 ok, 1 gh error, 2 not github / no pr, 3 usage
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --action) ACTION="${2:?}"; shift 2 ;;
    --workspace) WORKSPACE="${2:?}"; shift 2 ;;
    --branch) BRANCH="${2:?}"; shift 2 ;;
    --pr) PR_NUMBER="${2:?}"; shift 2 ;;
    --body) BODY="${2:?}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown: $1" >&2; exit 3 ;;
  esac
done

[[ -n "$ACTION" ]] || { usage >&2; exit 3; }
command -v jq >/dev/null || { echo '{"error":"jq required"}' >&2; exit 3; }
command -v gh >/dev/null || { jq -nc '{error:"gh CLI not installed"}'; exit 3; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DETECT=$("${SCRIPT_DIR}/pr-reviewer-detect.sh" --workspace "$WORKSPACE")
PROVIDER=$(echo "$DETECT" | jq -r '.provider')
HAS_GH=$(echo "$DETECT" | jq -r '.has_gh')
GH_AUTH=$(echo "$DETECT" | jq -r '.gh_authenticated // false')

if [[ "$PROVIDER" != "github" || "$HAS_GH" != "true" ]]; then
  jq -nc --arg p "$PROVIDER" '{error:"not a GitHub remote or gh missing",provider:$p}'
  exit 2
fi

if [[ "$GH_AUTH" != "true" ]]; then
  jq -nc '{error:"gh not authenticated; run: gh auth login"}'
  exit 1
fi

WORKSPACE="$(cd "$WORKSPACE" && pwd)"
cd "$WORKSPACE"
[[ -n "$BRANCH" ]] || BRANCH=$(echo "$DETECT" | jq -r '.branch')

gh_pr() {
  if [[ -n "$PR_NUMBER" ]]; then
    gh pr "$@" "$PR_NUMBER"
  elif [[ -n "$BRANCH" ]]; then
    gh pr "$@" --head "$BRANCH"
  else
    gh pr "$@""
  fi
}

case "$ACTION" in
  status)
    set +e
    OUT=$(gh_pr view --json number,url,title,state,isDraft,baseRefName,headRefName,reviewDecision,statusCheckRollup,mergeable,author 2>&1)
    EC=$?
    set -e
    if [[ "$EC" -ne 0 ]]; then
      jq -nc --arg err "$OUT" --arg branch "$BRANCH" '{found:false,branch:$branch,error:$err}'
      exit 2
    fi
    echo "$OUT" | jq -c '. + {found:true,provider:"github"}'
    ;;
  diff)
    set +e
    OUT=$(gh_pr diff 2>&1)
    EC=$?
    set -e
    if [[ "$EC" -ne 0 ]]; then
      BASE=$(echo "$DETECT" | jq -r '.base_branch')
      OUT=$(git diff "origin/${BASE}...HEAD" 2>&1) || true
      jq -nc --arg diff "$OUT" --arg err "no PR; used git diff" '{source:"git",diff:$diff,note:$err}'
      exit 0
    fi
    jq -nc --arg diff "$OUT" '{source:"gh",diff:$diff}'
    ;;
  comments)
    set +e
    OUT=$(gh_pr view --json comments,reviews,reviewThreads 2>&1)
    EC=$?
    set -e
    [[ "$EC" -eq 0 ]] || { jq -nc --arg err "$OUT" '{error:$err}'; exit 1; }
    echo "$OUT" | jq -c '. + {provider:"github"}'
    ;;
  comment)
    [[ -n "$BODY" ]] || { jq -nc '{error:"--body required"}'; exit 3; }
    set +e
    OUT=$(gh_pr comment --body "$BODY" 2>&1)
    EC=$?
    set -e
    if [[ "$EC" -eq 0 ]]; then
      jq -nc --arg msg "$OUT" '{status:"posted",provider:"github",message:$msg}'
    else
      jq -nc --arg err "$OUT" '{status:"failed",error:$err}'
      exit 1
    fi
    ;;
  checks)
    set +e
    OUT=$(gh_pr view --json statusCheckRollup,mergeStateStatus 2>&1)
    EC=$?
    set -e
    [[ "$EC" -eq 0 ]] || { jq -nc --arg err "$OUT" '{error:$err}'; exit 1; }
    echo "$OUT" | jq -c '. + {provider:"github"}'
    ;;
  *)
    jq -nc --arg a "$ACTION" '{error:"unknown action",action:$a}'
    exit 3
    ;;
esac
