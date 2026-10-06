#!/usr/bin/env bash
# Detect git remote provider and PR tooling for @pr-reviewer.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../lib/pr-template.sh
source "${SCRIPT_DIR}/../lib/pr-template.sh"

WORKSPACE="."

usage() {
  cat <<'EOF'
Usage: pr-reviewer-detect.sh [--workspace DIR]

Stdout: JSON { provider, remote_url, branch, base_branch, has_gh, gh_authenticated,
  repo_slug, pr_number, repo_root, pr_template_path }
  pr_template_path is repo-root-relative, or "" when the repo has no PR template
  (checked: .github/pull_request_template.md, .github/PULL_REQUEST_TEMPLATE.md,
  .github/PULL_REQUEST_TEMPLATE/*.md, PULL_REQUEST_TEMPLATE.md, docs/PULL_REQUEST_TEMPLATE.md)
Exit 0 ok, 2 not a git repo, 3 usage error
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workspace) WORKSPACE="${2:?}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown: $1" >&2; exit 3 ;;
  esac
done

command -v jq >/dev/null || { echo '{"error":"jq required"}' >&2; exit 3; }

WORKSPACE="$(cd "$WORKSPACE" && pwd)"
cd "$WORKSPACE"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  jq -nc '{provider:"none",error:"not a git repository"}'
  exit 2
fi

REPO_ROOT="$(git rev-parse --show-toplevel)"
BRANCH="$(git branch --show-current 2>/dev/null || echo "")"
REMOTE_URL="$(git remote get-url origin 2>/dev/null || echo "")"

BASE="main"
for candidate in main master develop; do
  if git rev-parse --verify "origin/${candidate}" >/dev/null 2>&1; then
    BASE="$candidate"
    break
  fi
done

PROVIDER="generic"
LOWER="$(echo "$REMOTE_URL" | tr '[:upper:]' '[:lower:]')"
case "$LOWER" in
  *github.com*|*github:* ) PROVIDER="github" ;;
  *gitlab*) PROVIDER="gitlab" ;;
  *bitbucket*|*scm/*|*7999*) PROVIDER="bitbucket" ;;
esac

HAS_GH=false
GH_AUTH=false
command -v gh >/dev/null && HAS_GH=true
if [[ "$HAS_GH" == true ]]; then
  gh auth status >/dev/null 2>&1 && GH_AUTH=true
fi

REPO_SLUG=""
PR_NUMBER=""
if [[ "$PROVIDER" == "github" ]]; then
  if [[ "$REMOTE_URL" =~ github\.com[:/]([^/]+)/([^/.]+) ]]; then
    REPO_SLUG="${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
  elif [[ "$REMOTE_URL" =~ git@github\.com:([^/]+)/([^/.]+) ]]; then
    REPO_SLUG="${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
  fi
  if [[ "$HAS_GH" == true && "$GH_AUTH" == true && -n "$BRANCH" ]]; then
    PR_NUMBER="$(gh pr list --head "$BRANCH" --json number -q '.[0].number' 2>/dev/null || echo "")"
    [[ "$PR_NUMBER" == "null" || -z "$PR_NUMBER" ]] && PR_NUMBER=""
  fi
fi

PR_TEMPLATE_PATH="$(adlc5_find_pr_template "$REPO_ROOT")"

jq -nc \
  --arg provider "$PROVIDER" \
  --arg remote_url "$REMOTE_URL" \
  --arg branch "$BRANCH" \
  --arg base_branch "$BASE" \
  --arg repo_root "$REPO_ROOT" \
  --arg repo_slug "$REPO_SLUG" \
  --arg pr_number "$PR_NUMBER" \
  --arg pr_template_path "$PR_TEMPLATE_PATH" \
  --argjson has_gh "$HAS_GH" \
  --argjson gh_authenticated "$GH_AUTH" \
  '{provider:$provider,remote_url:$remote_url,branch:$branch,base_branch:$base_branch,repo_root:$repo_root,repo_slug:$repo_slug,pr_number:$pr_number,has_gh:$has_gh,gh_authenticated:$gh_authenticated,pr_template_path:$pr_template_path}'
